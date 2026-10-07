# analytics/profiler.py

import pandas as pd


class DataProfiler:

    @staticmethod
    def generate_profile(df: pd.DataFrame) -> dict:

        profile = {}

        profile["row_count"] = len(df)

        profile["column_count"] = len(df.columns)

        profile["columns"] = list(df.columns)

        profile["data_types"] = (
            df.dtypes.astype(str).to_dict()
        )

        profile["missing_values"] = (
            df.isnull().sum().to_dict()
        )

        profile["missing_percentage"] = (
            (
                df.isnull().sum()
                / len(df)
                * 100
            ).round(2).to_dict()
        )

        numeric_df = df.select_dtypes(
            include="number"
        )

        if not numeric_df.empty:

            profile["statistics"] = (
                numeric_df
                .describe()
                .to_dict()
            )

            profile["correlation"] = (
                numeric_df
                .corr()
                .round(2)
                .to_dict()
            )

        return profile