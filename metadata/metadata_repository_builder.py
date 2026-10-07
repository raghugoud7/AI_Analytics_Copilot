# metadata/metadata_repository_builder.py

import json
from pathlib import Path


class MetadataRepositoryBuilder:

    def __init__(
        self,
        output_file="metadata/metadata_repository.json"
    ):
        self.output_file = output_file

    def _add_list_documents(
        self,
        repository,
        document_type,
        items,
        prefix=None
    ):
        for item in items or []:

            content = (
                f"{prefix}: {item}"
                if prefix
                else str(item)
            )

            name_value = item
            if isinstance(item, dict):
                name_value = item.get(
                    "name",
                    str(item)
                )
          
            repository.append(
                {
                    "document_type": document_type,
                    "name": name_value,
                    "schema_name": None,
                    "table_name": None,
                    "column_name": name_value,
                    "content": content
                }
            )

    def build(
        self,
        schema_name: str,
        table_name: str,
        metadata_df,
        profiling_output: dict
    ):

        repository = []

        # ==================================================
        # TABLE DOCUMENT
        # ==================================================

        repository.append(
            {
                "document_type": "table",
                "schema_name": schema_name,
                "table_name": table_name,
                "content": (
                    f"Schema: {schema_name}\n"
                    f"Table: {table_name}\n"
                    f"Fully Qualified Table: "
                    f"{schema_name}.{table_name}"
                )
            }
        )

        # ==================================================
        # COLUMN DOCUMENTS
        # ==================================================

        for row in metadata_df.to_dict("records"):

            column_name = row.get("column_name")
            data_type = row.get("data_type")

            repository.append(
                {
                    "document_type": "column",
                    "name": column_name,
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "column_name": column_name,
                    "data_type": data_type,
                    "content": (
                        f"Schema: {schema_name}\n"
                        f"Table: {table_name}\n"
                        f"Column: {column_name}\n"
                        f"Data Type: {data_type}"
                    )
                }
            )

        # ==================================================
        # BUSINESS DOMAIN
        # ==================================================

        if profiling_output.get(
            "business_domain"
        ):
            repository.append(
                {
                    "document_type": "business_domain",
                    "content": profiling_output[
                        "business_domain"
                    ]
                }
            )

        # ==================================================
        # TABLE PURPOSE
        # ==================================================

        if profiling_output.get(
            "table_purpose"
        ):
            repository.append(
                {
                    "document_type": "table_purpose",
                    "content": profiling_output[
                        "table_purpose"
                    ]
                }
            )

        # ==================================================
        # ENTITY DOCUMENTS
        # ==================================================

        self._add_list_documents(
            repository,
            "entity",
            profiling_output.get("entities"),
            "Business Entity"
        )

        # ==================================================
        # DIMENSION DOCUMENTS
        # ==================================================

        self._add_list_documents(
            repository,
            "dimension",
            profiling_output.get("dimensions"),
            "Business Dimension"
        )

        # ==================================================
        # MEASURE DOCUMENTS
        # ==================================================

        self._add_list_documents(
            repository,
            "measure",
            profiling_output.get("measures"),
            "Measure"
        )

        # ==================================================
        # KPI DOCUMENTS
        # ==================================================

        self._add_list_documents(
            repository,
            "kpi",
            profiling_output.get("kpis"),
            "KPI"
        )

        # ==================================================
        # TIME DIMENSIONS
        # ==================================================

        self._add_list_documents(
            repository,
            "time_dimension",
            profiling_output.get(
                "time_dimensions"
            ),
            "Time Dimension"
        )

        # ==================================================
        # CUSTOMER DIMENSIONS
        # ==================================================

        self._add_list_documents(
            repository,
            "customer_dimension",
            profiling_output.get(
                "customer_dimensions"
            ),
            "Customer Dimension"
        )

        # ==================================================
        # RISK METRICS
        # ==================================================

        self._add_list_documents(
            repository,
            "risk_metric",
            profiling_output.get(
                "risk_metrics"
            ),
            "Risk Metric"
        )

        # ==================================================
        # OPPORTUNITY METRICS
        # ==================================================

        self._add_list_documents(
            repository,
            "opportunity_metric",
            profiling_output.get(
                "opportunity_metrics"
            ),
            "Opportunity Metric"
        )

        # ==================================================
        # BUSINESS QUESTIONS
        # ==================================================

        for question in profiling_output.get(
            "business_questions",
            []
        ):
            repository.append(
                {
                    "document_type":
                        "business_question",
                    "content":
                        question
                }
            )

        # ==================================================
        # DASHBOARDS
        # ==================================================

        for dashboard in profiling_output.get(
            "suggested_dashboards",
            []
        ):
            repository.append(
                {
                    "document_type":
                        "dashboard",
                    "content":
                        dashboard
                }
            )

        # ==================================================
        # SAVE
        # ==================================================

        Path(
            self.output_file
        ).parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            self.output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                repository,
                f,
                indent=4,
                ensure_ascii=False
            )

        print(
            f"Metadata repository saved: "
            f"{self.output_file}"
        )

        print(
            f"Total documents created: "
            f"{len(repository)}"
        )

        return repository