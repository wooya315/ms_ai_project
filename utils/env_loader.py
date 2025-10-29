from dotenv import load_dotenv
import os

def load_env():
    load_dotenv()
    required = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "DEPLOYMENT_NAME", "OPENAI_API_VERSION"]
    for key in required:
        if not os.getenv(key):
            raise EnvironmentError(f"환경 변수 누락: {key}")
