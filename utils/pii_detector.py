# utils/pii_detector.py

import re
import pandas as pd
# from config.privacy import MANDATORY_COLUMNS

MANDATORY_COLUMNS = {
    "phone_number__c",
    "person_account__c",
    # "lead__c",
    # "transcript__c",
    # "call_summary__c",
    # "transcription_uid__c",
    # "external_id__c",
    # "user_id__c",
}
EMAIL_VALUE = re.compile(
    r"(?<![\w.+-])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[A-Z0-9](?:[A-Z0-9.-]*[A-Z0-9])?\.[A-Z]{2,}"
    r"(?![\w.-])",
    re.IGNORECASE,
)

PHONE_VALUE = re.compile(
    r"^\+?[\d\s().-]+(?:\s*(?:ext\.?|x)\s*\d{1,6})?$",
    re.IGNORECASE,
)

CONTACT_NAME = re.compile(
    r"\b(?:email|e mail|phone|telephone|mobile|fax|contact|tel)\b"
)

SECONDARY_NAME = re.compile(
    r"\b(?:"
    r"name|firstname|lastname|surname|address|postcode|postal|"
    r"birth|dob|ip|notes?|comments?|description|statement"
    r")\b"
)

NON_CONTACT_VALUE = re.compile(
    r"\b(?:"
    r"count|counts|total|number of|score|ratio|rate|percentage|"
    r"date|datetime|time|timestamp|hour|hours|delay|"
    r"opt out|optout|opted out|optedout|opt in|optin|"
    r"consent|preference|preferences|status|method|"
    r"sent|received|completed|bounced|id|key|"
    r"has|is|flag|sync|synced"
    r")\b"
)

DIRECT_CONTACT_NAME = re.compile(
    r"\b(?:email|e mail|phone|telephone|mobile|fax)\b"
    r"|\bcontact (?:number|no|email|phone|mobile)\b"
)

# Recognise separated date tokens and common compact field names.
# Avoid a generic "ends with date" rule: "candidate" also ends with "date".
DATE_COLUMN_NAME = re.compile(
    r"\b(?:date|datetime|timestamp|dob)\b"
    r"|\b(?:createddate|lastmodifieddate|converteddate|"
    r"lastactivitydate|lastvieweddate|lastreferenceddate|"
    r"emailbounceddate|birthdate|dateofbirth|"
    r"firstcalldatetime|firstemaildatetime|systemmodstamp)\b"
)

REPORT_COLUMNS = [
    "column",
    "data_type",
    "inspected_values",
    "email_matches",
    "phone_candidates",
    "action",
    "reason",
]


def normalize_name(column: str) -> str:
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(column))
    name = re.sub(r"__c$", "", name, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def looks_like_phone(value: str) -> bool:
    value = value.strip()

    if not PHONE_VALUE.fullmatch(value):
        return False

    # Prevent common date strings in other columns becoming phone candidates.
    date_patterns = (
        r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",
        r"\d{1,2}[-/.]\d{1,2}[-/.]\d{4}",
    )

    if any(re.fullmatch(pattern, value) for pattern in date_patterns):
        return False

    base = re.split(r"\s*(?:ext\.?|x)\s*", value, flags=re.IGNORECASE)[0]
    digits = re.sub(r"\D", "", base)

    # Heuristic only, not international phone-number validation.
    return 7 <= len(digits) <= 15


def detect_pii_columns(
    df: pd.DataFrame,
    sample_rows: int = 100,
    date_columns: list[str] | None = None,
) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if not df.columns.is_unique:
        raise ValueError("Duplicate column names are unsupported.")

    if (
        isinstance(sample_rows, bool)
        or not isinstance(sample_rows, int)
        or sample_rows < 1
    ):
        raise ValueError("sample_rows must be a positive integer.")

    # Explicit date overrides support string dates with unusual column names.
    explicit_dates = {
        str(column).strip().casefold()
        for column in (date_columns or [])
    }

    mandatory = {
        str(column).strip().casefold()
        for column in MANDATORY_COLUMNS
    }

    sample = (
        df.sample(n=min(sample_rows, len(df)), random_state=42)
        if len(df)
        else df
    )

    results = []

    for column in df.columns:
        normalized_column = str(column).strip().casefold()
        name = normalize_name(column)
        dtype = df[column].dtype

        report = {
            "column": column,
            "data_type": str(dtype),
            "inspected_values": 0,
            "email_matches": 0,
            "phone_candidates": 0,
            "action": "NO_EVIDENCE",
            "reason": "No contact evidence in the sample; not a safety guarantee.",
        }

        # Existing mandatory policy always takes priority.
        if normalized_column in mandatory:
            report["action"] = "MANDATORY_REMOVE"
            report["reason"] = "Existing administrator-defined mandatory exclusion."
            results.append(report)
            continue

        is_date_column = (
            pd.api.types.is_datetime64_any_dtype(dtype)
            or normalized_column in explicit_dates
            or bool(DATE_COLUMN_NAME.search(name))
        )

        # Do not inspect date values or suggest their removal.
        if is_date_column:
            report["action"] = "SKIPPED_DATE"
            report["reason"] = (
                "Date column retained; contact-value inspection was skipped."
            )
            results.append(report)
            continue

        values = sample[column].dropna().map(lambda value: str(value).strip())
        values = values.loc[values.ne("")]

        is_boolean = pd.api.types.is_bool_dtype(dtype)

        email_matches = int(
            values.map(lambda value: bool(EMAIL_VALUE.search(value))).sum()
        )
        phone_matches = (
            0 if is_boolean else int(values.map(looks_like_phone).sum())
        )

        contact_context = bool(CONTACT_NAME.search(name))
        metric_context = bool(NON_CONTACT_VALUE.search(name))
        direct_contact = (
            bool(DIRECT_CONTACT_NAME.search(name))
            and not metric_context
        )

        report["inspected_values"] = len(values)
        report["email_matches"] = email_matches
        report["phone_candidates"] = phone_matches

        if email_matches:
            report["action"] = "MANDATORY_REMOVE"
            report["reason"] = "Email-address pattern detected in sampled values."

        elif direct_contact:
            report["action"] = "MANDATORY_REMOVE"
            report["reason"] = "Column name indicates a contact value."

        elif contact_context and phone_matches and not metric_context:
            report["action"] = "MANDATORY_REMOVE"
            report["reason"] = "Contact-related name and phone-shaped sampled values."

        elif contact_context and not metric_context:
            report["action"] = "REVIEW"
            report["reason"] = "Ambiguous contact-related column name."

        elif phone_matches:
            report["action"] = "REVIEW"
            report["reason"] = (
                "Phone-shaped values; could also be identifiers or numeric measures."
            )

        elif SECONDARY_NAME.search(name):
            report["action"] = "REVIEW"
            report["reason"] = "Possible secondary PII or unrestricted text."

        elif values.empty:
            report["action"] = "REVIEW"
            report["reason"] = "No non-empty sample values available for inspection."

        results.append(report)

    return pd.DataFrame(results, columns=REPORT_COLUMNS)