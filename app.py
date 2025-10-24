import streamlit as st
from azure.storage.blob import BlobServiceClient
import os
import time
from dotenv import load_dotenv
from config import EXTENSION_FOLDERS

# ✅ .env 파일 로드
load_dotenv()

# ✅ 환경 변수 가져오기
azure_storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
azure_storage_account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
container_name = os.getenv("AZURE_CONTAINER_NAME", "raw-data")

# ✅ Blob Service Client 생성
blob_service_client = BlobServiceClient.from_connection_string(
    f"DefaultEndpointsProtocol=https;AccountName={azure_storage_account_name};AccountKey={azure_storage_account_key};EndpointSuffix=core.windows.net"
)

# ✅ 파일 업로드 함수
def upload_to_azure_storage(file):
    ext = os.path.splitext(file.name)[1].lower().replace(".", "")
    folder = EXTENSION_FOLDERS.get(ext, "others/")
    blob_path = f"{folder}{file.name}"
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
    blob_client.upload_blob(file, overwrite=True)
    return blob_path


# ✅ Streamlit UI
st.title("☁️ Azure Storage 다중 파일 업로더 (진행률 표시)")

uploaded_files = st.file_uploader("📂 여러 파일을 선택하세요", accept_multiple_files=True)

if uploaded_files:
    total_files = len(uploaded_files)
    st.write(f"총 {total_files}개의 파일이 선택되었습니다.")
    
    # 상태 메시지와 진행률 바
    status_text = st.empty()
    progress_bar = st.progress(0)

    if st.button("📤 Azure Storage로 업로드"):
        success, fail = 0, 0

        for idx, f in enumerate(uploaded_files, start=1):
            try:
                upload_to_azure_storage(f)
                success += 1
            except Exception as e:
                fail += 1
                st.error(f"❌ {f.name} 업로드 실패: {e}")

            # ✅ 진행 상태 갱신
            progress = int((idx / total_files) * 100)
            progress_bar.progress(progress)
            status_text.text(f"📦 업로드 중... {idx}/{total_files} 완료 ({progress}%)")

            # (선택) 업로드 간 짧은 지연을 주면 시각적으로 더 자연스럽게 보임
            time.sleep(0.2)

        # 완료 후 상태 표시
        progress_bar.empty()
        status_text.text(f"✅ 업로드 완료: {success}개 성공, {fail}개 실패")
        st.success("🎉 모든 업로드가 완료되었습니다.")
