# agents/orchestrator.py

import copy
import time
import traceback
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


class AnalyticsOrchestrator:
    VALID_INTENTS = {"general", "metadata", "sql_query", "visualization"}
    SUPPORTED_CHARTS = {"area", "bar", "box", "histogram", "line", "pie", "scatter"}

    def __init__(
        self,
        enable_redis: bool = False,
        approved_agent_column: str | None = None,
    ):
        self.intent_router = IntentRouterAgent()
        self.general_agent = GeneralAgent()
        self.metadata_agent = MetadataAgent(enable_redis=enable_redis)
        self.metadata_insight_agent = MetadataInsightAgent()
        self.sql_agent = SQLAgent()
        self.sql_validator = SQLValidatorAgent()
        self.visualization_agent = VisualizationAgent()
        self.query_executor = QueryExecutor()
        self.schema_extractor = SchemaExtractor(self.query_executor)
        self.insight_agent = InsightAgent()
        self.chat_memory = ChatMemory()
        self.metadata_filter = MetadataFilter()

        self.redis = RedisService() if enable_redis else None
        self.approved_agent_column = approved_agent_column

    @staticmethod
    def _error(question, error, intent=None, brand=None, sql=None):
        response = {
            "success": False,
            "question": question,
            "brand": brand,
            "error": str(error),
        }

        if intent:
            response["intent"] = intent

        if sql:
            response["sql"] = sql

        return response

    def _get_redis_response(self, cache_key):
        if self.redis is None:
            return None

        try:
            cached = self.redis.get(cache_key)
            return copy.deepcopy(cached) if isinstance(cached, dict) else None
        except Exception as ex:
            print(f"Redis lookup skipped: {ex}")
            return None

    def _store_cache(self, cache_key, response):
        if self.redis is None:
            return

        try:
            saved = self.redis.set(cache_key, response, ttl=3600)
            print("Response saved to Redis." if saved else "Redis storage skipped.")
        except Exception as ex:
            print(f"Redis storage skipped: {ex}")

    def _restore_chat_memory(self, question, response):
        sql = response.get("sql")
        records = response.get("result") or []

        if not sql or not isinstance(records, list):
            return

        try:
            self.chat_memory.add(
                question=question,
                sql=sql,
                result=records[:20],
                insight=response.get("insight"),
            )
        except Exception as ex:
            print(f"Chat memory update skipped: {ex}")

    def _finish_response(self, question, cache_key, response):
        response["cached_at"] = datetime.now(timezone.utc).isoformat()
        self._restore_chat_memory(question, response)
        self._store_cache(cache_key, response)
        return response

    @staticmethod
    def _add_metadata_scope(metadata, brand, schema_name, table_name):
        if not isinstance(metadata, dict):
            raise TypeError("Metadata must be a dictionary.")

        scoped_metadata = dict(metadata)
        scoped_metadata["analysis_scope"] = {
            "brand": brand,
            "schema_name": schema_name,
            "table_name": table_name,
        }
        return scoped_metadata

    def _get_verified_metadata(self, metadata, schema_name: str, table_name: str):
        schema_df = self.schema_extractor.get_columns(
            schema_name=schema_name,
            table_name=table_name,
        )

        if not isinstance(schema_df, pd.DataFrame):
            raise TypeError("SchemaExtractor.get_columns() must return a DataFrame.")

        if "column_name" not in schema_df.columns:
            raise ValueError("Schema metadata must contain column_name.")

        sensitive = {str(column).casefold() for column in SENSITIVE_COLUMNS}

        verified_columns = [
            column
            for column in schema_df["column_name"].dropna().astype(str)
            if column.casefold() not in sensitive
        ]

        verified_columns = list(dict.fromkeys(verified_columns))

        if not verified_columns:
            raise ValueError("No privacy-approved physical columns are available.")

        verified_metadata = dict(metadata)
        verified_metadata["verified_physical_columns"] = verified_columns
        verified_metadata["business_mappings"] = {}

        if self.approved_agent_column:
            if self.approved_agent_column not in verified_columns:
                raise ValueError(
                    "The configured agent identifier is missing from the schema "
                    "or excluded by the privacy policy."
                )

            verified_metadata["business_mappings"] = {
                "agent_identifier": self.approved_agent_column,
            }

        return verified_metadata

    def _prepare_sql(
        self,
        sql_query,
        brand: str,
        schema_name: str,
        table_name: str,
    ) -> str:
        if not isinstance(sql_query, str) or not sql_query.strip():
            raise ValueError("Generated SQL is empty.")

        validation = self.sql_validator.validate(sql_query.strip())

        if not isinstance(validation, dict):
            raise TypeError("SQL validator must return a dictionary.")

        if not validation.get("success", False):
            raise ValueError(validation.get("error") or "SQL validation failed.")

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
                final_validation.get("error") or "Brand-scoped SQL validation failed."
            )

        return final_validation["sql"]


    def _execute_query(self, sql_query):
        started = time.perf_counter()
        result_df = self.query_executor.execute(sql_query)

        print(f"SQL Execution Time: {time.perf_counter() - started:.2f}s")

        if not isinstance(result_df, pd.DataFrame):
            raise TypeError("QueryExecutor.execute() must return a DataFrame.")

        return remove_sensitive_columns(result_df)

    def _validate_chart(self, chart, result_df):
        if not isinstance(chart, dict):
            raise ValueError("Chart specification must be a dictionary.")

        chart_type = str(chart.get("type", "")).lower().strip()

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
                raise ValueError(f"Chart specification requires a valid {axis} field.")

            if field not in result_df.columns:
                raise ValueError(
                    f"Chart field '{field}' is not in the query output. "
                    f"Available columns: {result_df.columns.tolist()}"
                )

        for optional_field in ("color", "size"):
            field = chart.get(optional_field)

            if field is not None and field not in result_df.columns:
                raise ValueError(f"Chart field '{field}' is not in the query output.")

        return chart

    def generate_insight(self, question, sql, result, metadata, history=None):
        if isinstance(result, pd.DataFrame):
            result_df = remove_sensitive_columns(result)
        elif isinstance(result, list):
            result_df = remove_sensitive_columns(pd.DataFrame(result))
        else:
            raise TypeError("Insight result must be a DataFrame or list of records.")

        insight = self.insight_agent.generate_insight(
            question=question,
            metadata=metadata,
            sql=sql,
            result=result_df,
            history=history or [],
        )

        self._restore_chat_memory(
            question,
            {
                "sql": sql,
                "result": result_df.head(20).to_dict(orient="records"),
                "insight": insight,
            },
        )
        return insight

    def analyze_question(
        self,
        question: str,
        brand: str | None = None,
        schema_name: str | None = None,
        table_name: str | None = None,
    ) -> dict:
        overall_start = time.perf_counter()
        intent = None
        sql_query = None

        try:
            if not isinstance(question, str) or not question.strip():
                return self._error(
                    question=question,
                    error="Please enter a question.",
                    brand=brand,
                )

            question = question.strip()

            # ==================================================
            # EXACT CACHE ONLY
            # ==================================================

            cache_key = generate_cache_key(
                question=question,
                brand=brand,
                schema_name=schema_name,
                table_name=table_name,
            )

            cache_start = time.perf_counter()
            cached_response = self._get_redis_response(cache_key)

            print(f"Redis Lookup: {time.perf_counter() - cache_start:.2f}s")

            if isinstance(cached_response, dict) and cached_response.get("success"):
                scope_matches = (
                    cached_response.get("question") == question
                    and cached_response.get("brand") == brand
                    and cached_response.get("schema_name") == schema_name
                    and cached_response.get("table_name") == table_name
                )

                if scope_matches:
                    cached_response["cache_hit"] = True
                    self._restore_chat_memory(question, cached_response)
                    print("EXACT REDIS CACHE HIT")
                    return cached_response

            print("Cache miss. Semantic response reuse is disabled.")

            # ==================================================
            # INTENT DETECTION
            # ==================================================

            intent_start = time.perf_counter()
            intent_result = self.intent_router.classify(question)

            print(f"Intent Time: {time.perf_counter() - intent_start:.2f}s")

            if not isinstance(intent_result, dict):
                raise TypeError("IntentRouterAgent must return a dictionary.")

            intent = intent_result.get("intent")

            if intent not in self.VALID_INTENTS:
                raise ValueError(f"Unsupported intent: {intent}")

            print(f"DETECTED INTENT: {intent}")

            base_response = {
                "success": True,
                "intent": intent,
                "question": question,
                "brand": brand,
                "schema_name": schema_name,
                "table_name": table_name,
            }

            # ==================================================
            # GENERAL INTENT
            # ==================================================

            if intent == "general":
                general_result = self.general_agent.respond(question)

                if not isinstance(general_result, dict):
                    raise TypeError("GeneralAgent must return a dictionary.")

                if general_result.get("success") is False:
                    return self._error(
                        question=question,
                        error=general_result.get("error") or "General response failed.",
                        intent=intent,
                        brand=brand,
                    )

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

            # ==================================================
            # VALIDATE LOADED DATASET
            # ==================================================

            if not brand or not schema_name or not table_name:
                raise ValueError(
                    "Please select a brand and load a valid schema and table first."
                )

            # ==================================================
            # METADATA RETRIEVAL
            # ==================================================

            metadata_start = time.perf_counter()

            metadata_result = self.metadata_agent.retrieve(
                question=question,
                brand=brand,
                schema_name=schema_name,
                table_name=table_name,
            )

            print(
                f"Metadata Retrieval Time: "
                f"{time.perf_counter() - metadata_start:.2f}s"
            )

            if not isinstance(metadata_result, dict):
                raise TypeError("MetadataAgent must return a dictionary.")

            if not metadata_result.get("context"):
                return self._error(
                    question=question,
                    error="No usable metadata was retrieved for the loaded table.",
                    intent=intent,
                    brand=brand,
                )

            filtered_metadata = self.metadata_filter.apply(metadata_result)

            filtered_metadata = self._add_metadata_scope(
                metadata=filtered_metadata,
                brand=brand,
                schema_name=schema_name,
                table_name=table_name,
            )

            # ==================================================
            # METADATA INTENT
            # ==================================================

            if intent == "metadata":
                metadata_question = (
                    f"{question}\n\n"
                    f"Loaded brand: {brand}.\n"
                    f"Loaded table: {schema_name}.{table_name}.\n"
                    "Explain the schema and business definitions in this context. "
                    "Do not infer brand-specific counts, averages, distributions, "
                    "or trends from schema metadata alone."
                )

                insight_start = time.perf_counter()

                insight = self.metadata_insight_agent.generate_insight(
                    question=metadata_question,
                    metadata=filtered_metadata,
                )

                print(
                    f"Metadata Insight Time: "
                    f"{time.perf_counter() - insight_start:.2f}s"
                )

                if not isinstance(insight, dict):
                    raise TypeError("MetadataInsightAgent must return a dictionary.")

                if insight.get("success") is False:
                    return self._error(
                        question=question,
                        error=insight.get("error") or "Metadata insight generation failed.",
                        intent=intent,
                        brand=brand,
                    )

                response = {
                    **base_response,
                    "metadata": filtered_metadata,
                    "sql": "",
                    "result": None,
                    "insight": insight,
                }

                return self._finish_response(question, cache_key, response)

            # ==================================================
            # VERIFIED PHYSICAL SCHEMA
            # ==================================================

            schema_start = time.perf_counter()

            generation_metadata = self._get_verified_metadata(
                metadata=filtered_metadata,
                schema_name=schema_name,
                table_name=table_name,
            )

            print(f"Schema Verification Time: {time.perf_counter() - schema_start:.2f}s")

            # ==================================================
            # SQL / VISUALIZATION GENERATION
            # ==================================================

            generation_start = time.perf_counter()
            chart = None

            if intent == "visualization":
                generated = self.visualization_agent.generate(
                    question=question,
                    metadata=generation_metadata,
                    brand=brand,
                )
                generation_label = "Visualization Generation"

            elif intent == "sql_query":
                generated = self.sql_agent.generate_sql(
                    question=question,
                    metadata=generation_metadata,
                    brand=brand,
                )
                generation_label = "SQL Generation"

            else:
                raise ValueError(f"Unsupported generation intent: {intent}")

            print(
                f"{generation_label} Time: "
                f"{time.perf_counter() - generation_start:.2f}s"
            )

            if not isinstance(generated, dict):
                raise TypeError("Generation agent must return a dictionary.")

            if not generated.get("success", False):
                return {
                    **self._error(
                        question=question,
                        error=generated.get("error") or "Generation failed.",
                        intent=intent,
                        brand=brand,
                    ),
                    "metadata": generation_metadata,
                }

            if intent == "visualization":
                chart = generated.get("chart")

                if not isinstance(chart, dict) or not chart:
                    raise ValueError("A valid chart specification was not generated.")

            # ==================================================
            # SQL VALIDATION AND BRAND SCOPING
            # ==================================================

            validation_start = time.perf_counter()

            sql_query = self._prepare_sql(
                sql_query=generated.get("sql"),
                brand=brand,
                schema_name=schema_name,
                table_name=table_name,
            )

            print(
                f"SQL Validation Time: "
                f"{time.perf_counter() - validation_start:.2f}s"
            )

            print("\n" + "=" * 80)
            print(f"EXECUTING {intent.upper()} SQL")
            print("=" * 80)
            print(sql_query)
            print("=" * 80)

            # ==================================================
            # QUERY EXECUTION AND PII CLEANUP
            # ==================================================

            result_df = self._execute_query(sql_query)

            # _execute_query() already validates the DataFrame
            # response and removes sensitive columns.

            # ==================================================
            # CHART VALIDATION
            # ==================================================

            if chart is not None:
                chart = self._validate_chart(chart, result_df)

            # ==================================================
            # RESPONSE
            # ==================================================

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

        except Exception as ex:
            print("\n" + "=" * 80)
            print("ORCHESTRATOR ERROR")
            print("=" * 80)
            print(str(ex))
            print("=" * 80)

            traceback.print_exc()

            return self._error(
                question=question,
                error=ex,
                intent=intent,
                brand=brand,
                sql=sql_query,
            )

        finally:
            print(f"TOTAL REQUEST TIME: {time.perf_counter() - overall_start:.2f}s")