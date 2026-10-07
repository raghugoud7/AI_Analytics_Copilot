# database/redshift_service.py

import json
import os
import re
from contextlib import contextmanager

import pandas as pd
import psycopg2
import streamlit as st


class RedshiftService:

    def __init__(self):
        secrets = getattr(st, "secrets", {})

        self.host = secrets.get("REDSHIFT_HOST") or os.getenv("REDSHIFT_HOST")
        self.port_value = secrets.get("REDSHIFT_PORT") or os.getenv("REDSHIFT_PORT")
        self.database = secrets.get("REDSHIFT_DB") or os.getenv("REDSHIFT_DB")
        self.user = secrets.get("REDSHIFT_USER") or os.getenv("REDSHIFT_USER")
        self.password = secrets.get("REDSHIFT_PASSWORD") or os.getenv("REDSHIFT_PASSWORD")

        self.port = int(self.port_value) if self.port_value else None
        self.config_complete = all([
            self.host,
            self.port,
            self.database,
            self.user,
            self.password,
        ])

    # ======================================================
    # Connection
    # ======================================================

    @contextmanager
    def get_connection(self):

        if not self.config_complete:
            raise ValueError(
                "Missing Redshift configuration. Set Streamlit secrets or environment variables for REDSHIFT_HOST, REDSHIFT_PORT, REDSHIFT_DB, REDSHIFT_USER, and REDSHIFT_PASSWORD."
            )

        conn = None

        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.database,
                user=self.user,
                password=self.password
            )

            yield conn

        finally:
            if conn:
                conn.close()

    # ======================================================
    # Helpers
    # ======================================================

    def _validate_identifier(self, identifier):

        pattern = r"^[A-Za-z0-9_]+$"

        if not re.match(pattern, identifier):
            raise ValueError(
                f"Invalid identifier: {identifier}"
            )

        return identifier

    def execute_query(self, query):

        with self.get_connection() as conn:
            return pd.read_sql(query, conn)

    # ======================================================
    # Connection Tests
    # ======================================================

    def test_connection(self):

        query = """
        SELECT
            current_database(),
            current_user
        """

        return self.execute_query(query)

    # ======================================================
    # Schema Discovery
    # ======================================================

    def get_schemas(self):

        query = """
        SELECT DISTINCT schemaname
        FROM pg_table_def
        ORDER BY schemaname
        """

        return self.execute_query(query)

    def get_tables(self, schema):

        schema = self._validate_identifier(schema)

        query = f"""
        SELECT DISTINCT
            tablename
        FROM pg_table_def
        WHERE schemaname = '{schema}'
        ORDER BY tablename
        """

        return self.execute_query(query)

    def validate_table(self, schema, table):

        schema = self._validate_identifier(schema)
        table = self._validate_identifier(table)

        query = f"""
        SELECT
            table_schema,
            table_name
        FROM information_schema.tables
        WHERE LOWER(table_schema)=LOWER('{schema}')
        AND LOWER(table_name)=LOWER('{table}')
        """

        return self.execute_query(query)

    # ======================================================
    # Metadata
    # ======================================================

    def load_metadata(self, schema, table):

        schema = self._validate_identifier(schema)
        table = self._validate_identifier(table)

        query = f"""
        SELECT
            schemaname,
            tablename,
            "column" AS column_name,
            type AS data_type,
            encoding,
            distkey,
            sortkey,
            notnull
        FROM pg_table_def
        WHERE LOWER(schemaname)=LOWER('{schema}')
        AND LOWER(tablename)=LOWER('{table}')
        ORDER BY column_name
        """

        try:

            df = self.execute_query(query)

            return df

        except Exception as ex:

            st.error(
                f"Metadata load failed: {str(ex)}"
            )

            return pd.DataFrame()

    # ======================================================
    # Data Access
    # ======================================================

    def get_row_count(self, schema, table):

        schema = self._validate_identifier(schema)
        table = self._validate_identifier(table)

        query = f"""
        SELECT COUNT(*) AS row_count
        FROM {schema}.{table}
        """

        df = self.execute_query(query)

        return int(df.iloc[0]["row_count"])

    def get_sample_data(
        self,
        schema,
        table,
        limit=1000
    ):

        schema = self._validate_identifier(schema)
        table = self._validate_identifier(table)

        query = f"""
        SELECT *
        FROM {schema}.{table}
        LIMIT {limit}
        """

        return self.execute_query(query)

    # ======================================================
    # Profiling Helpers
    # ======================================================

    def get_top_values(
        self,
        schema,
        table,
        column,
        limit=20
    ):

        schema = self._validate_identifier(schema)
        table = self._validate_identifier(table)
        column = self._validate_identifier(column)

        query = f"""
        SELECT
            {column},
            COUNT(*) AS frequency
        FROM {schema}.{table}
        GROUP BY 1
        ORDER BY frequency DESC
        LIMIT {limit}
        """

        return self.execute_query(query)

    def get_date_range(
        self,
        schema,
        table,
        date_column
    ):

        schema = self._validate_identifier(schema)
        table = self._validate_identifier(table)
        date_column = self._validate_identifier(date_column)

        query = f"""
        SELECT
            MIN({date_column}) AS min_date,
            MAX({date_column}) AS max_date
        FROM {schema}.{table}
        """

        return self.execute_query(query)

    def get_numeric_summary(
        self,
        schema,
        table,
        column
    ):

        schema = self._validate_identifier(schema)
        table = self._validate_identifier(table)
        column = self._validate_identifier(column)

        query = f"""
        SELECT
            COUNT(*) AS row_count,
            AVG({column}) AS avg_value,
            MIN({column}) AS min_value,
            MAX({column}) AS max_value
        FROM {schema}.{table}
        """

        return self.execute_query(query)

    # ======================================================
    # Metadata Export
    # ======================================================

    def export_metadata_json(
        self,
        schema,
        table,
        output_file="metadata/metadata.json"
    ):

        metadata = self.load_metadata(
            schema,
            table
        )

        result = {
            "schema": schema,
            "table": table,
            "column_count": len(metadata),
            "columns": metadata.to_dict("records")
        }

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                result,
                f,
                indent=4
            )

        return output_file

    # ======================================================
    # Table Profile
    # ======================================================

    def generate_table_profile(
        self,
        schema,
        table
    ):

        metadata = self.load_metadata(
            schema,
            table
        )

        row_count = self.get_row_count(
            schema,
            table
        )

        sample = self.get_sample_data(
            schema,
            table,
            limit=100
        )

        return {
            "schema": schema,
            "table": table,
            "row_count": row_count,
            "column_count": len(metadata),
            "columns": metadata[
                ["column_name", "data_type"]
            ].to_dict("records"),
            "sample_shape": sample.shape
        }