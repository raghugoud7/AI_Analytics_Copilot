# analytics/driver_analyzer.py

import math

import pandas as pd

from utils.privacy import remove_sensitive_columns


class DriverAnalyzer:
    @staticmethod
    def _strength(correlation: float) -> str:
        value = abs(correlation)

        if value >= 0.80:
            return "Very Strong"
        if value >= 0.60:
            return "Strong"
        if value >= 0.40:
            return "Moderate"
        if value >= 0.20:
            return "Weak"

        return "Very Weak"

    def analyze(
        self,
        df: pd.DataFrame,
        target_col: str | None = None,
        top_n: int = 10,
        min_records: int = 3,
        min_correlation: float = 0.0,
    ) -> dict:
        if not isinstance(df, pd.DataFrame) or df.empty:
            return {"success": False, "error": "DataFrame is empty or invalid."}

        df = remove_sensitive_columns(df)

        if df.empty:
            return {"success": False, "error": "No approved columns are available."}

        if not df.columns.is_unique:
            return {"success": False, "error": "Duplicate column names are not supported."}

        if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1:
            return {"success": False, "error": "top_n must be a positive integer."}

        if (
            not isinstance(min_records, int)
            or isinstance(min_records, bool)
            or min_records < 3
        ):
            return {"success": False, "error": "min_records must be at least 3."}

        if not 0 <= min_correlation <= 1:
            return {"success": False, "error": "min_correlation must be between 0 and 1."}

        numeric_df = df.select_dtypes(include="number").replace(
            [float("inf"), float("-inf")],
            float("nan"),
        )

        eligible_targets = [
            column
            for column in numeric_df.columns
            if numeric_df[column].count() >= min_records
            and numeric_df[column].nunique(dropna=True) >= 2
        ]

        if target_col is None:
            return {
                "success": False,
                "error": "Select a numeric business measure for driver analysis.",
                "available_targets": eligible_targets,
            }

        if target_col not in eligible_targets:
            return {
                "success": False,
                "error": (
                    "The selected target must be an approved numeric column with "
                    f"at least {min_records} valid records and two distinct values."
                ),
                "available_targets": eligible_targets,
            }

        drivers = []
        skipped_columns = {}

        for column in numeric_df.columns:
            if column == target_col:
                continue

            pair = numeric_df[[column, target_col]].dropna()

            if len(pair) < min_records:
                skipped_columns[column] = "Insufficient paired records."
                continue

            if pair[column].nunique() < 2 or pair[target_col].nunique() < 2:
                skipped_columns[column] = "Constant values in paired records."
                continue

            correlation = float(
                pair[column].astype(float).corr(pair[target_col].astype(float))
            )

            if not math.isfinite(correlation):
                skipped_columns[column] = "Undefined correlation."
                continue

            if correlation == 0 or abs(correlation) < min_correlation:
                continue

            drivers.append(
                {
                    "driver": column,
                    "correlation": correlation,
                    "strength": self._strength(correlation),
                    "sample_size": len(pair),
                }
            )

        # Rank using full precision before rounding for display.
        positive = sorted(
            [driver for driver in drivers if driver["correlation"] > 0],
            key=lambda driver: driver["correlation"],
            reverse=True,
        )

        negative = sorted(
            [driver for driver in drivers if driver["correlation"] < 0],
            key=lambda driver: driver["correlation"],
        )

        for driver in drivers:
            driver["correlation"] = round(driver["correlation"], 6)

        return {
            "success": True,
            "target": target_col,
            "driver_count": len(drivers),
            "available_targets": eligible_targets,
            "strongest_positive": positive[0] if positive else None,
            "strongest_negative": negative[0] if negative else None,
            "top_positive_drivers": positive[:top_n],
            "top_negative_drivers": negative[:top_n],
            "skipped_columns": skipped_columns,
            "recommendations": [],
            "message": (
                "Relationships are associations, not evidence of causal impact."
                if drivers
                else "No valid relationships met the selected criteria."
            ),
        }