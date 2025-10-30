# modules/ai_agent.py
import os
import json
import streamlit as st
import pandas as pd
from openai import AzureOpenAI

# ==============================
# ✅ Azure 클라이언트 초기화
# ==============================
def init_azure_client():
    try:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("OPENAI_API_VERSION")

        if not all([api_key, endpoint, api_version]):
            raise ValueError("환경 변수(AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, OPENAI_API_VERSION)가 누락되었습니다.")

        return AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )

    except Exception as e:
        st.error(f"❌ AzureOpenAI 초기화 실패: {e}")
        return None


# ==============================
# ✅ 품질 점검 보고서 생성
# ==============================
def run_ai_report(client, summaries, relations=None):
    if not client:
        return "⚠️ Azure OpenAI 클라이언트가 초기화되지 않았습니다."

    system_prompt = (
        "You are a senior data engineer.\n"
        "주어진 다중 테이블 요약(summaries)과 컬럼 관계 후보(relations)를 기반으로, "
        "사전 적재 데이터 품질 점검 보고서를 **한국어로** 작성하라.\n\n"

        "다음 형식을 반드시 준수하라:\n"
        "- 섹션 제목은 굵게(**) 표시하라. 예: **1. 데이터 개요**\n"
        "- 각 섹션은 순서대로 작성하라.\n"
        "- Markdown의 # 헤더는 사용하지 마라.\n\n"

        "섹션 순서:\n"
        "1. 데이터 개요\n"
        "2. 결측치 현황\n"
        "3. 데이터 타입 적합성\n"
        "4. 중복 및 유일성\n"
        "5. 명명 일관성 및 관계\n"
        "6. 종합 의견\n"
        "7. 전처리 우선 권장 사항\n\n"

        "7. 전처리 우선 권장 사항 섹션은 반드시 아래 두 부분으로 구성하라:\n"
        "① 사람이 읽을 수 있는 요약 설명 (간략한 문단)\n"
        "② JSON 형식의 구조화 데이터 블록 (아래 예시와 동일한 포맷)\n\n"

        "```json\n"
        "{\n"
        "  \"01_csv_basic_cleaning.csv\": [\n"
        "    {\"action\": \"strip_strings\", \"columns\": [\"id\", \"Name\", \"Gender\", \"BirthDate\"]},\n"
        "    {\"action\": \"normalize_case\", \"columns\": [\"Gender\"], \"params\": \"lower\"}\n"
        "  ],\n"
        "  \"전체 파일\": [\n"
        "    {\"action\": \"normalize_case\", \"columns\": [\"모든 컬럼\"], \"params\": \"lower\"}\n"
        "  ]\n"
        "}\n"
        "```\n\n"
        "⚠️ JSON 블록은 반드시 코드블록(```json`) 안에 출력하라.\n"
        "리포트 마지막은 '이상으로 사전 적재 데이터 품질 점검 보고서를 마칩니다.'로 끝내라.\n"
    )

    payload = {
        "table_summaries": summaries,
        "relations": relations or []
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
    ]

    try:
        resp = client.chat.completions.create(
            model=os.getenv("DEPLOYMENT_NAME"),
            messages=messages,
            temperature=0.5,
            max_completion_tokens=1800
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ AI 보고서 생성 실패: {e}")
        return "⚠️ AI 품질 보고서 생성 중 오류가 발생했습니다."


# ==============================
# ✅ 리포트 기반 Q&A 수행
# ==============================
def run_qa(client, report, question):
    if not client:
        return "⚠️ Azure OpenAI 클라이언트가 초기화되지 않았습니다."
    if not report:
        return "⚠️ 품질 점검 리포트가 없습니다."

    messages = [
        {"role": "system", "content":
            "You are a helpful data quality analyst assistant. "
            "Answer ONLY using the content of the provided report, and reply in Korean. "
            "If the report lacks relevant information, state it briefly."
        },
        {"role": "user", "content": f"리포트 내용:\n{report}\n\n질문: {question}"}
    ]

    try:
        resp = client.chat.completions.create(
            model=os.getenv("DEPLOYMENT_NAME"),
            messages=messages,
            temperature=0.4,
            max_completion_tokens=800
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ Q&A 처리 실패: {e}")
        return "⚠️ AI Q&A 처리 중 오류가 발생했습니다."
    

# ==============================
# ✅ 데이터 가공 명령 수행
# ==============================
def run_data_processing(client, dataframe, user_command):
    """
    자연어 명령을 받아, 구체적인 pandas 전처리 코드를 생성하고 실행함.
    """
    if not client:
        return "⚠️ Azure OpenAI 클라이언트가 초기화되지 않았습니다.", dataframe

    system_prompt = (
        "You are a senior data engineer. "
        "주어진 데이터프레임의 구조를 기반으로, 사용자의 명령(user_command)을 수행하기 위한 "
        "pandas 코드 스니펫을 작성하라. 반드시 실행 가능한 코드만 작성하고, "
        "print문이나 설명은 포함하지 마라.\n\n"
        "예시:\n"
        "사용자 명령: 결측치를 평균값으로 채워줘\n"
        "출력 코드 예시:\n"
        "df = df.fillna(df.mean())"
    )

    # 데이터프레임 스키마 요약
    schema_info = json.dumps({
        "columns": list(dataframe.columns),
        "dtypes": dataframe.dtypes.astype(str).to_dict(),
        "shape": dataframe.shape
    }, ensure_ascii=False)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"데이터프레임 구조: {schema_info}\n\n사용자 명령: {user_command}"}
    ]

    try:
        resp = client.chat.completions.create(
            model=os.getenv("DEPLOYMENT_NAME"),
            messages=messages,
            temperature=0.4,
            max_completion_tokens=600
        )

        code = resp.choices[0].message.content.strip()
        local_vars = {"df": dataframe.copy()}
        exec(code, {}, local_vars)
        new_df = local_vars["df"]

        return "✅ 데이터 전처리 성공", new_df

    except Exception as e:
        st.error(f"❌ 데이터 전처리 실패: {e}")
        return "⚠️ 데이터 전처리 중 오류가 발생했습니다.", dataframe

