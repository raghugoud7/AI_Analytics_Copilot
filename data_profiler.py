import pandas as pd


def profile_dataframe(df):

    profile = {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
        "data_types": df.dtypes.astype(str).to_dict()
    }

    return profile