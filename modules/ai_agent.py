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

def run_ai_report(client, summaries):
    """
    summaries: {테이블명: {...}}  # summarize_dataframe() 결과들

    """

    # 기본 섹션 가이드 (1~6)
    system_prompt = (
        "You are a senior data engineer.\n"
        "주어진 다중 테이블 요약(summaries)과 컬럼 관계 후보(relations)를 기반으로, "
        "사전 적재 데이터 품질 점검 보고서를 한국어로 작성하라.\n\n"

        "보고서는 아래 섹션 순서를 반드시 따라라:\n"
        "1. 데이터 개요\n"
        "2. 결측치 현황\n"
        "3. 데이터 타입 적합성\n"
        "4. 중복 및 유일성\n"
        "5. 명명 일관성 및 관계\n"
        "6. 종합 의견\n"
    )

    # 공통 스타일 지시
    system_prompt = (
        "You are a senior data engineer.\n"
        "… (중략 기존 섹션 가이드) …\n"
        "아래 섹션도 마지막에 반드시 포함하라:\n"
        "8. 전처리 우선 권장 사항\n"
        "- 실제 DB 적재 전에 우선 적용해야 할 데이터 정제 작업을 불릿으로 제안하라.\n"
        "- 예시는 다음과 같다:\n"
        "  - 결측치가 많은 컬럼은 기본값 채우기 또는 컬럼 분리 필요\n"
        "  - 문자열로 들어온 날짜 컬럼은 datetime 변환 필요\n"
        "  - 전부 동일한 값을 갖는 컬럼은 드롭 가능성 검토\n"
        "  - 중복 행 제거 필요 여부\n"
        "  - 숫자형으로 취급해야 할 문자열 컬럼은 숫자 변환 필요\n"
        "- 테이블 단위로 구체적인 컬럼명을 명시하라.\n"
        "- '자동 전처리 수행 권장: 결측치 0 채우기 / 중복 제거 / 문자열 공백 제거 / 날짜 변환 / 숫자 변환' 처럼 실제 액션 단위로 말하라.\n"
        "\n"
        "보고서 마지막 문장은 여전히 '이상으로 사전 적재 데이터 품질 점검 보고서를 마칩니다.' 로 끝내라.\n"
    )

    user_payload = {
        "table_summaries": summaries,
    }

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False)
        }
    ]

    resp = client.chat.completions.create(
        model=os.getenv("DEPLOYMENT_NAME"),
        messages=messages,
        temperature=0.6,
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
        temperature=0.6,
        max_completion_tokens=1000
    )
    return resp.choices[0].message.content.strip()
