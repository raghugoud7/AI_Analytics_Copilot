# utils/privacy_policy.py

import hashlib
import json
from dataclasses import dataclass

import pandas as pd

from config.privacy import (
    MANDATORY_COLUMNS,
    SECONDARY_PII_COLUMNS,
    TABLE_PRIVACY_RULES,
)


def normalize_column(value: str) -> str:
    return str(value).strip().casefold()


def _normalize_columns(columns) -> set[str]:
    return {normalize_column(column) for column in columns}


def dataset_key(
    schema_name: str,
    table_name: str,
    columns: list[str],
) -> str:
    payload = {
        "schema": schema_name,
        "table": table_name,
        "columns": columns,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PrivacyPolicy:
    dataset_id: str
    source_columns: tuple[str, ...]
    mandatory_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]

    @property
    def blocked_names(self) -> frozenset[str]:
        return frozenset(
            normalize_column(column)
            for column in self.mandatory_columns + self.optional_columns
        )

    @property
    def approved_columns(self) -> tuple[str, ...]:
        return tuple(
            column
            for column in self.source_columns
            if normalize_column(column) not in self.blocked_names
        )

    @property
    def fingerprint(self) -> str:
        payload = {
            "version": 2,
            "dataset": self.dataset_id,
            "source_columns": self.source_columns,
            "blocked_columns": sorted(self.blocked_names),
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def detection_lists(
    report: pd.DataFrame,
) -> tuple[list[str], list[str], list[str]]:
    """Return detected mandatory fields, review fields, and skipped dates."""
    if not isinstance(report, pd.DataFrame):
        raise TypeError("Detection report must be a DataFrame.")

    if not {"column", "action"}.issubset(report.columns):
        raise ValueError("Detection report must contain column and action.")

    def columns_for(action: str) -> list[str]:
        return (
            report.loc[report["action"].eq(action), "column"]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .tolist()
        )

    return (
        columns_for("MANDATORY_REMOVE"),
        columns_for("REVIEW"),
        columns_for("SKIPPED_DATE"),
    )


def classify_columns(
    columns: list[str],
    table_key: str,
    detected_mandatory: list[str] | None = None,
    detected_suggested: list[str] | None = None,
    date_columns: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    rules = TABLE_PRIVACY_RULES.get(table_key.casefold(), {})

    mandatory_names = (
        _normalize_columns(MANDATORY_COLUMNS)
        | _normalize_columns(rules.get("mandatory", []))
        | _normalize_columns(detected_mandatory or [])
    )

    suggested_names = (
        _normalize_columns(SECONDARY_PII_COLUMNS)
        | _normalize_columns(rules.get("suggested", []))
        | _normalize_columns(detected_suggested or [])
    )

    date_names = _normalize_columns(date_columns or [])

    mandatory = [
        column
        for column in columns
        if normalize_column(column) in mandatory_names
    ]

    # Dates are not automatically suggested for exclusion.
    # Existing mandatory rules still take priority.
    suggested = [
        column
        for column in columns
        if normalize_column(column) in suggested_names
        and normalize_column(column) not in mandatory_names
        and normalize_column(column) not in date_names
    ]

    return mandatory, suggested


def build_policy(
    columns: list[str],
    table_key: str,
    dataset_id: str,
    optional_exclusions: list[str],
    detected_mandatory: list[str] | None = None,
    detected_suggested: list[str] | None = None,
    date_columns: list[str] | None = None,
) -> PrivacyPolicy:
    if not columns:
        raise ValueError("No dataset columns are available.")

    if any(not isinstance(column, str) or not column.strip() for column in columns):
        raise ValueError("Column names must be non-empty strings.")

    normalized = [normalize_column(column) for column in columns]

    if len(set(normalized)) != len(normalized):
        raise ValueError("Column names must be unique after normalization.")

    if not isinstance(dataset_id, str) or not dataset_id:
        raise ValueError("A dataset identifier is required.")

    mandatory, _ = classify_columns(
        columns=columns,
        table_key=table_key,
        detected_mandatory=detected_mandatory,
        detected_suggested=detected_suggested,
        date_columns=date_columns,
    )

    selected_names = _normalize_columns(optional_exclusions)
    unknown = selected_names - set(normalized)

    if unknown:
        raise ValueError(f"Unknown selected columns: {sorted(unknown)}")

    mandatory_names = _normalize_columns(mandatory)

    # Explicit user selections may include dates.
    # Skipping date detection does not override an explicit selection.
    optional = [
        column
        for column in columns
        if normalize_column(column) in selected_names
        and normalize_column(column) not in mandatory_names
    ]

    policy = PrivacyPolicy(
        dataset_id=dataset_id,
        source_columns=tuple(columns),
        mandatory_columns=tuple(mandatory),
        optional_columns=tuple(optional),
    )

    if not policy.approved_columns:
        raise ValueError("At least one approved column must remain.")

    return policy