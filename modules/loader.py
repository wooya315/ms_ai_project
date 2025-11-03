import pandas as pd
import json
import xml.etree.ElementTree as ET
import zipfile
import io

# ==========================================================
# 🧩 1️⃣ 개별 파일 파서 (공통 함수)
# ==========================================================
def parse_file_to_df(file_obj, filename: str) -> pd.DataFrame | None:
    """파일 객체와 이름을 받아 확장자에 따라 DataFrame으로 변환"""
    try:
        if filename.endswith(".csv"):
            return pd.read_csv(file_obj)

        elif filename.endswith(".xlsx"):
            return pd.read_excel(file_obj)

        elif filename.endswith(".json"):
            return pd.json_normalize(json.load(file_obj))

        elif filename.endswith(".xml"):
            tree = ET.parse(file_obj)
            root = tree.getroot()
            data = [{child.tag: child.text for child in elem} for elem in root]
            return pd.DataFrame(data)

        elif filename.endswith(".txt"):
            content = file_obj.read().decode("utf-8", errors="ignore")
            # 자동 구분자 탐색
            delim = "," if "," in content else "\t" if "\t" in content else ";"
            return pd.read_csv(io.StringIO(content), delimiter=delim)

        else:
            print(f"⚠️ 지원되지 않는 파일 형식: {filename}")
            return None

    except Exception as e:
        print(f"❌ {filename} 처리 중 오류: {e}")
        return None


# ==========================================================
# 📦 2️⃣ 업로드 파일 로더 (ZIP 포함)
# ==========================================================
def load_uploaded_files(uploaded_files):
    """
    Streamlit uploader에서 넘어온 파일 리스트를 읽어 DataFrame dict로 반환.
    - zip 파일일 경우 내부 파일을 자동 해제하여 함께 반환
    """
    dfs = {}

    for file in uploaded_files:
        filename = file.name.lower()

        # ---- ZIP 파일 처리 ----
        if filename.endswith(".zip"):
            with zipfile.ZipFile(file, "r") as z:
                for inner_name in z.namelist():
                    if inner_name.endswith("/"):
                        continue  # 폴더는 스킵

                    with z.open(inner_name) as inner_file:
                        df = parse_file_to_df(inner_file, inner_name.lower())
                        if df is not None:
                            dfs[inner_name] = df

        # ---- 단일 파일 처리 ----
        else:
            df = parse_file_to_df(file, filename)
            if df is not None:
                dfs[file.name] = df

    return dfs
