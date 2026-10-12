import re

import duckdb
import pandas as pd

from utils.privacy import remove_sensitive_columns


class TrendAnalyzer:
    KPI_KEYWORDS = (
    "score",
    "quality",
    "rating",
    "ratio",
    "percentage",
    "percent",
    "duration",
    "performance",
    "accuracy",
    )
    DATE_KEYWORDS = ("date", "time", "timestamp", "created", "modified", "start", "end")
    DATE_EXCLUSIONS = (
        "id",
        "guid",
        "uuid",
        "key",
        "owner",
        "createdby",
        "modifiedby",
        "userid",
        "accountid",
        "contactid",
        "leadid",
        "audit",
        "etl",
        "refresh",
        "sync",
        "system",
    )
    KPI_EXCLUSIONS = ("id", "guid", "uuid", "key", "phone", "postcode", "zip", "year")

    @staticmethod
    def _safe_identifier(column_name: str) -> str:
        if not isinstance(column_name, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", column_name
        ):
            raise ValueError(f"Unsafe column name: {column_name}")
        return column_name

    def analyze(
        self,
        df: pd.DataFrame,
        top_points: int = 100,
        max_date_columns: int = 5,
    ) -> dict:
        if df is None or df.empty:
            return {"success": False, "error": "Empty dataframe."}

        df = remove_sensitive_columns(df).copy()
        top_points = max(1, min(int(top_points), 10_000))
        max_date_columns = max(1, min(int(max_date_columns), 20))

        candidate_cols = [
            col
            for col in df.columns
            if any(k in col.lower() for k in self.DATE_KEYWORDS)
            and not any(k in col.lower() for k in self.DATE_EXCLUSIONS)
        ]

        datetime_cols = []

        for col in candidate_cols:
            try:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    datetime_cols.append(col)
                    continue

                sample = df[col].dropna().head(500)

                if not sample.empty and (
                    pd.to_datetime(sample, errors="coerce", format="mixed")
                    .notna()
                    .mean()
                    >= 0.8
                ):
                    df[col] = pd.to_datetime(
                        df[col], errors="coerce", format="mixed"
                    )

                    if df[col].notna().any():
                        datetime_cols.append(col)

            except (TypeError, ValueError, OverflowError):
                pass

        if not datetime_cols:
            return {
                "success": False,
                "error": "No meaningful datetime column found.",
                "candidate_columns": candidate_cols,
            }

        numeric_cols = [
            col
            for col in df.select_dtypes(include="number").columns
            if not any(k in col.lower() for k in self.KPI_EXCLUSIONS)
        ]

        kpi_col = next(
            (
                col
                for col in numeric_cols
                if any(k in col.lower() for k in self.KPI_KEYWORDS)
            ),
            numeric_cols[0] if numeric_cols else None,
        )

        safe_kpi_col = self._safe_identifier(kpi_col) if kpi_col else None

        avg_kpi_sql = (
            f', ROUND(AVG("{safe_kpi_col}"), 2) AS avg_kpi'
            if safe_kpi_col
            else ""
        )

        conn = duckdb.connect()
        conn.register("df", df)

        trends = {}

        for date_col in datetime_cols[:max_date_columns]:
            safe_date_col = self._safe_identifier(date_col)

            try:
                monthly_df = conn.execute(
                    f"""
                    SELECT
                        DATE_TRUNC('month', "{safe_date_col}") AS period,
                        COUNT(*) AS record_count
                        {avg_kpi_sql}
                    FROM df
                    WHERE "{safe_date_col}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY 1 DESC
                    LIMIT {top_points}
                    """
                ).df()

                daily_df = conn.execute(
                    f"""
                    SELECT
                        CAST("{safe_date_col}" AS DATE) AS period,
                        COUNT(*) AS record_count
                        {avg_kpi_sql}
                    FROM df
                    WHERE "{safe_date_col}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY 1 DESC
                    LIMIT {top_points}
                   """
                ).df()

                trends[date_col] = {
                    "monthly_trend": monthly_df.to_dict("records"),
                    "daily_trend": daily_df.to_dict("records"),
                }

            except Exception as ex:
                trends[date_col] = {
                    "error": str(ex),
                    "monthly_trend": [],
                    "daily_trend": [],
                }

        conn.close()

        if not trends:
            return {"success": False, "error": "No trend analysis generated."}

        return {
            "success": True,
            "kpi_column": kpi_col,
            "datetime_columns": datetime_cols,
            "trends": trends,
        }