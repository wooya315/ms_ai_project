import os
import io
import pandas as pd
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def test_azure_connection() -> bool:
    """Azure Blob 연결 테스트"""
    try:
        account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        container_name = os.getenv("AZURE_CONTAINER_NAME", "preprocessed-data")

        if not all([account_name, account_key]):
            st.error("❌ .env 파일의 Azure Storage 설정이 누락되었습니다.")
            return False

        blob_service_client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net",
            credential=account_key
        )
        # 단순 요청으로 연결 확인
        _ = blob_service_client.list_containers()
        st.success(f"✅ Azure Blob 연결 성공: {account_name}")
        return True

    except Exception as e:
        st.error(f"❌ Azure Blob 연결 실패: {e}")
        return False


def upload_to_azure_blob(selected_dataframes: dict, container_name: str = None):
    """선택된 DataFrame들을 Parquet으로 변환 후 Azure Blob에 업로드"""
    try:
        account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        container_name = container_name or os.getenv("AZURE_CONTAINER_NAME", "preprocessed-data")

        blob_service_client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net",
            credential=account_key
        )

        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            blob_service_client.create_container(container_name)
            st.info(f"🆕 새 컨테이너 '{container_name}' 생성 완료")

        for name, df in selected_dataframes.items():
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
            parquet_buffer.seek(0)

            blob_name = f"cleaned_{os.path.splitext(os.path.basename(name))[0]}.parquet"
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(parquet_buffer, overwrite=True)
            st.success(f"✅ 업로드 완료: {blob_name} ({len(df)} rows)")

        st.info("🎉 모든 선택 파일 Parquet 업로드 완료!")

    except Exception as e:
        st.error(f"❌ 업로드 중 오류 발생: {e}")
