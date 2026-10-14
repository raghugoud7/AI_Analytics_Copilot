# analytics/segment_analyzer.py

import math
import warnings
import numpy as np
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
        target_col: str | None = None,
        min_group_records: int = 5,
        min_test_records: int = 30,
        max_cardinality: int = 100,
        higher_is_better: bool = True,
    ) -> dict:
        if not isinstance(df, pd.DataFrame) or df.empty:
            return {"success": False, "error": "DataFrame is empty or invalid."}

        df = remove_sensitive_columns(df)

        if df.empty:
            return {"success": False, "error": "No approved columns are available."}

        if not df.columns.is_unique:
            return {"success": False, "error": "Duplicate column names are unsupported."}

        settings = {
            "top_n": (top_n, 1),
            "max_dimensions": (max_dimensions, 1),
            "min_group_records": (min_group_records, 1),
            "min_test_records": (min_test_records, 2),
            "max_cardinality": (max_cardinality, 2),
        }

        for name, (value, minimum) in settings.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                return {
                    "success": False,
                    "error": f"{name} must be an integer of at least {minimum}.",
                }

        if not isinstance(higher_is_better, bool):
            return {"success": False, "error": "higher_is_better must be boolean."}

        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        if not numeric_cols:
            return {"success": False, "error": "No numeric columns found."}

        kpi = target_col

        if kpi is None:
            kpi = next(
                (
                    column
                    for column in numeric_cols
                    if any(keyword in str(column).lower() for keyword in self.KPI_KEYWORDS)
                ),
                None,
            )

        if kpi not in numeric_cols:
            return {
                "success": False,
                "error": "Select an approved numeric business measure for segmentation.",
                "available_targets": numeric_cols,
            }

        metric = df[kpi].astype(float)
        # replace infinities with NaN in a way that type checkers accept
        metric = metric.where(np.isfinite(metric), np.nan)

        if metric.notna().sum() < 2:
            return {"success": False, "error": "The target has too few valid values."}

        overall_avg = float(metric.mean())
        total_records = len(df)

        categorical_cols = [
            column
            for column, dtype in df.dtypes.items()
            if pd.api.types.is_object_dtype(dtype)
            or pd.api.types.is_string_dtype(dtype)
            or isinstance(dtype, pd.CategoricalDtype)
        ]

        if not categorical_cols:
            return {"success": False, "error": "No categorical columns found."}

        # Identify eligible dimensions before applying max_dimensions.
        candidates = []
        skipped = {}

        for column in categorical_cols:
            try:
                values = df[column].astype("string").str.strip()
                values = values.mask(values == "", pd.NA)
                cardinality = int(values.nunique(dropna=True))

                if cardinality < 2:
                    skipped[column] = "Fewer than two non-missing categories."
                elif cardinality > max_cardinality:
                    skipped[column] = f"Cardinality exceeds {max_cardinality}."
                else:
                    candidates.append(column)

            except (TypeError, ValueError) as ex:
                skipped[column] = f"Dimension preparation failed: {ex}"

        for column in candidates[max_dimensions:]:
            skipped[column] = "Excluded by max_dimensions."

        segments = {}

        with duckdb.connect(database=":memory:") as connection:
            for column in candidates[:max_dimensions]:
                try:
                    values = df[column].astype("string").str.strip()
                    values = values.mask(values == "", pd.NA)

                    # Fixed SQL identifiers avoid interpolating source column names.
                    source = pd.DataFrame(
                        {
                            "segment": values,
                            "metric": metric,
                        }
                    )
                    connection.register("segment_source", source)

                    # Aggregate all eligible groups before selecting top results.
                    result = connection.execute(
                        """
                        SELECT
                            segment,
                            COUNT(*) AS record_count,
                            COUNT(metric) AS valid_kpi_count,
                            AVG(metric) AS avg_kpi
                        FROM segment_source
                        WHERE segment IS NOT NULL
                        GROUP BY segment
                        HAVING COUNT(*) >= ?
                           AND COUNT(metric) >= 2
                        """,
                        [min_group_records],
                    ).df()

                    if len(result) < 2:
                        skipped[column] = (
                            "Fewer than two groups meet the record and valid-KPI thresholds."
                        )
                        continue

                    details = []
                    known_dimension = values.notna()

                    for row in result.to_dict(orient="records"):
                        value = row["segment"]
                        group_mask = values.eq(value).fillna(False)
                        other_mask = known_dimension & ~group_mask

                        group_values = metric.loc[group_mask].dropna()
                        other_values = metric.loc[other_mask].dropna()

                        p_value = None
                        test_status = "Insufficient Sample"

                        if (
                            len(group_values) >= min_test_records
                            and len(other_values) >= min_test_records
                        ):
                            if group_values.var() == 0 and other_values.var() == 0:
                                test_status = "Undefined Test: Constant Groups"
                            else:
                                try:
                                    with warnings.catch_warnings():
                                        warnings.simplefilter("error", RuntimeWarning)
                                        _, raw_p = ttest_ind(
                                            group_values.to_numpy(dtype=float),
                                            other_values.to_numpy(dtype=float),
                                            equal_var=False,
                                        )

                                    if math.isfinite(float(raw_p)):
                                        p_value = float(raw_p)
                                        test_status = "Tested"
                                    else:
                                        test_status = "Undefined Test"

                                except (RuntimeWarning, TypeError, ValueError) as ex:
                                    test_status = f"Test Unavailable: {ex}"

                        avg_kpi = float(row["avg_kpi"])

                        details.append(
                            {
                                "segment": value,
                                "record_count": int(row["record_count"]),
                                "valid_kpi_count": int(row["valid_kpi_count"]),
                                "segment_percentage": round(
                                    int(row["record_count"]) * 100 / total_records, 2
                                ),
                                "avg_kpi": round(avg_kpi, 2),
                                "difference_from_average": round(avg_kpi - overall_avg, 2),
                                "sample_size": len(group_values),
                                "comparison_size": len(other_values),
                                "comparison_average": (
                                    round(float(other_values.mean()), 2)
                                    if not other_values.empty
                                    else None
                                ),
                                "p_value": p_value,
                                "test_status": test_status,
                                "_ranking_value": avg_kpi,
                            }
                        )

                    # Preserve full-precision averages for ranking.
                    details.sort(
                        key=lambda item: item["_ranking_value"],
                        reverse=higher_is_better,
                    )

                    segments[column] = {
                        "cardinality": int(values.nunique(dropna=True)),
                        "overall_kpi": round(overall_avg, 2),
                        "missing_dimension_records": int(values.isna().sum()),
                        "eligible_segment_count": len(details),
                        "all_segments": details,
                    }

                except Exception as ex:
                    skipped[column] = f"Aggregation failed: {ex}"
                    print(f"Segment analysis failed for {column}: {ex}")

        # Adjust across all successfully tested groups in this analysis run.
        test_count = sum(
            item["p_value"] is not None
            for dimension in segments.values()
            for item in dimension["all_segments"]
        )

        for dimension in segments.values():
            details = dimension["all_segments"]

            for item in details:
                raw_p = item["p_value"]
                adjusted_p = min(raw_p * test_count, 1.0) if raw_p is not None else None

                item["adjusted_p_value"] = adjusted_p
                item["significant"] = adjusted_p is not None and adjusted_p <= 0.05
                item["significance"] = (
                    item["test_status"]
                    if adjusted_p is None
                    else "Highly Significant"
                    if adjusted_p <= 0.001
                    else "Significant"
                    if adjusted_p <= 0.05
                    else "Not Significant"
                )
                item.pop("_ranking_value")

            dimension["best_segment"] = details[0]
            dimension["worst_segment"] = details[-1]
            dimension["top_segments"] = details[:top_n]
            dimension["displayed_segment_percentage"] = round(
                sum(item["segment_percentage"] for item in details[:top_n]), 2
            )

        return {
            "success": True,
            "target_kpi": kpi,
            "overall_kpi": round(overall_avg, 2),
            "higher_is_better": higher_is_better,
            "dimensions_analyzed": len(segments),
            "segments": segments,
            "skipped_dimensions": skipped,
            "significance_method": "Welch test with Bonferroni adjustment",
            "significance_test_count": test_count,
            "percentage_denominator": "All rows in the loaded sample",
            "message": (
                "Segment analysis completed."
                if segments
                else "No eligible segment comparisons were found. Check skipped_dimensions."
            ),
        }