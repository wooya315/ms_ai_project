import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
import os
from dotenv import load_dotenv

# ===== 모듈 import =====
from modules.loader import load_uploaded_files
from modules.quality_checker import summarize_dataframe
from modules.ai_agent import init_azure_client, run_ai_report, run_qa, run_data_processing
from modules.cleaner import preprocess_dataframe
from modules.blob_uploader import upload_to_azure_blob


# ===== 환경 설정 =====
load_dotenv()
st.set_page_config(page_title="🧠 데이터 품질 점검 & 전처리 에이전트", page_icon="🤖", layout="wide")

# ===== 제목 =====
st.markdown("""
<h2 style='text-align:center; color:#4B9CD3;'>🧠 데이터 품질 점검 & 전처리 에이전트</h2>
<p style='text-align:center; color:gray;'>데이터를 업로드하면 AI가 품질 점검, 전처리, 추가 가공까지 수행합니다.</p>
""", unsafe_allow_html=True)

# ===== 세션 상태 초기화 =====
for key, default in {
    "preload_quality_report": None,
    "qa_history": [],
    "ai_history": [],
    "cleaned_results": None,
    "uploaded_file_names": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ===== Azure 클라이언트 초기화 =====
client = init_azure_client()

# ===== 1️⃣ 파일 업로드 =====
uploaded_files = st.file_uploader(
    "📦 CSV / XLSX / TXT / XML / JSON / ZIP 업로드",
    type=["csv", "xlsx", "txt", "xml", "json", "zip"],
    accept_multiple_files=True,
    key="file_uploader_main"
)

dfs = {}

if uploaded_files:
    current_file_names = [f.name for f in uploaded_files]
    if current_file_names != st.session_state["uploaded_file_names"]:
        st.session_state["uploaded_file_names"] = current_file_names
        st.session_state["preload_quality_report"] = None
        st.session_state["qa_history"] = []

    dfs = load_uploaded_files(uploaded_files)
    st.success(f"✅ 총 {len(dfs)}개의 데이터셋 로드 완료")

    st.markdown("### 📊 업로드된 데이터 미리보기")
    for name, df in dfs.items():
        with st.expander(f"🔍 {name} 미리보기"):
            st.dataframe(df.head(), width="stretch")

# ===== 2️⃣ 품질 점검 리포트 + Q&A =====
if dfs:
    st.markdown("---")
    st.subheader("🧠 데이터 품질 점검 보고서")

    table_summaries = {name: summarize_dataframe(df, name) for name, df in dfs.items()}

    if st.button("보고서 생성하기"):
        with st.spinner("AI가 데이터 품질 점검 중입니다..."):
            ai_report = run_ai_report(client, table_summaries)
            st.session_state["preload_quality_report"] = ai_report
        st.success("✅ 품질 점검 리포트가 생성되었습니다.")

    if st.session_state["preload_quality_report"]:
        st.markdown(st.session_state["preload_quality_report"])
    else:
        st.info("아직 리포트를 생성하지 않았습니다.")

    # ===== Q&A =====
    st.markdown("---")
    st.subheader("💬 리포트 기반 Q&A")

    for user_q, ai_a in st.session_state["qa_history"]:
        with st.chat_message("user"):
            st.markdown(f"**{user_q}**")
        with st.chat_message("assistant"):
            st.markdown(ai_a)

    with st.form(key="qa_form", clear_on_submit=True):
        user_question = st.text_area("리포트에 대해 질문하기", placeholder="리포트 내용에 대해 궁금한 점을 입력하세요...")
        submitted = st.form_submit_button("질문하기")

    if submitted and user_question:
        with st.chat_message("user"):
            st.markdown(user_question)
        with st.spinner("AI가 답변 중입니다..."):
            ai_answer = run_qa(client, st.session_state["preload_quality_report"], user_question)
        st.session_state["qa_history"].append((user_question, ai_answer))
        with st.chat_message("assistant"):
            available_files = list(st.session_state["cleaned_results"].keys())
        st.markdown(ai_answer)

# ===== 3️⃣ 전처리 실행 =====
st.markdown("---")
st.subheader("⚙️ 전처리 실행")

st.caption("""
데이터 적재 전에 적용할 정제 작업을 선택하세요.
- 전체 일괄 적용은 안전한 형식 정규화(strip/케이스/날짜/숫자) 위주로 권장됩니다.
""")

mode = st.radio(
    "전처리 적용 범위",
    ["전체 업로드된 파일에 일괄 적용", "선택한 파일만 처리"],
    index=0 # ✅ 기본 선택을 두 번째 옵션으로 설정
)

if dfs:
    target_table_name = None
    if mode == "선택한 파일만 처리":
        target_table_name = st.multiselect("전처리할 파일 선택", list(dfs.keys()))

    st.markdown("#### 전처리 옵션 선택")
    fillna_opt = st.checkbox("fillna_zero : 결측치 값 채우기", value=False)
    dropdup_opt = st.checkbox("drop_duplicates : 중복행 제거", value=False)
    strip_opt = st.checkbox("strip_strings : 문자열 앞뒤 공백 제거", value=False)
    case_norm = st.selectbox("문자열 대소문자 정규화", ["변경 안 함", "소문자로 통일", "대문자로 통일"], index=0)
    convert_dates_opt = st.checkbox("convert_dates : 문자열 날짜 → datetime 변환", value=False)
    convert_num_opt = st.checkbox("convert_numeric_strings : 문자열 숫자 → 수치형 변환", value=False)
    drop_empty_cols_opt = st.checkbox("drop_empty_cols : 완전 공백 컬럼 제거", value=False)

    if st.button("🚀 전처리 실행"):
        normalize_case_val = (
            "lower" if case_norm == "소문자로 통일"
            else "upper" if case_norm == "대문자로 통일"
            else None
        )

        base_opts = {
            "fillna_zero": fillna_opt,
            "drop_duplicates": dropdup_opt,
            "strip_strings": strip_opt,
            "normalize_case": normalize_case_val,
            "convert_dates": convert_dates_opt,
            "convert_numeric_strings": convert_num_opt,
            "drop_empty_cols": drop_empty_cols_opt,
        }

        results_summary = []
        cleaned_results = {}
        targets = target_table_name if mode == "선택한 파일만 처리" else list(dfs.keys())

        for t in targets:
            before = dfs[t].copy()
            after = preprocess_dataframe(before, base_opts)
            cleaned_results[t] = after

            changed_types = []
            dtypes_before = before.dtypes.astype(str).to_dict()
            dtypes_after = after.dtypes.astype(str).to_dict()
            for col in after.columns:
                if dtypes_before.get(col) != dtypes_after.get(col):
                    changed_types.append(f"{col}: {dtypes_before.get(col)} -> {dtypes_after.get(col)}")

            results_summary.append({
                "table": t,
                "rows_before": len(before),
                "rows_after": len(after),
                "nulls_before": int(before.isna().sum().sum()),
                "nulls_after": int(after.isna().sum().sum()),
                "changed_types": changed_types
            })

        st.session_state["cleaned_results"] = cleaned_results
        st.session_state["results_summary"] = results_summary
        st.success("✅ 전처리 완료! AI 기반 추가 전처리를 이어서 수행할 수 있습니다.")

# ===== 전처리 결과 유지 표시 =====
if st.session_state.get("cleaned_results") and st.session_state.get("results_summary"):
    st.markdown("### 📊 전처리 결과 미리보기")

    for s in st.session_state["results_summary"]:
        table_name = s["table"]
        if table_name not in dfs or table_name not in st.session_state["cleaned_results"]:
            continue

        st.markdown(f"#### ▶ {table_name} 처리 결과")
        colL, colR = st.columns(2)
        with colL:
            st.markdown("**전(before)**")
            st.dataframe(dfs[table_name].head(), width="stretch")
        with colR:
            st.markdown("**후(after)**")
            st.dataframe(st.session_state["cleaned_results"][table_name].head(), width="stretch")

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, df in st.session_state["cleaned_results"].items():
            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            zf.writestr(f"processed_{name.replace('/', '_')}.csv", csv_bytes)
    zip_buffer.seek(0)
    st.download_button(
        label="📥 데이터 ZIP 다운로드",
        data=zip_buffer,
        file_name="processed_datasets.zip",
        mime="application/zip"
    )

# ===== 4️⃣ AI 명령 기반 추가 전처리 =====
if st.session_state.get("cleaned_results"):
    st.markdown("---")
    st.subheader("🤖 AI 명령 기반 후속 전처리")

    for user_q, ai_a in st.session_state["ai_history"]:
        with st.chat_message("user"):
            st.markdown(f"**{user_q}**")
        with st.chat_message("assistant"):
            st.markdown(ai_a)

    with st.form(key="ai_process_form", clear_on_submit=True):
        ai_target = st.selectbox("대상 테이블 선택", list(st.session_state["cleaned_results"].keys()))
        ai_command = st.text_area("전처리 명령 입력", placeholder="예: age 컬럼 제거해줘 / 날짜 포맷 YYYY-MM-DD로 바꿔줘")
        ai_submitted = st.form_submit_button("명령 실행")

    if ai_submitted and ai_command:
        df_before = st.session_state["cleaned_results"][ai_target].copy()

        with st.chat_message("user"):
            st.markdown(f"**{ai_command}**")

        with st.spinner("AI가 명령을 해석하고 데이터를 가공 중입니다..."):
            status, processed_df = run_data_processing(client, df_before, ai_command)

        st.session_state["ai_history"].append((ai_command, status))

        if isinstance(processed_df, pd.DataFrame):
            st.session_state["cleaned_results"][ai_target] = processed_df
            with st.chat_message("assistant"):
                st.success(status)

            st.markdown(f"### 🔄 '{ai_target}' 전처리 결과 비교")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**전(before)**")
                st.dataframe(df_before.head(), width="stretch")
            with col2:
                st.markdown("**후(after)**")
                st.dataframe(processed_df.head(), width="stretch")
        else:
            with st.chat_message("assistant"):
                st.warning(processed_df)

# ☁️ Azure Blob Storage 업로드
st.markdown("### ☁️ Azure Blob Storage 업로드")

if st.session_state.get("cleaned_results") and isinstance(st.session_state["cleaned_results"], dict):
    st.info("✅ 전처리 완료 데이터가 있습니다. 업로드할 파일을 선택하세요.")

    available_files = list(st.session_state["cleaned_results"].keys())
    selected_files = st.multiselect("📂 업로드할 파일 선택", available_files)

    if st.button("🚀 선택한 파일 업로드"):
        with st.spinner("Azure Blob Storage 업로드 중..."):
            upload_to_azure_blob(
                cleaned_results=st.session_state["cleaned_results"],
                selected_files=selected_files,
                container_name=os.getenv("AZURE_CONTAINER_NAME", "raw-data")
            )

else:
    st.info("⚠️ 아직 전처리된 결과가 없습니다. 전처리 후 업로드를 진행해주세요.")
