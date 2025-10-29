import os
import io
import zipfile
import csv
import json
import pandas as pd
import streamlit as st
from xml.etree import ElementTree as ET
from collections import Counter

# 여러 인코딩 후보 (윈도우 계열 엑셀 저장본 대비)
ENCODING_CANDIDATES = ["utf-8", "utf-8-sig", "cp949", "euc-kr"]


def _read_bytes_guess_encoding(file_bytes: bytes):
    """
    바이트 -> (텍스트, 사용된 인코딩)
    여러 인코딩 후보를 시도해 가장 먼저 성공한 결과를 반환.
    """
    last_err = None
    for enc in ENCODING_CANDIDATES:
        try:
            return file_bytes.decode(enc), enc
        except Exception as e:
            last_err = e
    # 모두 실패하면 그냥 예외 터뜨림
    raise last_err or ValueError("텍스트 디코딩 실패")


def _read_txt_auto(file_bytes: bytes) -> pd.DataFrame:
    """
    TXT 파일을 DataFrame으로 읽는다.
    - 구분자(, \t | ; 등) 자동 추정
    - 헤더 유무 자동 추정
    - 판다스로 로드
    """
    text, _enc = _read_bytes_guess_encoding(file_bytes)

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=[",", "\t", "|", ";", "^", "~"]
        )
        has_header = csv.Sniffer().has_header(sample)
        sep = dialect.delimiter
    except Exception:
        # 추정 실패 시 기본값
        sep = ","
        has_header = True

    df = pd.read_csv(
        io.StringIO(text),
        sep=sep,
        header=0 if has_header else None,
        engine="python"
    )

    # 헤더가 없던 경우 인공 컬럼명 생성
    if not has_header:
        df.columns = [f"col_{i+1}" for i in range(df.shape[1])]

    return df


def _read_csv_file(file_bytes: bytes) -> pd.DataFrame:
    """
    CSV 파일을 DataFrame으로 읽는다. 인코딩은 자동 감지.
    """
    text, _enc = _read_bytes_guess_encoding(file_bytes)
    return pd.read_csv(io.StringIO(text))


def _read_xlsx_file(file_bytes: bytes) -> pd.DataFrame:
    """
    XLSX 파일을 DataFrame으로 읽는다.
    """
    return pd.read_excel(io.BytesIO(file_bytes))


def _flatten_xml_nodes(xml_bytes: bytes) -> pd.DataFrame:
    """
    XML을 반복 노드 단위로 평탄화하여 DataFrame으로 변환한다.

    가정:
      <root>
         <record>...</record>
         <record>...</record>
      </root>
    처럼 동일 반복 태그(record, row, item 등)가 여러 번 등장한다는 상황을 우선 지원.

    동작:
    - root 바로 아래에서 반복되는 자식 tag를 찾는다.
    - 없다면 root의 첫 번째 자식 아래에서 반복되는 자식 tag를 찾는다.
    - 그 반복되는 노드의 하위 요소/속성을 column으로 매핑.
    """
    root = ET.fromstring(xml_bytes)

    # 1차 시도: root 바로 아래 children 태그 빈도 계산
    direct_children = list(root)
    if direct_children:
        from collections import Counter
        tag_counts = Counter(child.tag for child in direct_children)
        record_tag, _count = tag_counts.most_common(1)[0]
        candidate_nodes = root.findall(record_tag)
    else:
        candidate_nodes = []

    # fallback: root 아래 첫 child의 children 들여다보기
    if not candidate_nodes:
        if len(root) > 0:
            first_child = root[0]
            grandchildren = list(first_child)
            if grandchildren:
                tag_counts = Counter(gc.tag for gc in grandchildren)
                record_tag, _count = tag_counts.most_common(1)[0]
                candidate_nodes = first_child.findall(record_tag)

    rows = []
    for node in candidate_nodes:
        row = {}

        # node attribute -> 컬럼화
        for k, v in node.attrib.items():
            row[f"__node_attr__{k}"] = v

        # node 하위 요소들 -> 컬럼화
        for child in list(node):
            row[child.tag] = (child.text or "").strip()
            # child의 attribute도 풀어준다
            for ak, av in child.attrib.items():
                row[f"{child.tag}__{ak}"] = av

        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def _read_xml_file(file_bytes: bytes) -> pd.DataFrame:
    """
    XML을 DataFrame으로 읽는다.
    1) pandas.read_xml 시도
    2) 실패 시 커스텀 평탄화
    """
    try:
        df_xml = pd.read_xml(io.BytesIO(file_bytes))
        if df_xml is not None and not df_xml.empty:
            return df_xml
    except Exception:
        pass

    # fallback 커스텀 파서
    return _flatten_xml_nodes(file_bytes)


