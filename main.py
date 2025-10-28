import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from io import StringIO
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI

# =========================
# ✅ 환경 변수 로드
# =========================
load_dotenv()
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# =========================
# ✅ Azure OpenAI 초기화
# =========================
llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-02-01-preview",
    deployment_name=DEPLOYMENT_NAME,
    model="gpt-4.1-mini",
    temperature=0.4
)

# =========================
# ✅ Streamlit 설정
# =========================
st.set_page_config(page_title="🧠 AI 데이터 전처리 Copilot", page_icon="🤖", layout="wide")
st.title("🧠 AI 기반 데이터 분석 및 전처리 Copilot")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📂 파일 업로드",
    "📊 데이터 분석",
    "💬 질의응답",
    "🧩 전처리",
    "🗃️ MySQL 적재"
])

# =========================
# 📂 1️⃣ 파일 업로드 탭
# =========================
with tab1:
    uploaded_files = st.file_uploader("📤 여러 파일을 업로드하세요", type=["csv", "xlsx", "json"], accept_multiple_files=True)
    if uploaded_files:
        st.session_state["dfs"] = {}
        for file in uploaded_files:
            try:
                if file.name.endswith(".csv"):
                    df = pd.read_csv(file)
                elif file.name.endswith(".xlsx"):
                    df = pd.read_excel(file)
                elif file.name.endswith(".json"):
                    df = pd.read_json(file)
                else:
                    st.warning(f"❌ {file.name}은(는) 지원되지 않는 형식입니다.")
                    continue
                st.session_state["dfs"][file.name] = df
                st.success(f"✅ {file.name} 업로드 완료 ({df.shape[0]}행 × {df.shape[1]}열)")
            except Exception as e:
                st.error(f"{file.name} 로드 오류: {e}")

# =========================
# 📊 2️⃣ 데이터 분석 탭
# =========================
with tab2:
    if "dfs" not in st.session_state or not st.session_state["dfs"]:
        st.warning("⚠️ 먼저 파일을 업로드하세요.")
    else:
        dfs = st.session_state["dfs"]
        st.subheader("📋 업로드된 데이터 요약")

        summaries = {}
        for name, df in dfs.items():
            summary = {
                "shape": df.shape,
                "missing_values": int(df.isnull().sum().sum()),
                "duplicated_rows": int(df.duplicated().sum()),
                "columns": list(df.columns),
                "types": df.dtypes.astype(str).to_dict()
            }
            summaries[name] = summary
            with st.expander(f"📄 {name} 데이터 요약"):
                st.json(summary)
                st.dataframe(df.head(5))

        # =========================
        # 🧠 AI 분석 보고서 생성
        # =========================
        if st.button("🧠 AI 데이터 분석 보고서 생성"):
            prompt = PromptTemplate.from_template("""
            다음은 사용자가 업로드한 여러 데이터셋의 요약 정보입니다.
            각 데이터셋의 주요 특징, 결측치, 중복률, 데이터 크기, 공통 컬럼, 병합 가능성 등을 기반으로
            데이터 분석 보고서를 작성해줘.
            
            데이터 요약:
            {summaries}
            """)
            ai_report = llm.invoke(prompt.format(summaries=json.dumps(summaries, ensure_ascii=False)))
            st.session_state["ai_report"] = ai_report.content
            st.success("✅ AI 분석 보고서 생성 완료!")
            st.markdown("### 📊 AI 데이터 분석 보고서")
            st.write(ai_report.content)

# =========================
# 💬 3️⃣ 대화형 질의응답 탭
# =========================
with tab3:
    if "dfs" not in st.session_state:
        st.warning("⚠️ 먼저 데이터를 업로드하세요.")
    else:
        st.subheader("💬 데이터 질의응답 (LLM + Pandas Agent)")

        df_names = list(st.session_state["dfs"].keys())
        selected_file = st.selectbox("질의할 데이터셋 선택", df_names)
        df = st.session_state["dfs"][selected_file]

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        query = st.chat_input("데이터에 대해 질문하세요 (예: 결측치가 가장 많은 컬럼은?)")

        if query:
            agent = create_pandas_dataframe_agent(llm, df, verbose=False)
            response = agent.run(query)
            st.session_state.chat_history.append((query, response))

        for q, a in st.session_state.chat_history:
            st.markdown(f"**🧑 질문:** {q}")
            st.markdown(f"**🤖 답변:** {a}")

# =========================
# 🧩 4️⃣ 전처리 탭
# =========================
with tab4:
    if "dfs" not in st.session_state:
        st.warning("⚠️ 먼저 데이터를 업로드하세요.")
    else:
        df_names = list(st.session_state["dfs"].keys())
        selected_file = st.selectbox("전처리할 데이터셋 선택", df_names)
        df = st.session_state["dfs"][selected_file]

        st.subheader("🧠 AI 전처리 제안")
        if st.button("전처리 제안 받기"):
            summary = {
                "shape": df.shape,
                "missing_values": int(df.isnull().sum().sum()),
                "duplicated_rows": int(df.duplicated().sum()),
                "columns": list(df.columns),
                "types": df.dtypes.astype(str).to_dict()
            }
            prompt = PromptTemplate.from_template("""
            아래 데이터 요약 정보를 바탕으로, 적절한 전처리 단계를 제안해줘.
            (예: 결측치 처리, 이상치 제거, 형변환, 인코딩 등)
            
            데이터 요약:
            {summary}
            """)
            suggestion = llm.invoke(prompt.format(summary=json.dumps(summary, ensure_ascii=False)))
            st.session_state["ai_suggestion"] = suggestion.content
            st.write(suggestion.content)

        st.subheader("⚙️ 사용자 정의 전처리 실행")
        actions = st.text_area("수행할 전처리 명령 (예: fillna=0, drop_duplicates, encode=label)")
        if st.button("🚀 전처리 실행"):
            df_clean = df.copy()
            try:
                if "fillna" in actions:
                    df_clean = df_clean.fillna(0)
                if "drop_duplicates" in actions:
                    df_clean = df_clean.drop_duplicates()
                if "encode" in actions:
                    from sklearn.preprocessing import LabelEncoder
                    enc = LabelEncoder()
                    for col in df_clean.select_dtypes(include=["object"]).columns:
                        df_clean[col] = enc.fit_transform(df_clean[col].astype(str))
                st.session_state["cleaned_df"] = df_clean
                st.success("✅ 전처리 완료!")
                st.dataframe(df_clean.head())
            except Exception as e:
                st.error(f"전처리 중 오류 발생: {e}")

# =========================
# 🗃️ 5️⃣ MySQL 적재 탭
# =========================
with tab5:
    if "cleaned_df" not in st.session_state:
        st.warning("⚠️ 먼저 전처리를 완료하세요.")
    else:
        st.subheader("🗃️ MySQL 데이터베이스 적재")

        host = st.text_input("MySQL 호스트", "localhost")
        port = st.text_input("포트", "3306")
        user = st.text_input("MySQL 사용자", "root")
        password = st.text_input("MySQL 비밀번호", type="password")
        database = st.text_input("DB 이름", "preprocessed_data")
        table_name = st.text_input("테이블 이름", "cleaned_table")

        if st.button("📥 MySQL 업로드"):
            try:
                engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
                st.session_state["cleaned_df"].to_sql(
                    name=table_name,
                    con=engine,
                    if_exists="replace",
                    index=False
                )
                st.success(f"✅ `{database}` DB의 `{table_name}` 테이블에 업로드 완료!")
            except Exception as e:
                st.error(f"MySQL 업로드 실패: {e}")
