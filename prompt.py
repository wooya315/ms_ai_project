from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate

prompt = PromptTemplate.from_template("""
아래 데이터 요약 결과를 기반으로, 필요한 전처리 액션을 제안해줘.
- 결측치 처리
- 이상치 제거
- 데이터 형변환
- 인코딩 필요 여부
{summary}
""")
