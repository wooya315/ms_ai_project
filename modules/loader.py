import pandas as pd, os, tempfile, zipfile, streamlit as st

def load_uploaded_files(uploaded_files):
    dfs = {}
    temp_dir = tempfile.mkdtemp()

    for f in uploaded_files:
        if f.name.endswith(".zip"):
            zip_path = os.path.join(temp_dir, f.name)
            with open(zip_path, "wb") as fp: fp.write(f.read())
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)
                for file_name in zf.namelist():
                    file_path = os.path.join(temp_dir, file_name)
                    if file_name.endswith(".csv"): dfs[file_name] = pd.read_csv(file_path)
                    elif file_name.endswith(".xlsx"): dfs[file_name] = pd.read_excel(file_path)
        else:
            if f.name.endswith(".csv") or f.name.endswith(".txt"):
                dfs[f.name] = pd.read_csv(f)
            elif f.name.endswith(".xlsx"):
                dfs[f.name] = pd.read_excel(f)
    return dfs
