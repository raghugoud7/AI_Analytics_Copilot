# agents/orchestrator.py

import copy
import re
import time
from datetime import datetime, timezone

import pandas as pd

from agents.general_agent import GeneralAgent
from agents.insight_agent import InsightAgent
from agents.intent_router_agent import IntentRouterAgent
from agents.metadata_agent import MetadataAgent
from agents.metadata_insight_agent import MetadataInsightAgent
from agents.sql_agent import SQLAgent
from agents.sql_validator_agent import SQLValidatorAgent
from agents.visualization_agent import VisualizationAgent
from cache.redis_service import RedisService
from config.privacy import SENSITIVE_COLUMNS
from database.query_executor import QueryExecutor
from database.schema_extractor import SchemaExtractor
from memory.chat_memory import ChatMemory
from metadata.metadata_filter import MetadataFilter
from utils.cache_utils import generate_cache_key
from utils.privacy import remove_sensitive_columns
from utils.privacy_policy import PrivacyPolicy, dataset_key, normalize_column


class AnalyticsOrchestrator:
    VALID_INTENTS = {"general", "metadata", "sql_query", "visualization"}
    SUPPORTED_CHARTS = {"area", "bar", "box", "histogram", "line", "pie", "scatter"}

    def __init__(
        self,
        enable_redis: bool = False,
        approved_agent_column: str | None = None,
        privacy_policy: PrivacyPolicy | None = None,
    ):
        # Do not reuse responses across different privacy policies.
        # Enable this only after access-aware cache isolation is implemented.
        if enable_redis and privacy_policy is not None:
            raise ValueError(
                "Redis must remain disabled for policy-aware requests "
                "until privacy and user-access cache isolation is implemented."
            )

        self.privacy_policy = privacy_policy
        self.approved_agent_column = approved_agent_column

        self.intent_router = IntentRouterAgent()
        self.general_agent = GeneralAgent()
        self.metadata_agent = MetadataAgent(enable_redis=enable_redis)
        self.metadata_insight_agent = MetadataInsightAgent()
        self.sql_agent = SQLAgent()

        # IMPORTANT: dynamic exclusions must reach execution-time validation.
        self.sql_validator = SQLValidatorAgent(privacy_policy=privacy_policy)

        self.visualization_agent = VisualizationAgent()
        self.query_executor = QueryExecutor()
        self.schema_extractor = SchemaExtractor(self.query_executor)
        self.insight_agent = InsightAgent()
        self.chat_memory = ChatMemory()
        self.metadata_filter = MetadataFilter()

        self.redis = RedisService() if enable_redis else None

    # ==================================================
    # RESPONSE AND CACHE HELPERS
    # ==================================================

    @staticmethod
    def _error(question, error, intent=None, brand=None):
        # Do not include raw SQL or database exception details in errors.
        response = {
            "success": False,
            "question": question,
            "brand": brand,
            "error": str(error),
        }

        if intent:
            response["intent"] = intent

        return response

    def _get_redis_response(self, cache_key):
        if self.redis is None:
            return None

        try:
            cached = self.redis.get(cache_key)
            return copy.deepcopy(cached) if isinstance(cached, dict) else None
        except Exception:
            print("Redis lookup skipped.")
            return None

    def _store_cache(self, cache_key, response):
        if self.redis is None:
            return

        try:
            saved = self.redis.set(cache_key, response, ttl=3600)
            print("Response cached." if saved else "Cache storage skipped.")
        except Exception:
            print("Cache storage skipped.")

    def _restore_chat_memory(self, question, response):
        sql = response.get("sql")
        records = response.get("result")

        if not sql or not isinstance(records, list):
            return

        # Responses reaching this helper have already passed SQL validation
        # and result cleanup.
        try:
            self.chat_memory.add(
                question=question,
                sql=sql,
                result=records[:20],
                insight=response.get("insight"),
            )
        except Exception:
            print("Chat memory update skipped.")

    def _finish_response(self, question, cache_key, response):
        response["cached_at"] = datetime.now(timezone.utc).isoformat()

        if self.privacy_policy is not None:
            response["privacy_policy_fingerprint"] = self.privacy_policy.fingerprint

        self._restore_chat_memory(question, response)
        self._store_cache(cache_key, response)
        return response

    # ==================================================
    # PRIVACY HELPERS
    # ==================================================

    def _require_policy(self) -> PrivacyPolicy:
        policy = self.privacy_policy

        if policy is None:
            raise ValueError("Apply privacy settings and reload the dataset first.")

        if not policy.approved_columns:
            raise ValueError("No approved columns remain in the applied policy.")

        # This app currently requires brand__c for SQL scoping.
        # Fail closed if it is excluded instead of silently bypassing policy.
        if "brand__c" in policy.blocked_names:
            raise ValueError(
                "brand__c is excluded, but this application requires it "
                "for brand scoping. Review the policy before continuing."
            )

        return policy

    def _blocked_names(self) -> set[str]:
        blocked = {
            normalize_column(column)
            for column in SENSITIVE_COLUMNS
        }

        if self.privacy_policy is not None:
            blocked.update(self.privacy_policy.blocked_names)

        return blocked

    @staticmethod
    def _add_metadata_scope(metadata, brand, schema_name, table_name):
        if not isinstance(metadata, dict):
            raise TypeError("Metadata must be a dictionary.")

        scoped = dict(metadata)
        scoped["analysis_scope"] = {
            "brand": brand,
            "schema_name": schema_name,
            "table_name": table_name,
        }
        return scoped

    def _filter_policy_metadata(self, metadata: dict) -> dict:
        """
        Remove metadata items mentioning blocked column names.

        This is not a free-text PII redactor. Metadata must contain reviewed
        schema/business definitions, not raw personal records.
        """
        policy = self._require_policy()

        if not isinstance(metadata, dict):
            raise TypeError("Metadata must be a dictionary.")

        approved = {
            normalize_column(column)
            for column in policy.approved_columns
        }

        patterns = [
            re.compile(
                rf"(?<!\w){re.escape(column)}(?!\w)",
                flags=re.IGNORECASE,
            )
            for column in self._blocked_names()
        ]

        def mentions_blocked(value) -> bool:
            if isinstance(value, dict):
                return any(
                    mentions_blocked(key) or mentions_blocked(item)
                    for key, item in value.items()
                )

            if isinstance(value, (list, tuple)):
                return any(mentions_blocked(item) for item in value)

            return any(pattern.search(str(value)) for pattern in patterns)

        result = {}

        # Retain only reviewed structural metadata fields.
        for key in ("tables", "kpis", "measures", "dimensions"):
            items = metadata.get(key) or []

            if isinstance(items, list):
                result[key] = [
                    item for item in items if not mentions_blocked(item)
                ]
            else:
                result[key] = []

        result["columns"] = [
            column
            for column in metadata.get("columns", [])
            if isinstance(column, str)
            and normalize_column(column) in approved
            and normalize_column(column) not in self._blocked_names()
        ]

        documents = [
            document
            for document in metadata.get("documents", [])
            if isinstance(document, dict)
            and not mentions_blocked(document)
        ]
        result["documents"] = documents

        # Rebuild context from retained documents rather than reusing
        # potentially unfiltered context.
        result["context"] = "\n\n".join(
            str(document.get("content") or "")
            for document in documents
            if document.get("content")
        )

        result["privacy_scope"] = {
            "policy_fingerprint": policy.fingerprint,
            "approved_columns": list(policy.approved_columns),
        }

        return result

    # ==================================================
    # VERIFIED SCHEMA
    # ==================================================

    def _get_verified_metadata(
        self,
        metadata: dict,
        schema_name: str,
        table_name: str,
    ) -> dict:
        policy = self._require_policy()

        schema_df = self.schema_extractor.get_columns(
            schema_name=schema_name,
            table_name=table_name,
        )

        if not isinstance(schema_df, pd.DataFrame):
            raise TypeError("SchemaExtractor must return a DataFrame.")

        if "column_name" not in schema_df.columns:
            raise ValueError("Schema metadata must contain column_name.")

        current_columns = schema_df["column_name"].dropna().astype(str).tolist()
        current_dataset_id = dataset_key(
            schema_name,
            table_name,
            current_columns,
        )

        # Validate for metadata intent as well as SQL/visualization.
        if current_dataset_id != policy.dataset_id:
            raise ValueError(
                "The selected table or schema changed. "
                "Inspect privacy and reload the dataset."
            )

        approved = {
            normalize_column(column)
            for column in policy.approved_columns
        }
        blocked = self._blocked_names()

        verified_columns = [
            column
            for column in current_columns
            if normalize_column(column) in approved
            and normalize_column(column) not in blocked
        ]

        if not verified_columns:
            raise ValueError("No approved physical columns are available.")

        verified_metadata = dict(metadata)
        verified_metadata["verified_physical_columns"] = verified_columns
        verified_metadata["business_mappings"] = {}

        if self.approved_agent_column:
            if self.approved_agent_column not in verified_columns:
                raise ValueError(
                    "The configured agent identifier is unavailable "
                    "or excluded by the applied privacy policy."
                )

            verified_metadata["business_mappings"] = {
                "agent_identifier": self.approved_agent_column,
            }

        return verified_metadata

    # ==================================================
    # SQL VALIDATION AND EXECUTION
    # ==================================================

    def _prepare_sql(
        self,
        sql_query,
        brand: str,
        schema_name: str,
        table_name: str,
    ) -> str:
        self._require_policy()

        if not isinstance(sql_query, str) or not sql_query.strip():
            raise ValueError("Generated SQL is empty.")

        validation = self.sql_validator.validate(sql_query.strip())

        if not isinstance(validation, dict):
            raise TypeError("SQL validator must return a dictionary.")

        if not validation.get("success", False):
            raise ValueError(validation.get("error") or "SQL validation failed.")

        # Uses your SQLGlot-based loaded-table and brand enforcement.
        scoped_sql = self.sql_validator.apply_brand_filter(
            sql=validation["sql"],
            brand=brand,
            schema_name=schema_name,
            table_name=table_name,
        )

        final_validation = self.sql_validator.validate(scoped_sql)

        if not isinstance(final_validation, dict):
            raise TypeError("SQL validator must return a dictionary.")

        if not final_validation.get("success", False):
            raise ValueError(
                final_validation.get("error") or "Scoped SQL validation failed."
            )

        return final_validation["sql"]

    def _execute_query(self, sql_query: str) -> pd.DataFrame:
        policy = self._require_policy()

        # Validate again immediately before execution.
        validation = self.sql_validator.validate(sql_query)

        if not validation.get("success", False):
            raise ValueError(
                validation.get("error") or "SQL privacy validation failed."
            )

        started = time.perf_counter()

        try:
            result_df = self.query_executor.execute(validation["sql"])
        except Exception:
            # Database errors can contain SQL literals or source values.
            # Do not expose those details to the UI or ordinary logs.
            raise RuntimeError(
                "Database query failed. Review column types, approved mappings, "
                "and query compatibility using restricted diagnostic tooling."
            ) from None
        finally:
            print(f"SQL Execution Time: {time.perf_counter() - started:.2f}s")

        if not isinstance(result_df, pd.DataFrame):
            raise TypeError("QueryExecutor must return a DataFrame.")

        # Defense in depth. Aliased source fields must already have been
        # blocked by SQL validation; output-name cleanup alone is insufficient.
        return remove_sensitive_columns(result_df, policy=policy)

    # ==================================================
    # CHART VALIDATION
    # ==================================================

    def _validate_chart(self, chart, result_df):
        if not isinstance(chart, dict):
            raise ValueError("Chart specification must be a dictionary.")

        chart = dict(chart)
        chart_type = str(chart.get("type") or "").lower().strip()

        if chart_type not in self.SUPPORTED_CHARTS:
            raise ValueError(f"Unsupported chart type: {chart_type}")

        chart["type"] = chart_type

        required_axes = (
            ["x"] if chart_type == "histogram"
            else ["y"] if chart_type == "box"
            else ["x", "y"]
        )

        for axis in required_axes:
            field = chart.get(axis)

            if not isinstance(field, str) or not field.strip():
                raise ValueError(f"Chart requires a valid {axis} field.")

            if field not in result_df.columns:
                raise ValueError(
                    f"Chart field '{field}' is not in the approved query output."
                )

        # Box grouping is optional but must be valid when supplied.
        optional_fields = ["color", "size"]

        if chart_type == "box":
            optional_fields.append("x")

        for field_name in optional_fields:
            field = chart.get(field_name)

            if field is not None and field not in result_df.columns:
                raise ValueError(
                    f"Chart field '{field}' is not in the approved query output."
                )

        return chart

    # ==================================================
    # INSIGHT GENERATION
    # ==================================================

    def generate_insight(
        self,
        question,
        sql,
        result,
        metadata,
        history=None,
    ):
        policy = self._require_policy()

        # Validate the source SQL before using supplied results.
        validation = self.sql_validator.validate(sql)

        if not validation.get("success", False):
            raise ValueError(
                validation.get("error") or "Insight SQL violates the privacy policy."
            )

        if isinstance(result, pd.DataFrame):
            result_df = result
        elif isinstance(result, list):
            result_df = pd.DataFrame(result)
        else:
            raise TypeError("Insight result must be a DataFrame or list of records.")

        result_df = remove_sensitive_columns(result_df, policy=policy)
        safe_metadata = self._filter_policy_metadata(metadata)

        if isinstance(metadata, dict) and isinstance(metadata.get("analysis_scope"), dict):
            safe_metadata["analysis_scope"] = dict(metadata["analysis_scope"])

        # Only call this method with results produced by this orchestrator.
        # Arbitrary history is intentionally not forwarded to the model.
        insight = self.insight_agent.generate_insight(
            question=question,
            metadata=safe_metadata,
            sql=validation["sql"],
            result=result_df,
            history=[],
        )

        self._restore_chat_memory(
            question,
            {
                "sql": validation["sql"],
                "result": result_df.head(20).to_dict(orient="records"),
                "insight": insight,
            },
        )

        return insight

    # ==================================================
    # MAIN REQUEST FLOW
    # ==================================================

    def analyze_question(
        self,
        question: str,
        brand: str | None = None,
        schema_name: str | None = None,
        table_name: str | None = None,
    ) -> dict:
        overall_start = time.perf_counter()
        intent = None

        try:
            if not isinstance(question, str) or not question.strip():
                return self._error(
                    question=question,
                    error="Please enter a question.",
                    brand=brand,
                )

            question = question.strip()

            # Policy-aware Redis is disabled by the constructor.
            cache_key = generate_cache_key(
                question=question,
                brand=brand,
                schema_name=schema_name,
                table_name=table_name,
            )

            cached = self._get_redis_response(cache_key)

            if isinstance(cached, dict) and cached.get("success"):
                scope_matches = (
                    cached.get("question") == question
                    and cached.get("brand") == brand
                    and cached.get("schema_name") == schema_name
                    and cached.get("table_name") == table_name
                )

                if scope_matches:
                    cached["cache_hit"] = True
                    self._restore_chat_memory(question, cached)
                    return cached

            # The question itself is sent to the intent model.
            # Do not enter contact values or other confidential literals
            # unless your model endpoint and input policy permit them.
            started = time.perf_counter()
            intent_result = self.intent_router.classify(question)
            print(f"Intent Time: {time.perf_counter() - started:.2f}s")

            if not isinstance(intent_result, dict):
                raise TypeError("Intent router must return a dictionary.")

            intent = intent_result.get("intent")

            if intent not in self.VALID_INTENTS:
                raise ValueError("The requested intent is unsupported.")

            base_response = {
                "success": True,
                "intent": intent,
                "question": question,
                "brand": brand,
                "schema_name": schema_name,
                "table_name": table_name,
            }

            # General responses do not receive dataset metadata or results.
            if intent == "general":
                general_result = self.general_agent.respond(question)

                if not isinstance(general_result, dict):
                    raise TypeError("General agent must return a dictionary.")

                if general_result.get("success") is False:
                    raise ValueError("General response generation failed.")

                response = {
                    **base_response,
                    "metadata": None,
                    "sql": "",
                    "result": None,
                    "insight": {
                        "answer": general_result.get("answer") or "No response generated.",
                    },
                }

                return self._finish_response(question, cache_key, response)

            # All dataset intents require a loaded scope and applied policy.
            if not brand or not schema_name or not table_name:
                raise ValueError(
                    "Please select a brand and load a valid schema and table first."
                )

            self._require_policy()

            started = time.perf_counter()
            metadata_result = self.metadata_agent.retrieve(
                question=question,
                brand=brand,
                schema_name=schema_name,
                table_name=table_name,
            )
            print(f"Metadata Retrieval Time: {time.perf_counter() - started:.2f}s")

            if not isinstance(metadata_result, dict):
                raise TypeError("Metadata agent must return a dictionary.")

            filtered_metadata = self.metadata_filter.apply(metadata_result)
            filtered_metadata = self._filter_policy_metadata(filtered_metadata)
            filtered_metadata = self._add_metadata_scope(
                metadata=filtered_metadata,
                brand=brand,
                schema_name=schema_name,
                table_name=table_name,
            )

            # Verify the live schema for every dataset intent, including metadata.
            started = time.perf_counter()
            generation_metadata = self._get_verified_metadata(
                metadata=filtered_metadata,
                schema_name=schema_name,
                table_name=table_name,
            )
            print(f"Schema Verification Time: {time.perf_counter() - started:.2f}s")

            # If semantic documents were filtered out, retain a minimal,
            # approved schema context rather than restoring unsafe context.
            if not generation_metadata.get("context"):
                approved = generation_metadata["verified_physical_columns"]
                generation_metadata["context"] = (
                    f"Loaded table: {schema_name}.{table_name}.\n"
                    f"Approved physical columns: {', '.join(approved)}.\n"
                    "No approved business definitions were retrieved. "
                    "Do not invent column meanings, units, or relationships."
                )

            if intent == "metadata":
                metadata_question = (
                    f"{question}\n\n"
                    f"Loaded brand: {brand}.\n"
                    "Describe only approved schema and business definitions. "
                    "Do not infer brand-specific statistics from metadata."
                )

                insight = self.metadata_insight_agent.generate_insight(
                    question=metadata_question,
                    metadata=generation_metadata,
                )

                if not isinstance(insight, dict):
                    raise TypeError("Metadata insight agent must return a dictionary.")

                if insight.get("success") is False:
                    raise ValueError("Metadata insight generation failed.")

                response = {
                    **base_response,
                    "metadata": generation_metadata,
                    "sql": "",
                    "result": None,
                    "insight": insight,
                }

                return self._finish_response(question, cache_key, response)

            # SQL and visualization receive only approved metadata.
            started = time.perf_counter()
            chart = None

            if intent == "visualization":
                generated = self.visualization_agent.generate(
                    question=question,
                    metadata=generation_metadata,
                    brand=brand,
                )
                label = "Visualization Generation"
            else:
                generated = self.sql_agent.generate_sql(
                    question=question,
                    metadata=generation_metadata,
                    brand=brand,
                )
                label = "SQL Generation"

            print(f"{label} Time: {time.perf_counter() - started:.2f}s")

            if not isinstance(generated, dict):
                raise TypeError("Generation agent must return a dictionary.")

            if not generated.get("success", False):
                # Avoid forwarding arbitrary raw model output or SQL in errors.
                return self._error(
                    question=question,
                    error=(
                        "The requested analysis could not be generated using "
                        "the approved columns and available business mappings."
                    ),
                    intent=intent,
                    brand=brand,
                )

            if intent == "visualization":
                chart = generated.get("chart")

                if not isinstance(chart, dict) or not chart:
                    raise ValueError("A valid chart specification was not generated.")

            sql_query = self._prepare_sql(
                sql_query=generated.get("sql"),
                brand=brand,
                schema_name=schema_name,
                table_name=table_name,
            )

            # Do not print raw SQL, prompts, or query results.
            result_df = self._execute_query(sql_query)

            if chart is not None:
                chart = self._validate_chart(chart, result_df)

            response = {
                **base_response,
                "metadata": generation_metadata,
                "sql": sql_query,
                "result": result_df.to_dict(orient="records"),
                "row_count": len(result_df),
                "insight": None,
                "insight_available": not result_df.empty,
            }

            if chart is not None:
                response["chart"] = chart

            if result_df.empty:
                response["message"] = "No matching records were found for the loaded brand."

            return self._finish_response(question, cache_key, response)

        except (ValueError, TypeError) as ex:
            # These are application validation messages, not database payloads.
            print(f"Request validation failed: {type(ex).__name__}")
            return self._error(
                question=question,
                error=ex,
                intent=intent,
                brand=brand,
            )

        except Exception as ex:
            # Do not print raw exception messages or tracebacks:
            # upstream libraries may include SQL literals or personal values.
            print(f"Request failed: {type(ex).__name__}")
            return self._error(
                question=question,
                error=(
                    "The request could not be completed. "
                    "Check the approved schema, mappings, and service connectivity."
                ),
                intent=intent,
                brand=brand,
            )

        finally:
            print(f"TOTAL REQUEST TIME: {time.perf_counter() - overall_start:.2f}s")