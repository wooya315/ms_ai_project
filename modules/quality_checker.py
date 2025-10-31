import pandas as pd
import json
import os
import streamlit as st
from openai import AzureOpenAI

# ====================================================
# 🔧 1. 기본 데이터 요약 함수
# ====================================================
def summarize_dataframe(df: pd.DataFrame, name: str):
    """각 데이터프레임의 기본 메타정보 및 통계 요약 생성"""
    return {
        "파일명": name,
        "shape": df.shape,
        "columns": list(df.columns),
        "types": df.dtypes.astype(str).to_dict(),
        "missing_values": df.isnull().sum().to_dict(),
        "unique_values": {col: df[col].nunique() for col in df.columns},
        "sample_rows": df.head(3).to_dict(orient="records"),
    }


# ====================================================
# 🤖 2. Azure OpenAI 클라이언트 초기화
# ====================================================
def init_azure_client():
    """Azure OpenAI 클라이언트 초기화"""
    try:
        return AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("OPENAI_API_VERSION"),
        )
    except Exception as e:
        st.error(f"AzureOpenAI 초기화 실패: {e}")
        return None


