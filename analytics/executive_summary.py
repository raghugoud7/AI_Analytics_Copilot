import pandas as pd

from utils.privacy import remove_sensitive_columns


class ExecutiveSummaryAnalyzer:
    def analyze(
        self,
        df: pd.DataFrame,
        total_rows: int | None = None,
    ) -> dict:
        df = remove_sensitive_columns(df)

        if df is None or df.empty:
            return {"success": False, "error": "DataFrame is empty."}

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        categorical_cols = df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()
        datetime_cols = df.select_dtypes(
            include=["datetime64[ns]"]
        ).columns.tolist()

        missing_pct = df.isna().mean().mul(100).round(2)

        high_null_columns = (
            missing_pct[missing_pct > 0]
            .sort_values(ascending=False)
            .head(20)
            .to_dict()
        )

        high_cardinality_columns = {
            c: int(df[c].nunique(dropna=True))
            for c in categorical_cols
            if df[c].nunique(dropna=True) > 50
        }

        constant_columns = [
            c for c in df.columns if df[c].nunique(dropna=False) <= 1
        ]

        return {
            "success": True,
            "overview": {
                "total_rows": total_rows or len(df),
                "sample_rows": len(df),
                "total_columns": len(df.columns),
                "numeric_columns": len(numeric_cols),
                "categorical_columns": len(categorical_cols),
                "datetime_columns": len(datetime_cols),
            },
            "data_quality": {
                "missing_values": int(df.isna().sum().sum()),
                "missing_percentage": round(
                    df.isna().sum().sum() / (len(df) * len(df.columns)) * 100,
                    2,
                ),
                "duplicate_rows": int(df.duplicated().sum()),
                "duplicate_percentage": round(df.duplicated().mean() * 100, 2),
                "constant_columns": constant_columns,
            },
            "column_analysis": {
                "high_null_columns": high_null_columns,
                "high_cardinality_columns": high_cardinality_columns,
            },
            "memory_mb": round(df.memory_usage(deep=True).sum() / 1024**2, 2),
            "columns": df.columns.tolist(),
            "top_numeric_columns": numeric_cols[:20],
            "top_categorical_columns": categorical_cols[:20],
        }