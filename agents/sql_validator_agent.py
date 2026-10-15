# agents/sql_validator_agent.py

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope
from utils.privacy_policy import PrivacyPolicy, normalize_column
from config.privacy import SENSITIVE_COLUMNS


class SQLValidatorAgent:
    
    def __init__(self, privacy_policy: PrivacyPolicy | None = None):
        self.privacy_policy = privacy_policy
        
    BLOCKED_NODES = {
        "alter",
        "command",
        "copy",
        "create",
        "delete",
        "drop",
        "execute",
        "grant",
        "insert",
        "into",
        "merge",
        "revoke",
        "transaction",
        "truncate",
        "truncatetable",
        "update",
        "use",
    }

    PLACEHOLDER_TABLES = {
        "your_table_name",
        "table_name_here",
        "sample_table",
        "example_table",
    }

    @staticmethod
    def _parse(sql: str):
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("Empty SQL query generated.")

        statements = [
            statement
            for statement in sqlglot.parse(sql, read="redshift")
            if statement is not None
        ]

        if len(statements) != 1:
            raise ValueError("Exactly one SQL statement is allowed.")

        return statements[0]

    def _check_tree(self, tree):
        if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
            raise ValueError("Only read-only SELECT queries and CTEs are allowed.")

        sensitive = {normalize_column(column) for column in SENSITIVE_COLUMNS}
        if self.privacy_policy is not None:
            sensitive.update(self.privacy_policy.blocked_names)

        for node in tree.walk():
            if node.key.lower() in self.BLOCKED_NODES:
                raise ValueError(f"Blocked SQL operation: {node.key.upper()}")

        if tree.find(exp.Join) is not None:
            raise ValueError(
                "Joins are not enabled. Use the loaded table or an approved "
                "database view until join-scoping rules are configured."
            )

        for with_clause in tree.find_all(exp.With):
            if with_clause.args.get("recursive"):
                raise ValueError("Recursive CTEs are not allowed.")

        for column in tree.find_all(exp.Column):
            if normalize_column(column.name) in sensitive:
                raise ValueError(
                    f"Column excluded by the privacy policy: {column.name}"
                )

        for star in tree.find_all(exp.Star):
            # COUNT(*) is allowed; SELECT * and alias.* are not.
            if not isinstance(star.parent, exp.Count):
                raise ValueError("Wildcard selection is not allowed. Use explicit columns.")

        for table in tree.find_all(exp.Table):
            if not isinstance(table.this, exp.Identifier):
                raise ValueError("Table-valued functions are not allowed.")

            if table.name.casefold() in self.PLACEHOLDER_TABLES:
                raise ValueError("SQL contains a placeholder table name.")

        for select in tree.find_all(exp.Select):
            if select.args.get("into"):
                raise ValueError("SELECT INTO is not allowed.")

            if select.args.get("locks"):
                raise ValueError("Locking SELECT queries are not allowed.")

    def validate(self, sql: str) -> dict:
        try:
            tree = self._parse(sql)
            self._check_tree(tree)

            return {
                "success": True,
                "sql": tree.sql(dialect="redshift"),
            }

        except Exception as ex:
            return {
                "success": False,
                "error": str(ex),
            }

    def apply_brand_filter(
        self,
        sql: str,
        brand: str | None,
        schema_name: str | None = None,
        table_name: str | None = None,
    ) -> str:
        if not isinstance(brand, str) or not brand.strip():
            raise ValueError("A loaded brand is required.")

        if not schema_name or not table_name:
            raise ValueError("A loaded schema and table are required for SQL scoping.")

        tree = self._parse(sql)
        self._check_tree(tree)

        expected_schema = schema_name.casefold()
        expected_table = table_name.casefold()
        physical_sources = 0

        scopes = list(traverse_scope(tree))

        if not scopes:
            raise ValueError("Unable to resolve SQL query scopes.")

        for scope in scopes:
            physical_tables = [
                source
                for _, source in scope.selected_sources.values()
                if isinstance(source, exp.Table)
            ]

            if not physical_tables:
                continue

            if not isinstance(scope.expression, exp.Select):
                raise ValueError("Unsupported physical-table query scope.")

            for source in physical_tables:
                if source.catalog:
                    raise ValueError("Cross-database queries are not allowed.")

                if source.name.casefold() != expected_table:
                    raise ValueError(
                        f"Only the loaded table is allowed: {schema_name}.{table_name}"
                    )

                if source.db and source.db.casefold() != expected_schema:
                    raise ValueError(
                        f"Only the loaded schema is allowed: {schema_name}"
                    )

                # Explicitly qualify unqualified physical table references.
                if not source.db:
                    source.set(
                        "db",
                        exp.Identifier(this=schema_name, quoted=True),
                    )

                qualifier = source.alias or source.name

                predicate = exp.EQ(
                    this=exp.Column(
                        this=exp.Identifier(this="brand__c", quoted=True),
                        table=exp.Identifier(this=qualifier, quoted=True),
                    ),
                    expression=exp.Literal.string(brand),
                )

                # Append with AND, preserving existing predicate grouping.
                # Never skip enforcement merely because brand__c is mentioned.
                scope.expression.where(
                    predicate,
                    append=True,
                    copy=False,
                )

                physical_sources += 1

        if physical_sources == 0:
            raise ValueError("The query must read from the loaded physical table.")

        scoped_sql = tree.sql(dialect="redshift")
        validation = self.validate(scoped_sql)

        if not validation["success"]:
            raise ValueError(validation["error"])

        return validation["sql"]