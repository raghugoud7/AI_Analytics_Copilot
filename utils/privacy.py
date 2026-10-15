# utils/privacy.py

from typing import cast

import pandas as pd

from config.privacy import MANDATORY_COLUMNS
from utils.privacy_policy import PrivacyPolicy, normalize_column


def remove_sensitive_columns(
    df: pd.DataFrame,
    policy: PrivacyPolicy | None = None,
) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if not df.columns.is_unique:
        raise ValueError("Duplicate column names are unsupported.")

    blocked = {
        normalize_column(column)
        for column in MANDATORY_COLUMNS
    }

    if policy is not None:
        blocked.update(policy.blocked_names)

    approved_columns: list[str] = [
        column
        for column in df.columns
        if normalize_column(column) not in blocked
    ]

    # Use explicit list-typed columns to ensure a DataFrame is returned.
    # Cast to DataFrame for type-checkers that treat .loc[...] as Series-like
    # when the selection is ambiguous.
    return cast(pd.DataFrame, df.loc[:, approved_columns].copy())