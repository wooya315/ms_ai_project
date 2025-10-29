import pandas as pd

def preprocess_dataframe(df: pd.DataFrame, options: dict):
    df_clean = df.copy()
    if options.get("fillna_zero"):
        df_clean.fillna(0, inplace=True)
    if options.get("drop_duplicates"):
        df_clean.drop_duplicates(inplace=True)
    return df_clean
