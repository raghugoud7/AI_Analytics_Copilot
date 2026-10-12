# agents/sql_validator_agent.py

import re
from config.privacy import SENSITIVE_COLUMNS

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
        sql_lower = sql.lower()

        if re.search(
            r"select\s+\*",
            sql_lower
        ):

            return {
                "success": False,
                "error": (
                    "SELECT * is not allowed. "
                    "Please select explicit columns."
                )
            }
            
            
        for column in SENSITIVE_COLUMNS:
            pattern = rf"\b{re.escape(column.lower())}\b"
            if re.search(pattern,sql_lower):

                return {
                    "success": False,
                    "error": (
                        f"Sensitive column not allowed: "
                        f"{column}"
                    )
                }

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

        if not re.match(
            r"^\s*(SELECT|WITH)\b",
            sql_upper,
        ):
            return {
                "success": False,
                "error": (
                    "Only SELECT queries "
                    "and CTEs are allowed."
                )
            }

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
        

    def apply_brand_filter(
        self,
        sql: str,
        brand: str | None,
    ) -> str:

        if not brand:
            return sql

        sql_upper = sql.upper()

        if "BRAND__C" in sql_upper:
            return sql

        safe_brand = brand.replace(
            "'",
            "''",
        )

        if "WHERE" in sql_upper:

            return re.sub(
                r"\bWHERE\b",
                (
                    f"WHERE brand__c = '{safe_brand}' "
                    f"AND "
                ),
                sql,
                count=1,
                flags=re.IGNORECASE,
            )

        return sql.rstrip(";") + (
            f"\nWHERE brand__c = '{safe_brand}'"
        )