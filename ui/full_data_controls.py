# ui/full_data_controls.py

import time
import uuid
from collections.abc import Callable

import pandas as pd
import streamlit as st


def render_full_data_controls(
    load_dataset: Callable,
    clear_chat: Callable,
) -> None:
    """
    Render Refresh Analysis and Load Full Data controls.

    load_dataset must accept:
        schema_name, table_name, brand_name, policy, row_limit

    load_dataset must return:
        metadata_df, data_df, row_count
    """
    state = st.session_state

    state.setdefault("full_data_loaded", False)
    state.setdefault("full_load_message", None)

    current_df = state.get("sample_df")
    loaded_rows = len(current_df) if isinstance(current_df, pd.DataFrame) else 0
    total_rows = int(state.get("row_count") or 0)

    # Full-data mode is valid only when the loaded DataFrame contains
    # the expected total number of rows for the loaded brand.
    is_full_dataset = (
        state.full_data_loaded
        and total_rows > 0
        and loaded_rows == total_rows
    )

    # Repair stale state left by changing the brand or loading a new sample.
    if state.full_data_loaded and not is_full_dataset:
        state.full_data_loaded = False
        state.full_load_message = None

    if is_full_dataset:
        st.caption(
            f"Full-data mode: {loaded_rows:,} loaded records for "
            f"{state.get('loaded_brand')}. Privacy exclusions remain active."
        )
    else:
        st.caption(
            f"Sample mode: {loaded_rows:,} of {total_rows:,} records loaded for "
            f"{state.get('loaded_brand')}. Privacy exclusions remain active."
        )

    if state.full_load_message:
        st.success(state.full_load_message)

    refresh_col, full_col, _ = st.columns([1, 1, 3])

    refresh_clicked = refresh_col.button(
        "Refresh Analysis",
        key="refresh_analysis",
        help="Run the analysis again using the currently loaded records.",
    )

    policy = state.get("applied_privacy_policy")
    schema_name = state.get("schema_name")
    table_name = state.get("table_name")
    brand_name = state.get("loaded_brand")

    can_load_full_data = (
        policy is not None
        and bool(schema_name)
        and bool(table_name)
        and bool(brand_name)
        and isinstance(current_df, pd.DataFrame)
        and not current_df.empty
        and total_rows > loaded_rows
        and not is_full_dataset
    )

    full_clicked = full_col.button(
        "Load Full Data",
        key="load_full_data",
        disabled=not can_load_full_data,
        help=(
            "Load all records for the currently loaded brand using the "
            "applied privacy policy."
        ),
    )

    if can_load_full_data:
        st.warning(
            f"Full-data loading will request all {total_rows:,} matching records "
            f"for '{brand_name}'. Loading and analysis may take several minutes "
            "and consume substantial memory. Very large datasets can exceed the "
            "server's available memory."
        )

    if refresh_clicked:
        state.analysis_result = None
        state.analysis_version = None
        state.full_load_message = None

        # This changes the analysis version without changing the dataset.
        state.dataset_version = uuid.uuid4().hex
        st.rerun()

    if not full_clicked:
        return

    started = time.perf_counter()
    # Preserve references to the currently loaded dataset. Session state is
    # updated only after full-data loading and validation complete successfully.
    previous_metadata_df = state.get("metadata_df")
    previous_sample_df = state.get("sample_df")
    previous_row_count = state.get("row_count")
    previous_dataset_version = state.get("dataset_version")
    # previous_analysis_result = state.get("analysis_result")
    # previous_analysis_version = state.get("analysis_version")

    # started = time.perf_counter()

    try:
        with st.spinner(
            "Loading all privacy-approved records. "
            "Large datasets may take several minutes..."
        ):
            metadata_df, full_df, row_count = load_dataset(
                schema_name=schema_name,
                table_name=table_name,
                brand_name=brand_name,
                policy=policy,
                row_limit=None,
            )

        if not isinstance(metadata_df, pd.DataFrame):
            raise TypeError("Full-data loading did not return valid metadata.")

        if not isinstance(full_df, pd.DataFrame):
            raise TypeError("Full-data loading did not return a DataFrame.")

        if full_df.empty and row_count > 0:
            raise ValueError(
                "The full-data query returned no rows for a non-empty dataset."
            )

        if len(full_df) != row_count:
            raise ValueError(
                f"Expected {row_count:,} records but received "
                f"{len(full_df):,} records."
            )

        elapsed = time.perf_counter() - started
        memory_mb = full_df.memory_usage(index=True, deep=True).sum() / (1024**2)

        # Commit the full dataset only after all validation succeeds.
        state.metadata_df = metadata_df
        state.sample_df = full_df
        state.row_count = int(row_count)
        state.full_data_loaded = True

        state.dataset_version = uuid.uuid4().hex
        state.analysis_result = None
        state.analysis_version = None

        # Clear chat responses generated for the previous sample.
        clear_chat()

        state.full_load_message = (
            f"Loaded {len(full_df):,} records in {elapsed:.1f} seconds. "
            f"DataFrame memory: {memory_mb:,.1f} MB. "
            "Analysis will now use all loaded records."
        )

        st.rerun()

    except Exception as ex:
        # Retain the previously loaded sample if full-data loading fails.
        state.metadata_df = previous_metadata_df
        state.sample_df = previous_sample_df
        state.row_count = previous_row_count
        state.dataset_version = previous_dataset_version
        # state.analysis_result = previous_analysis_result
        # state.analysis_version = previous_analysis_version

        state.full_data_loaded = False
        state.full_load_message = None

        # Log only the exception type to the server console.
        # Avoid printing SQL, DataFrame values, or sensitive source data.
        print(
            "Full-data loading failed: "
            f"{type(ex).__name__}"
        )

        st.error(
            "Full-data loading failed. The previously loaded sample was "
            "retained. Check available memory, database connectivity, "
            "query timeouts, and server logs."
        )

        return