from config.privacy import SENSITIVE_COLUMNS

import pandas as pd


def remove_sensitive_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    if df is None or df.empty:
        return df

    return df.drop(
        columns=list(SENSITIVE_COLUMNS),
        errors="ignore",
    )