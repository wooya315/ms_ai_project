import pandas as pd
import json
import xml.etree.ElementTree as ET
import zipfile
import io

def load_uploaded_files(uploaded_files):
    """
    Streamlit uploader에서 넘어온 파일 리스트를 읽어 DataFrame dict로 반환.
    - zip 파일일 경우 내부 파일을 자동으로 해제하여 함께 반환
    """
    dfs = {}

    for file in uploaded_files:
        filename = file.name.lower()

        # ---- ZIP 파일 처리 ----
        if filename.endswith(".zip"):
            with zipfile.ZipFile(file, "r") as z:
                for inner_name in z.namelist():
                    # 하위 폴더 제외
                    if inner_name.endswith("/"):
                        continue

                    with z.open(inner_name) as inner_file:
                        try:
                            if inner_name.endswith(".csv"):
                                df = pd.read_csv(inner_file)
                            elif inner_name.endswith(".xlsx"):
                                df = pd.read_excel(inner_file)
                            elif inner_name.endswith(".json"):
                                df = pd.json_normalize(json.load(inner_file))
                            elif inner_name.endswith(".xml"):
                                tree = ET.parse(inner_file)
                                root = tree.getroot()
                                dfs_in_xml = []
                                for child in root:
                                    dfs_in_xml.append({elem.tag: elem.text for elem in child})
                                df = pd.DataFrame(dfs_in_xml)
                            elif inner_name.endswith(".txt"):
                                content = inner_file.read().decode("utf-8", errors="ignore")
                                # 자동 구분자 탐색 (쉼표/탭/세미콜론)
                                delim = "," if "," in content else "\t" if "\t" in content else ";"
                                df = pd.read_csv(io.StringIO(content), delimiter=delim)
                            else:
                                continue

                            dfs[inner_name] = df
                        except Exception as e:
                            print(f"❌ {inner_name} 처리 중 오류: {e}")

        # ---- 일반 CSV / XLSX / JSON / XML / TXT ----
        elif filename.endswith(".csv"):
            dfs[file.name] = pd.read_csv(file)
        elif filename.endswith(".xlsx"):
            dfs[file.name] = pd.read_excel(file)
        elif filename.endswith(".json"):
            dfs[file.name] = pd.json_normalize(json.load(file))
        elif filename.endswith(".xml"):
            tree = ET.parse(file)
            root = tree.getroot()
            data = [{child.tag: child.text for child in elem} for elem in root]
            dfs[file.name] = pd.DataFrame(data)
        elif filename.endswith(".txt"):
            content = file.read().decode("utf-8", errors="ignore")
            delim = "," if "," in content else "\t" if "\t" in content else ";"
            dfs[file.name] = pd.read_csv(io.StringIO(content), delimiter=delim)
        else:
            print(f"⚠️ 지원되지 않는 파일 형식: {file.name}")

    return dfs
