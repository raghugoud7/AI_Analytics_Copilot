import pandas as pd

from utils.privacy import remove_sensitive_columns


class DriverAnalyzer:

    def analyze(
        self,
        df: pd.DataFrame,
        target_col: str = "overall_total_score__c",
    ) -> dict:
        if df is None or df.empty:
            return {"success": False, "error": "DataFrame is empty."}

        df = remove_sensitive_columns(df).copy()

        if target_col not in df.columns:
            return {"success": False, "error": f"{target_col} not found."}

        numeric_df = df.select_dtypes(include="number")

        if target_col not in numeric_df.columns:
            return {"success": False, "error": f"{target_col} is not numeric."}

        corr = (
            numeric_df.corr()[target_col]
            .drop(target_col)
            .dropna()
            .sort_values(ascending=False)
        )

        positive = [
            {"driver": col, "correlation": round(float(val), 3)}
            for col, val in corr.items()
            if val > 0
        ]

        negative = [
            {"driver": col, "correlation": round(float(val), 3)}
            for col, val in corr.sort_values().items()
            if val < 0
        ]

        return {
            "success": True,
            "target": target_col,
            "driver_count": len(corr),
            "strongest_positive": positive[0] if positive else None,
            "strongest_negative": negative[0] if negative else None,
            "top_positive_drivers": positive[:10],
            "top_negative_drivers": negative[:10],
        }