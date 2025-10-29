from sklearn.preprocessing import LabelEncoder
import pandas as pd

def preprocess_dataframe(df: pd.DataFrame, options: dict):
    df_clean = df.copy()
    if options.get("fillna_zero"):
        df_clean.fillna(0, inplace=True)
    if options.get("drop_duplicates"):
        df_clean.drop_duplicates(inplace=True)
    if options.get("encode_objects"):
        encoder = LabelEncoder()
        for col in df_clean.select_dtypes(include=["object"]).columns:
            df_clean[col] = encoder.fit_transform(df_clean[col].astype(str))
    return df_clean
