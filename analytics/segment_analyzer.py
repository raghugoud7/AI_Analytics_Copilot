import duckdb
import pandas as pd

from scipy.stats import ttest_ind
from utils.privacy import remove_sensitive_columns


class SegmentAnalyzer:

    KPI_KEYWORDS = (
        "score",
        "quality",
        "rating",
        "ratio",
        "percentage",
        "duration",
        "performance",
    )

    def analyze(
        self,
        df: pd.DataFrame,
        top_n: int = 10,
        max_dimensions: int = 15,
    ) -> dict:

        if df is None or df.empty:
            return {"success": False, "error": "Empty dataframe."}

        df = remove_sensitive_columns(df).copy()

        nums = df.select_dtypes(include="number").columns.tolist()
        cats = df.select_dtypes(include=["object", "category"]).columns.tolist()

        if not nums:
            return {"success": False, "error": "No numeric columns found."}

        if not cats:
            return {"success": False, "error": "No categorical columns found."}

        kpi = next(
            (c for c in nums if any(k in c.lower() for k in self.KPI_KEYWORDS)),
            nums[0],
        )

        overall_avg = round(df[kpi].mean(), 2)
        total_records = len(df)
        segments = {}

        for col in cats[:max_dimensions]:
            try:
                cardinality = df[col].nunique(dropna=True)

                if cardinality < 2 or cardinality > 100:
                    continue

                result = duckdb.query(f"""
                    SELECT
                        "{col}" AS segment,
                        COUNT(*) AS record_count,
                        ROUND(AVG("{kpi}"), 2) AS avg_kpi
                    FROM df
                    WHERE "{col}" IS NOT NULL
                    GROUP BY 1
                    HAVING COUNT(*) >= 5
                    ORDER BY avg_kpi DESC
                    LIMIT {top_n}
                """).to_df()

                if result.empty:
                    continue

                details = []

                for _, row in result.iterrows():
                    value = row["segment"]

                    segment_df = df[df[col] == value]
                    other_df = df[df[col] != value]

                    segment_values = segment_df[kpi].dropna()
                    other_values = other_df[kpi].dropna()

                    min_sample_size = 30
                    p = None
                    significant = False
                    significance = "Insufficient Sample"

                    if (
                        len(segment_values) >= min_sample_size
                        and len(other_values) >= min_sample_size
                    ):
                        try:
                            _, p = ttest_ind(
                                segment_values,
                                other_values,
                                equal_var=False,
                            )

                            if pd.notna(p):
                                p = round(float(p), 6)
                                significant = p <= 0.05
                                significance = (
                                    "Highly Significant"
                                    if p <= 0.001
                                    else "Significant"
                                    if p <= 0.05
                                    else "Not Significant"
                                )
                            else:
                                p = None

                        except Exception:
                            p = None

                    details.append({
                        "segment": value,
                        "record_count": int(row["record_count"]),
                        "segment_percentage": round(row["record_count"] * 100 / total_records, 2),
                        "avg_kpi": float(row["avg_kpi"]),
                        "difference_from_average": round(row["avg_kpi"] - overall_avg, 2),
                        "p_value": round(float(p), 6) if p is not None else None,
                        "significant": p is not None and p <= 0.05,
                        "significance": (
                            "Highly Significant"
                            if p is not None and p <= 0.001
                            else "Significant"
                            if p is not None and p <= 0.05
                            else "Not Significant"
                        ),
                    })

                if details:
                    segments[col] = {
                        "cardinality": cardinality,
                        "overall_kpi": overall_avg,
                        "best_segment": details[0],
                        "worst_segment": details[-1],
                        "top_segments": details,
                    }

            except Exception:
                continue

        return {
            "success": True,
            "target_kpi": kpi,
            "overall_kpi": overall_avg,
            "dimensions_analyzed": len(segments),
            "segments": segments,
        }