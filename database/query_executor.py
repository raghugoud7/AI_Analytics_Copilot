import re

from database.redshift_service import RedshiftService


class QueryExecutor:

    BLOCKED_KEYWORDS = (
        "ALTER",
        "CREATE",
        "DELETE",
        "DROP",
        "GRANT",
        "INSERT",
        "MERGE",
        "REVOKE",
        "TRUNCATE",
        "UPDATE",
    )

    def __init__(self):
        self.redshift_service = RedshiftService()

    def validate_sql(self, sql: str) -> None:
        if not sql or not sql.strip():
            raise ValueError("SQL query cannot be empty.")

        normalized_sql = sql.strip()

        if not re.match(r"^(SELECT|WITH)\b", normalized_sql, flags=re.IGNORECASE):
            raise ValueError("Only SELECT statements and read-only CTEs are allowed.")

        for keyword in self.BLOCKED_KEYWORDS:
            pattern = rf"\b{re.escape(keyword)}\b"

            if re.search(pattern, normalized_sql, flags=re.IGNORECASE):
                raise ValueError(f"Blocked SQL keyword detected: {keyword}")

        statements = [statement.strip() for statement in normalized_sql.split(";") if statement.strip()]

        if len(statements) > 1:
            raise ValueError("Multiple SQL statements are not allowed.")

    def execute(self, sql: str):
        self.validate_sql(sql)
        return self.redshift_service.execute_query(sql)