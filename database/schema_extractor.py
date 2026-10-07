# database/schema_extractor.py

import pandas as pd


class SchemaExtractor:

    def __init__(self, query_executor):
        self.query_executor = query_executor

    def get_columns(
        self,
        schema_name: str,
        table_name: str
    ) -> pd.DataFrame:

        query = f"""
        SELECT
            table_schema,
            table_name,
            column_name,
            data_type,
            ordinal_position
        FROM information_schema.columns
        WHERE table_schema = '{schema_name}'
          AND table_name = '{table_name}'
        ORDER BY ordinal_position
        """

        return self.query_executor.execute(query)

    def get_table_stats(
        self,
        schema_name: str,
        table_name: str
    ):

        query = f"""
        SELECT COUNT(*) AS row_count
        FROM {schema_name}.{table_name}
        """

        result = self.query_executor.execute(query)

        return {
            "row_count": int(
                result.iloc[0]["row_count"]
            )
        }

    def extract(
        self,
        schema_name: str,
        table_name: str
    ):

        columns = self.get_columns(
            schema_name,
            table_name
        )

        stats = self.get_table_stats(
            schema_name,
            table_name
        )

        return {
            "schema": schema_name,
            "table": table_name,
            "row_count": stats["row_count"],
            "columns": columns
        }