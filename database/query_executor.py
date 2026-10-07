# database/query_executor.py

import pandas as pd

from database.redshift_service import (
    RedshiftService
)


class QueryExecutor:

    BLOCKED_KEYWORDS = [
        "DROP",
        "DELETE",
        "UPDATE",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "INSERT",
        "GRANT",
        "REVOKE"
    ]

    def __init__(self):

        self.redshift = RedshiftService()

    def validate_sql(
        self,
        sql: str
    ):

        upper_sql = sql.upper()

        for keyword in self.BLOCKED_KEYWORDS:

            if keyword in upper_sql:

                raise ValueError(
                    f"Blocked SQL keyword detected: {keyword}"
                )

    def execute(
        self,
        sql: str
    ) -> pd.DataFrame:

        self.validate_sql(sql)

        return self.redshift.execute_query(sql)