import pandas as pd
import numpy as np
import unicodedata
import streamlit as st
from dateutil import parser
from datetime import datetime

# ==========================================================
# 🧹 1️⃣ 비어 있는 컬럼 자동 삭제
# ==========================================================
def drop_empty_cols(df: pd.DataFrame) -> pd.DataFrame:
    drop_cols = []
    for col in df.columns:
        if df[col].apply(lambda x: (pd.isna(x)) or (str(x).strip() == "")).all():
            drop_cols.append(col)
    if drop_cols:
        df = df.drop(columns=drop_cols)
        st.info(f"🗑️ 비어 있는 컬럼 자동 삭제됨: {', '.join(drop_cols)}")
    return df


# ==========================================================
# 🧠 2️⃣ Robust 날짜 파서
# ==========================================================
def robust_parse_date(x):
    """datetime + dateutil.parser 병합 파서"""
    if pd.isna(x) or str(x).strip() == "":
        return pd.NaT
    x = str(x).strip().replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(x, fmt)
        except ValueError:
            continue
    try:
        return parser.parse(x, fuzzy=True)
    except Exception:
        return pd.NaT


# ==========================================================
# 🔍 3️⃣ 날짜 추정 함수
# ==========================================================
def looks_like_date(val: str) -> bool:
    """값이 날짜 형태로 보이는지 간단히 추정"""
    if not isinstance(val, str):
        return False
    val = val.strip()
    return bool(
        val
        and 6 <= len(val) <= 10
        and all(c.isdigit() or c in "-/." for c in val)
    )


# ==========================================================
# ⚙️ 4️⃣ 메인 전처리 함수
# ==========================================================
def preprocess_dataframe(df: pd.DataFrame, options: dict):
    df = df.copy()
    logs = []

    # 0️⃣ 빈 문자열을 NaN으로 통일
    df = df.replace(r'^\s*$', np.nan, regex=True)

    # 1️⃣ 문자열 공백 및 유니코드 정규화
    if options.get("strip_strings", True):
        df = df.applymap(lambda x: unicodedata.normalize("NFKC", x.strip()) if isinstance(x, str) else x)
        logs.append("✅ 문자열 앞뒤 공백 및 유니코드 정규화")

    # 2️⃣ 대소문자 변환
    normalize_case = options.get("normalize_case")
    if normalize_case:
        if normalize_case == "lower":
            df = df.applymap(lambda x: x.lower() if isinstance(x, str) else x)
        elif normalize_case == "upper":
            df = df.applymap(lambda x: x.upper() if isinstance(x, str) else x)
        logs.append("✅ 문자열 대소문자 변환 수행")

    # 3️⃣ 숫자형 문자열 변환 ("1,000", "$3000")
    if options.get("convert_numeric_strings", True):
        for col in df.columns:
            if df[col].dtype == object:
                cleaned = (
                    df[col].astype(str)
                    .str.replace(r"['\"]", "", regex=True)
                    .str.replace(r"[^\d\.\-]", "", regex=True)
                )
                numeric = pd.to_numeric(cleaned, errors="coerce")
                if numeric.notna().sum() > len(df) * 0.3:
                    df[col] = numeric
        logs.append("✅ 숫자형 문자열 변환 수행")

    if options.get("convert_dates", True):
        date_keywords = ["date", "day", "time", "dob", "birth", "dt"]
        for col in df.columns:
            if df[col].dtype != object:
                continue

            # ① 날짜 가능성 판단
            sample_values = df[col].dropna().astype(str).head(20).tolist()
            has_date_name = any(key in col.lower() for key in date_keywords)
            has_date_pattern = (
                sum(looks_like_date(v) for v in sample_values) / max(len(sample_values), 1)
            ) > 0.5

            if not (has_date_name or has_date_pattern):
                continue

            # ② 문자열 전처리 먼저 수행
            temp = (
                df[col].astype(str)
                .str.strip()
                .str.replace(r"[./]", "-", regex=True)
                .replace(["", " ", "NULL", "nan", "NaN", "None"], np.nan)
            )

            # ③ 1차 pandas 변환
            parsed = pd.to_datetime(temp, errors="coerce", infer_datetime_format=True)

            # ④ 2차 robust parser 적용 (NaT인 항목만)
            mask_failed = parsed.isna()
            if mask_failed.any():
                parsed.loc[mask_failed] = temp[mask_failed].apply(robust_parse_date)

            # ⑤ 변환 결과 반영
            df[col] = parsed

        # ✅ 날짜 포맷 통일
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")

        logs.append("✅ 날짜형 변환 완료 (원본 문자열 유지 후 robust 처리)")

    # 5️⃣ Gender 표준화
    if "Gender" in df.columns:
        df["Gender"] = (
            df["Gender"]
            .astype(str)
            .str.strip()
            .str.lower()
            .replace({
                "female": "F", "f": "F",
                "male": "M", "m": "M"
            })
        )
        logs.append("✅ Gender 컬럼 표준화 (F/M)")

    # 6️⃣ 결측치 채우기
    if options.get("fillna_zero", True):
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(0)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].fillna(pd.Timestamp("1900-01-01"))
            else:
                df[col] = df[col].fillna("NULL")
        logs.append("✅ 결측치 채우기 수행 (숫자: 0, 날짜: 1900-01-01, 문자열: 'NULL')")

    # 7️⃣ 중복 제거
    if options.get("drop_duplicates", False):
        before = len(df)
        df.drop_duplicates(inplace=True)
        logs.append(f"⚙️ 중복 행 {before - len(df)}개 제거")

    # 8️⃣ 완전 공백 컬럼 제거
    if options.get("drop_empty_cols", True):
        df = drop_empty_cols(df)

    # 9️⃣ 컬럼명 정리
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    logs.append("✅ 컬럼명 공백 제거 및 언더스코어 변환")

    df.attrs["clean_log"] = logs
    return df
