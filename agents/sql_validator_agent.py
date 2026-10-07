# agents/sql_validator_agent.py

import re


class SQLValidatorAgent:

    BLOCKED_KEYWORDS = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "GRANT",
        "REVOKE",
        "MERGE"
    ]

    def validate(
        self,
        sql: str
    ) -> dict:

        if not sql:

            return {
                "success": False,
                "error": "Empty SQL query generated."
            }

        sql = sql.strip()

        sql_upper = sql.upper()

        # ----------------------------------
        # Block Dangerous Statements
        # ----------------------------------

        for keyword in self.BLOCKED_KEYWORDS:

            pattern = rf"\b{keyword}\b"

            if re.search(
                pattern,
                sql_upper
            ):

                return {
                    "success": False,
                    "error": (
                        f"Blocked SQL operation detected: "
                        f"{keyword}"
                    )
                }

        # ----------------------------------
        # Only Allow SELECT Queries
        # ----------------------------------

        if not sql_upper.startswith(
            "SELECT"
        ):

            return {
                "success": False,
                "error": (
                    "Only SELECT queries are allowed."
                )
            }

        # ----------------------------------
        # Placeholder Tables
        # ----------------------------------

        placeholders = [
            "YOUR_TABLE_NAME",
            "TABLE_NAME_HERE",
            "SAMPLE_TABLE",
            "EXAMPLE_TABLE"
        ]

        for placeholder in placeholders:

            if placeholder in sql_upper:

                return {
                    "success": False,
                    "error": (
                        "SQL contains placeholder "
                        "table names."
                    )
                }

        # ----------------------------------
        # Multiple Statements
        # ----------------------------------

        if sql.count(";") > 1:

            return {
                "success": False,
                "error": (
                    "Multiple SQL statements "
                    "are not allowed."
                )
            }

        # ----------------------------------
        # Success
        # ----------------------------------

        return {
            "success": True,
            "sql": sql
        }