import pandas as pd

from scipy.stats import pearsonr
from utils.privacy import remove_sensitive_columns


class CorrelationAnalyzer:

    def analyze(self, df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {"success": False, "error": "DataFrame is empty."}

        numeric_df = remove_sensitive_columns(df).select_dtypes(include="number")

        if numeric_df.shape[1] < 2:
            return {"success": False, "error": "Insufficient numeric columns."}

        correlations = []

        cols = numeric_df.columns.tolist()

        for i, c1 in enumerate(cols):
            for c2 in cols[i + 1 :]:
                # Clean both columns together to preserve row alignment.
                pair = (
                    numeric_df[[c1, c2]]
                    .replace([float("inf"), float("-inf")], float("nan"))
                    .dropna()
                )
                # Check the actual paired rows, not only the complete columns.
                if len(pair) < 3:
                    continue

                if pair[c1].nunique() < 2 or pair[c2].nunique() < 2:
                    continue

                r, p = pearsonr(
                    pair[c1].to_numpy(dtype=float),
                    pair[c2].to_numpy(dtype=float),
                )
                if pd.isna(r) or pd.isna(p):
                    continue

                correlations.append({
                    "column_1": c1,
                    "column_2": c2,
                    "correlation": round(float(r), 3),
                    "p_value": round(float(p), 5),
                    "significant": p < 0.05,
                    "strength": (
                        "Strong"
                        if abs(r) >= 0.7
                        else "Moderate"
                        if abs(r) >= 0.4
                        else "Weak"
                    ),
                })

        correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        return {
            "success": True,
            "correlation_count": len(correlations),
            "top_correlations": correlations[:20],
            "top_positive": [c for c in correlations if c["correlation"] > 0][:10],
            "top_negative": [c for c in correlations if c["correlation"] < 0][:10],
            "significant_correlations": [
                c for c in correlations if c["significant"]
            ][:20],
        }