import os, json
from openai import AzureOpenAI
import streamlit as st

def init_azure_client():
    try:
        return AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("OPENAI_API_VERSION")
        )
    except Exception as e:
        st.error(f"AzureOpenAI 초기화 실패: {e}")
        return None

def run_ai_report(client, summaries, relations):
    messages = [
        {"role": "system", "content": (
    "You are a senior data engineer. "
    "Perform a pre-load data quality inspection report in Korean, focusing on missing values, data types, duplicates, naming consistency, and relationships. "
    "Structure the report clearly using Markdown section headers and bullet points. "
    "Use the following section order:\n"
    "1. 데이터 개요\n"
    "2. 결측치 현황\n"
    "3. 데이터 타입 적합성\n"
    "4. 중복 및 유일성\n"
    "5. 명명 일관성 및 관계\n"
    "6. 종합 의견\n\n"
    "Write concisely and professionally in report tone. "
    "Do not include closing phrases like '문의 바랍니다' or '연락 바랍니다'. "
    "End naturally with '이상으로 사전 적재 데이터 품질 점검 보고서를 마칩니다.'"
)},
        {"role": "user", "content": json.dumps({
            "table_summaries": summaries,
            "relations": relations
        }, ensure_ascii=False)}
    ]
    resp = client.chat.completions.create(
        model=os.getenv("DEPLOYMENT_NAME"),
        messages=messages,
        temperature=0.4,
        max_completion_tokens=2000
    )
    return resp.choices[0].message.content.strip()

def run_qa(client, report, question):
    messages = [
        {"role": "system", "content": (
            "You are a data quality analyst assistant. Answer in Korean using context from the report."
        )},
        {"role": "user", "content": f"리포트 내용:\n{report}\n\n질문: {question}"}
    ]
    resp = client.chat.completions.create(
        model=os.getenv("DEPLOYMENT_NAME"),
        messages=messages,
        temperature=0.3,
        max_completion_tokens=1000
    )
    return resp.choices[0].message.content.strip()
