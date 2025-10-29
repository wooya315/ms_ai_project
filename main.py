import streamlit as st
import tempfile, os, zipfile, json
import pandas as pd
from dotenv import load_dotenv

# ===== 모듈 import =====
from modules.loader import load_uploaded_files
from modules.quality_checker import summarize_dataframe, find_relations
from modules.ai_agent import init_azure_client, run_ai_report, run_qa
from modules.cleaner import preprocess_dataframe
from modules.db_uploader import upload_to_mysql

# ===== 환경 설정 =====
load_dotenv()
st.set_page_config(page_title="🧠 데이터 품질 점검 & 전처리 에이전트", page_icon="🤖", layout="wide")

# ===== 제목 =====
st.markdown("""
<h2 style='text-align:center; color:#4B9CD3;'>🧠 데이터 품질 점검 & 전처리 에이전트</h2>
<p style='text-align:center; color:gray;'>데이터를 업로드하면, AI가 자동으로 품질 점검과 전처리 제안을 수행합니다.</p>
""", unsafe_allow_html=True)

# ===== 세션 초기화 =====
if "preload_quality_report" not in st.session_state:
    st.session_state["preload_quality_report"] = None
if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []
if "cleaned_df" not in st.session_state:
    st.session_state["cleaned_df"] = None

# ===== Azure 클라이언트 초기화 =====
client = init_azure_client()

# ===== 1️⃣ 파일 업로드 =====
uploaded_files = st.file_uploader(
    "📦 CSV / XLSX / TXT / XML / JSON / ZIP 업로드",
    type=["csv","xlsx","txt","xml", "json", "zip"],
    accept_multiple_files=True,
    key="file_uploader_main"
)
dfs = {}

if uploaded_files:
    st.session_state["preload_quality_report"] = None
    dfs = load_uploaded_files(uploaded_files)
    st.success(f"✅ 총 {len(dfs)}개의 데이터셋 로드 완료")

# ===== 2️⃣ 품질 점검 리포트 + Q&A =====
if dfs:
    table_summaries = {name: summarize_dataframe(df, name) for name, df in dfs.items()}
    relations = find_relations(dfs)

    st.markdown("---")
    st.subheader("🧠 데이터 품질 점검 보고서")

    button_clicked = st.button("보고서 생성하기")

    if button_clicked:
        # 리포트 생성
        if st.session_state["preload_quality_report"] is None:
            with st.spinner("AI가 데이터 품질 점검 중입니다..."):
                ai_report = run_ai_report(client, table_summaries, relations)
                st.session_state["preload_quality_report"] = ai_report

        # 리포트 출력
        if st.session_state["preload_quality_report"]:
            st.markdown(st.session_state["preload_quality_report"])
        else:
            st.info("아직 품질 점검 리포트가 생성되지 않았습니다.")

    # Q&A 구간
    st.subheader("💬 리포트 기반 Q&A")
    st.caption("리포트를 기반으로 궁금한 점을 바로 물어보세요 (예: 결측치가 가장 많은 컬럼은?).")

    for user_q, ai_a in st.session_state["qa_history"]:
        with st.chat_message("user"):
            st.markdown(f"**{user_q}**")
        with st.chat_message("assistant"):
            st.markdown(ai_a)

    user_question = st.chat_input("🗨️ 리포트에 대해 질문하기...")

    if user_question:
        with st.chat_message("user"):
            st.markdown(user_question)
        with st.spinner("AI가 답변 중입니다..."):
            ai_answer = run_qa(client, st.session_state["preload_quality_report"], user_question)
        st.session_state["qa_history"].append((user_question, ai_answer))
        with st.chat_message("assistant"):
            st.markdown(ai_answer)

    # ===== 4️⃣ 전처리 실행 =====
    st.markdown("---")
    st.subheader("⚙️ 전처리 실행")

    file_to_clean = st.selectbox("전처리할 파일 선택", list(dfs.keys()))
    df = dfs[file_to_clean]

    fillna_opt = st.checkbox("결측치 0으로 채우기")
    dropdup_opt = st.checkbox("중복행 제거")

    if st.button("🚀 전처리 실행"):
        # 전처리 옵션 정리
        opts = {
            "fillna_zero": fillna_opt,
            "drop_duplicates": dropdup_opt,
        }

        # 원본 복사
        original_df = df.copy()

        # 전처리 수행
        cleaned_df = preprocess_dataframe(df, opts)
        st.session_state["cleaned_df"] = cleaned_df

        # ===== 변화 요약 계산 =====
        rows_before = len(original_df)
        rows_after = len(cleaned_df)

        nulls_before = int(original_df.isna().sum().sum())
        nulls_after = int(cleaned_df.isna().sum().sum())

        # dtype 변화 감지
        dtypes_before = original_df.dtypes.astype(str).to_dict()
        dtypes_after = cleaned_df.dtypes.astype(str).to_dict()

        changed_types = []
        for col in cleaned_df.columns:
            before_t = dtypes_before.get(col)
            after_t = dtypes_after.get(col)
            if before_t != after_t:
                changed_types.append(f"- {col}: {before_t} -> {after_t}")

        # ===== UI 출력 =====
        st.success("✅ 전처리 완료!")

        st.markdown("#### 전처리 결과 요약")
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.metric(
                label="행 개수",
                value=f"{rows_after}",
                delta=f"{rows_after - rows_before} (전 {rows_before})"
            )

        with col_b:
            st.metric(
                label="결측치 총 개수",
                value=f"{nulls_after}",
                delta=f"{nulls_after - nulls_before} (전 {nulls_before})"
            )

        with col_c:
            st.metric(
                label="컬럼 수",
                value=f"{cleaned_df.shape[1]}",
                delta=f"{cleaned_df.shape[1] - original_df.shape[1]} (전 {original_df.shape[1]})"
            )

        # dtype 변경 사항 표시
        if changed_types:
            st.markdown("#### 변경된 컬럼 타입")
            st.code("\n".join(changed_types), language="text")

        # 전/후 미리보기 나란히 보기
        st.markdown("#### 전처리 전/후 샘플 비교 (상위 5행)")
        preview_col1, preview_col2 = st.columns(2)

        with preview_col1:
            st.markdown("**전(before)**")
            st.dataframe(original_df.head(), use_container_width=True)

        with preview_col2:
            st.markdown("**후(after)**")
            st.dataframe(cleaned_df.head(), use_container_width=True)