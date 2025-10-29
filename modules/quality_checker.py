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


# ====================================================
# 🧠 4. AI 품질 점검 보고서 생성
# ====================================================
def run_ai_report(client, table_summaries: dict, relations: list):
    """
    각 파일의 데이터 품질 정보를 기반으로
    사전 적재 데이터 품질 점검 보고서를 Markdown 섹션 구조로 생성.
    """

    messages = [
        {
    "role": "system",
    "content": (
                "You are a senior data engineer. "
                "Perform a pre-load data quality inspection report in Korean, "
                "focusing on missing values, data types, duplicates, naming consistency, and relationships. "
                "Format the report using **literal Markdown syntax** so that it displays properly in Streamlit. "
                "Use bold section titles by literally including double asterisks around them (e.g., **1. 데이터 개요**). "
                "Under each section, use bullet points starting with '- '. "
                "Do NOT use '#' headers or numbered lists. "
                "Follow this structure order:\n"
                "1. 데이터 개요\n"
                "2. 결측치 현황\n"
                "3. 데이터 타입 적합성\n"
                "4. 중복 및 유일성\n"
                "5. 명명 일관성 및 관계\n"
                "6. 종합 의견\n\n"
                "Write concisely and professionally in a report tone. "
                "Do not include closing phrases like '문의 바랍니다' or '연락 바랍니다'. "
                "End naturally with '이상으로 사전 적재 데이터 품질 점검 보고서를 마칩니다.' "
                "Avoid excessive repetition and ensure each section is contextually relevant to the provided data."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "table_summaries": table_summaries,
                    "relations": relations,
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]

    try:
        response = client.chat.completions.create(
            model=os.getenv("DEPLOYMENT_NAME"),
            messages=messages,
            temperature=0.4,
            max_completion_tokens=2500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ AI 보고서 생성 실패: {e}")
        return "⚠️ 품질 점검 보고서 생성 중 오류가 발생했습니다."


# ====================================================
# 💬 5. Q&A (선택적 - 필요 시 연결)
# ====================================================
def run_qa(client, report_text: str, question: str):
    """품질 리포트를 기반으로 Q&A 수행"""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful data quality analyst assistant. "
                "Answer the user's question in Korean based on the given data quality report. "
                "Maintain a concise and professional tone, avoid repetition, "
                "and refer to relevant column names or table names directly when applicable."
            ),
        },
        {
            "role": "user",
            "content": f"다음은 데이터 품질 점검 보고서입니다:\n\n{report_text}\n\n사용자 질문: {question}",
        },
    ]
    try:
        response = client.chat.completions.create(
            model=os.getenv("DEPLOYMENT_NAME"),
            messages=messages,
            temperature=0.3,
            max_completion_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ AI Q&A 오류: {e}")
        return "⚠️ Q&A 처리 중 오류가 발생했습니다."
