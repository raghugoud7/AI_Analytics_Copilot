# agents/metadata_profiler_agent.py

import json
import logging
from typing import Dict, Any

from llm.llm_factory import get_llm
from prompts.metadata_profiler_prompt import (
    METADATA_PROFILER_PROMPT
)

logger = logging.getLogger(__name__)


class MetadataProfilerAgent:

    def __init__(self):
        self.llm = get_llm()

    def _prepare_metadata(
        self,
        metadata_df
    ) -> Dict[str, Any]:

        columns = metadata_df.to_dict("records")

        column_names = []
        data_types = {}
        candidate_kpis = []
        date_columns = []
        identifier_columns = []

        kpi_keywords = [
            "score",
            "quality",
            "revenue",
            "sales",
            "profit",
            "amount",
            "duration",
            "cost",
            "rate",
            "satisfaction",
            "volume",
            "count",
            "csat",
            "nps",
            "kpi"
        ]

        date_keywords = [
            "date",
            "time",
            "timestamp",
            "created",
            "updated",
            "modified"
        ]

        id_keywords = [
            "id",
            "_id",
            "key",
            "number"
        ]

        for row in columns:

            column_name = row.get("column_name")
            data_type = row.get("data_type")

            if not column_name:
                continue

            column_names.append(column_name)

            data_types[column_name] = data_type

            col_lower = column_name.lower()

            if any(
                keyword in col_lower
                for keyword in kpi_keywords
            ):
                candidate_kpis.append(column_name)

            if any(
                keyword in col_lower
                for keyword in date_keywords
            ):
                date_columns.append(column_name)

            if any(
                keyword in col_lower
                for keyword in id_keywords
            ):
                identifier_columns.append(column_name)

        return {
            "total_columns": len(column_names),
            "column_names": column_names,
            "data_types": data_types,
            "candidate_kpis": candidate_kpis,
            "date_columns": date_columns,
            "identifier_columns": identifier_columns,
            "metadata_records": columns
        }

    def _clean_llm_response(
        self,
        content: str
    ) -> str:

        if not content:
            return ""

        content = content.strip()

        if content.startswith("```json"):
            content = content.replace(
                "```json",
                ""
            )

        if content.startswith("```"):
            content = content.replace(
                "```",
                ""
            )

        if content.endswith("```"):
            content = content[:-3]

        return content.strip()

    def profile_metadata(
        self,
        metadata_df,
        table_name: str,
        schema_name: str = ""
    ) -> Dict[str, Any]:

        prepared_metadata = self._prepare_metadata(
            metadata_df
        )

        metadata_text = json.dumps(
            prepared_metadata,
            indent=2,
            default=str
        )

        prompt = METADATA_PROFILER_PROMPT.format(
            table_name=table_name,
            schema_name=schema_name,
            metadata=metadata_text
        )

        logger.info(
            f"Profiling metadata for {schema_name}.{table_name}"
        )

        response = self.llm.invoke(
            prompt
        )

        content = self._clean_llm_response(
            response.content
        )

        try:

            llm_output = json.loads(
                content
            )

            return {
                "success": True,
                "schema_name": schema_name,
                "table_name": table_name,
                "column_count": prepared_metadata[
                    "total_columns"
                ],
                "candidate_kpis": prepared_metadata[
                    "candidate_kpis"
                ],
                "date_columns": prepared_metadata[
                    "date_columns"
                ],
                "identifier_columns": prepared_metadata[
                    "identifier_columns"
                ],
                "profile": llm_output
            }

        except Exception as ex:

            logger.exception(
                "Failed parsing MetadataProfilerAgent response"
            )

            return {
                "success": False,
                "schema_name": schema_name,
                "table_name": table_name,
                "column_count": prepared_metadata[
                    "total_columns"
                ],
                "candidate_kpis": prepared_metadata[
                    "candidate_kpis"
                ],
                "date_columns": prepared_metadata[
                    "date_columns"
                ],
                "identifier_columns": prepared_metadata[
                    "identifier_columns"
                ],
                "error": str(ex),
                "raw_response": content
            }