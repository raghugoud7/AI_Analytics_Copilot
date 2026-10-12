import pandas as pd

from utils.privacy import remove_sensitive_columns


class OutlierDetector:

    def analyze(self, df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {"success": False, "error": "Empty dataframe."}

        df = remove_sensitive_columns(df).copy()

        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        if not numeric_cols:
            return {"success": False, "error": "No numeric columns found."}

        outlier_summary = {}

        for col in numeric_cols:
            series = df[col].dropna()

            if len(series) < 10:
                continue

            q1, q3 = series.quantile([0.25, 0.75])
            iqr = q3 - q1

            lower = q1 - (1.5 * iqr)
            upper = q3 + (1.5 * iqr)

            outliers = series[(series < lower) | (series > upper)]

            if outliers.empty:
                continue

            count = len(outliers)

            outlier_summary[col] = {
                "outlier_count": count,
                "outlier_percentage": round(count / len(series) * 100, 2),
                "lower_bound": round(float(lower), 2),
                "upper_bound": round(float(upper), 2),
                "minimum": round(float(series.min()), 2),
                "maximum": round(float(series.max()), 2),
            }

        ranked = sorted(
            outlier_summary.items(),
            key=lambda x: x[1]["outlier_percentage"],
            reverse=True,
        )

        return {
            "success": True,
            "numeric_columns": len(numeric_cols),
            "outlier_columns": len(outlier_summary),
            "top_outliers": dict(ranked[:10]),
            "all_outliers": outlier_summary,
        }