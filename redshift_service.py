# redshift_service.py

import pandas as pd
import psycopg2
import streamlit as st
from contextlib import contextmanager


class RedshiftService:

    def __init__(self):
        self.host = st.secrets["REDSHIFT_HOST"]
        self.port = int(st.secrets["REDSHIFT_PORT"])
        self.database = st.secrets["REDSHIFT_DB"]
        self.user = st.secrets["REDSHIFT_USER"]
        self.password = st.secrets["REDSHIFT_PASSWORD"]

    @contextmanager
    def get_connection(self):

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

    def execute_query(self, query):

        with self.get_connection() as conn:
            return pd.read_sql(query, conn)

    def test_connection(self):

        query = """
        SELECT
            current_database(),
            current_user;
        """

        return self.execute_query(query)

    def get_schemas(self):

        query = """
        SELECT DISTINCT schemaname
        FROM pg_table_def
        ORDER BY schemaname
        """

        return self.execute_query(query)

    def get_tables(self, schema):

        query = f"""
        SELECT DISTINCT tablename
        FROM pg_table_def
        WHERE schemaname = '{schema.lower()}'
        ORDER BY tablename
        """

        return self.execute_query(query)

    def load_metadata(self, schema, table):

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
        WHERE LOWER(schemaname) = LOWER('{schema}')
          AND LOWER(tablename) = LOWER('{table}')
        ORDER BY ordinal_position NULLS LAST
        """

        try:
            df = self.execute_query(query)

            print(f"Schema: {schema}")
            print(f"Table: {table}")
            print(f"Rows Returned: {len(df)}")

            return df

        except Exception as e:
            print(f"Metadata Error: {str(e)}")
            return pd.DataFrame()

    def get_row_count(self, schema, table):

        query = f"""
        SELECT COUNT(*) AS row_count
        FROM {schema}.{table}
        """

        df = self.execute_query(query)

        return int(df.iloc[0]["row_count"])

    def get_sample_data(self, schema, table, limit=100):

        query = f"""
        SELECT *
        FROM {schema}.{table}
        LIMIT {limit}
        """

        return self.execute_query(query)

    def validate_table(self, schema, table):

        query = f"""
        SELECT
            table_schema,
            table_name
        FROM information_schema.tables
        WHERE LOWER(table_schema)=LOWER('{schema}')
          AND LOWER(table_name)=LOWER('{table}')
        """

        return self.execute_query(query)

    def generate_table_profile(self, schema, table):

        metadata = self.load_metadata(schema, table)

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