def _read_json_file(file_bytes: bytes) -> pd.DataFrame:
    """
    JSON 파일을 DataFrame으로 변환.

    허용 패턴 예:
    1) [ { ... }, { ... } ]  -> records 그대로 DataFrame
    2) { "data": [ {...}, {...} ] } -> data 키를 records로 간주
    3) { "id": 1, "name": "foo" } -> 단일 row DataFrame
    4) 기타 형태 -> 그냥 전체를 value 컬럼으로 담음
    """
    # 인코딩 추정부터 (csv/txt와 동일 전략)
    text, _enc = _read_bytes_guess_encoding(file_bytes)

    try:
        obj = json.loads(text)
    except Exception as e:
        st.warning(f"JSON 파싱 실패: {e}")
        return pd.DataFrame()

    # 1) list of dict
    if isinstance(obj, list):
        if all(isinstance(x, dict) for x in obj):
            return pd.DataFrame(obj)
        else:
            return pd.DataFrame({"value": [obj]})

    # 2) dict
    if isinstance(obj, dict):
        if "data" in obj and isinstance(obj["data"], list) and all(isinstance(x, dict) for x in obj["data"]):
            return pd.DataFrame(obj["data"])
        else:
            return pd.DataFrame([obj])

    # 3) 기타
    return pd.DataFrame({"value": [obj]})


def _handle_regular_file(file_name: str, file_bytes: bytes) -> pd.DataFrame:
    """
    확장자에 따라 적절한 reader 호출.
    지원: csv / xlsx / txt / xml / json
    """
    lower = file_name.lower()

    if lower.endswith(".csv"):
        return _read_csv_file(file_bytes)

    elif lower.endswith(".xlsx"):
        return _read_xlsx_file(file_bytes)

    elif lower.endswith(".txt"):
        return _read_txt_auto(file_bytes)

    elif lower.endswith(".xml"):
        return _read_xml_file(file_bytes)

    elif lower.endswith(".json"):
        return _read_json_file(file_bytes)

    else:
        raise ValueError(f"지원되지 않는 파일 형식입니다: {file_name}")


def _handle_zip_file(zip_stream: bytes) -> dict:
    """
    ZIP 내부 파일을 탐색해서 csv/xlsx/txt/xml/json 만 DataFrame으로 읽는다.
    리턴: { "내부파일명": DataFrame, ... }
    """
    dfs_in_zip = {}
    with zipfile.ZipFile(io.BytesIO(zip_stream), "r") as zf:
        for member_name in zf.namelist():
            # 디렉토리 스킵
            if member_name.endswith("/"):
                continue

            lower = member_name.lower()
            # ZIP 내부에서도 우리가 지원하는 확장자만 처리
            if not any(lower.endswith(ext) for ext in [".csv", ".xlsx", ".txt", ".xml", ".json"]):
                continue

            with zf.open(member_name) as member_file:
                file_bytes = member_file.read()

            try:
                dfs_in_zip[member_name] = _handle_regular_file(member_name, file_bytes)
            except Exception as e:
                st.warning(f"ZIP 내부 파일 `{member_name}` 로딩 실패: {e}")

    return dfs_in_zip


def load_uploaded_files(uploaded_files):
    """
    Streamlit file_uploader로 받은 uploaded_files(list-like)를 순회하고
    지원되는 모든 파일(csv/xlsx/txt/xml/json/zip)을 DataFrame으로 변환하여 dict로 반환한다.

    return 예시:
    {
        "sales_2025.csv": DataFrame(...),
        "product_master.xlsx": DataFrame(...),
        "raw_dump.xml": DataFrame(...),
        "logs_2025_10_29.txt": DataFrame(...),
        "snapshot.json": DataFrame(...)
    }
    """
    dfs_total = {}

    for f in uploaded_files:
        fname = f.name
        lower = fname.lower()

        # Streamlit UploadedFile은 read() 후 포인터가 이동하므로
        file_bytes = f.read()
        f.seek(0)

        if lower.endswith(".zip"):
            # ZIP 내부 파일 해석
            inside = _handle_zip_file(file_bytes)
            # ZIP 안의 파일명으로 dfs_total 병합
            # (동일 이름 충돌 시 덮어쓰지 않도록 suffix를 붙이는 것도 가능)
            for inner_name, df_inner in inside.items():
                key_name = inner_name
                idx = 1
                while key_name in dfs_total:
                    idx += 1
                    key_name = f"{inner_name}__{idx}"
                dfs_total[key_name] = df_inner

        elif any(lower.endswith(ext) for ext in [".csv", ".xlsx", ".txt", ".xml", ".json"]):
            try:
                df_parsed = _handle_regular_file(fname, file_bytes)

                # 같은 이름 중복 업로드 방지: 중복되면 __2, __3 붙임
                key_name = fname
                i = 1
                while key_name in dfs_total:
                    i += 1
                    key_name = f"{fname}__{i}"

                dfs_total[key_name] = df_parsed

            except Exception as e:
                st.warning(f"파일 `{fname}` 로딩 실패: {e}")

        else:
            st.warning(f"지원하지 않는 파일 형식: {fname}")

    return dfs_total
