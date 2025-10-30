# modules/blob_uploader.py
import os
from azure.storage.blob import BlobServiceClient
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def get_blob_service_client():
    """환경 변수 기반으로 BlobServiceClient 초기화"""
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
    endpoint_suffix = os.getenv("AZURE_ENDPOINT_SUFFIX", "core.windows.net")

    if not account_name or not account_key:
        raise ValueError("환경 변수 AZURE_STORAGE_ACCOUNT_NAME 또는 AZURE_STORAGE_ACCOUNT_KEY가 설정되지 않았습니다.")

    connection_str = (
        f"DefaultEndpointsProtocol=https;"
        f"AccountName={account_name};"
        f"AccountKey={account_key};"
        f"EndpointSuffix={endpoint_suffix}"
    )

    return BlobServiceClient.from_connection_string(connection_str)


def upload_to_azure_blob(cleaned_results: dict, selected_files: list, container_name: str = "raw-data"):
    """
    전처리된 DataFrame들을 Azure Blob Storage로 업로드

    Args:
        cleaned_results (dict): 파일명 → DataFrame 매핑
        selected_files (list): 업로드할 파일명 리스트
        container_name (str): 대상 컨테이너명 (기본값 raw-data)
    """
    try:
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(container_name)

        # 컨테이너 없으면 생성
        if not container_client.exists():
            container_client.create_container()
            st.info(f"ℹ️ '{container_name}' 컨테이너가 존재하지 않아 새로 생성했습니다.")

        # 파일 업로드
        for name in selected_files:
            if name not in cleaned_results:
                st.warning(f"⚠️ '{name}' 데이터가 세션에 존재하지 않습니다.")
                continue

            df = cleaned_results[name]
            blob_name = f"processed_{name.replace('/', '_')}.csv"
            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")

            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(csv_bytes, overwrite=True)

            st.success(f"✅ {blob_name} 업로드 완료")

        st.success(f"🎉 총 {len(selected_files)}개 파일이 '{container_name}' 컨테이너에 업로드되었습니다.")

    except Exception as e:
        st.error(f"❌ 업로드 실패: {e}")
