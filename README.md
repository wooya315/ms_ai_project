# 🧠 데이터 품질 점검 & 전처리 에이전트  
**(Data Quality Check & Preprocessing Agent)**  

> DB 적재 전에 “이 데이터, 믿어도 될까?”를 대신 점검해주는 AI 도구입니다.  
> Streamlit 기반 UI로, 업로드 → 품질 점검 → 전처리 → AI 기반 수정 → **Azure Blob Storage 업로드**까지  
> **한 화면에서 자동 처리**합니다.

🌐 **실행 주소:** [https://data-preprocessing-agent.azurewebsites.net](https://data-preprocessing-agent.azurewebsites.net)

---

## 🎯 1. 프로젝트 목표

데이터 엔지니어링에서 반복되는 “적재 전 점검/정제 작업”을 자동화하여  
**데이터 품질과 생산성을 동시에 향상시키는 것**이 목적입니다.

### 🔑 핵심 기능

| 구분 | 설명 |
|------|------|
| ✅ **데이터 품질 점검** | 결측치, 중복, 타입 불일치, FK/PK 후보, 관계성 등 자동 분석 |
| 💡 **AI 품질 리포트** | Azure OpenAI 기반으로 데이터 품질 리포트를 한국어로 생성 |
| 🧩 **전처리 실행** | 체크박스로 전처리 옵션 선택 후 즉시 실행 (개별/일괄 적용 가능) |
| 🤖 **AI 명령 전처리** | “날짜 포맷 바꿔줘”처럼 자연어로 데이터 수정 명령 |
| ☁️ **Azure 업로드** | 전처리 완료 데이터를 **Azure Blob Storage**로 업로드 |

---

## 🧱 2. 전체 아키텍처

```mermaid
graph TD
A[📂 데이터 업로드<br/>CSV, Excel, JSON, XML, ZIP 파일] --> B[🧮 데이터 분석<br/>결측치 · 중복 · 타입 점검]
B --> C[🤖 AI 품질 리포트<br/>Azure OpenAI 기반 자동 생성]
C --> D[💬 Q&A 인터페이스<br/>리포트 기반 대화형 질의응답]
D --> E[🧹 전처리 실행<br/>옵션 선택 또는 일괄 정제]
E --> F[🧠 AI 명령 전처리<br/>자연어 명령 예: 날짜 포맷 변경]
F --> G[☁️ 클라우드 업로드<br/>Azure Blob Storage 저장]



---

## ⚙️ 3. 설치 및 실행 가이드

### 1️⃣ 레포지토리 클론
아래 명령어를 통해 프로젝트를 로컬 환경으로 복제합니다.

```bash
git clone https://github.com/wooya315/ms_ai_project.git
cd ms_ai_project
```

---

### 2️⃣ `.env` 파일 생성
레포지토리 루트 경로(`ms_ai_project/`)에 `.env` 파일을 직접 생성하고  
아래 형식에 맞게 값을 기입합니다.

> ⚠️ **주의:** 실제 키 값은 개인 Azure 계정의 정보를 사용하세요.  
> (보안상 아래는 예시 형태입니다.)

```env
AZURE_STORAGE_ACCOUNT_NAME=your_storage_account_name
AZURE_STORAGE_ACCOUNT_KEY=your_storage_account_key
AZURE_CONTAINER_NAME=raw-data
AZURE_OPENAI_API_KEY=your_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
OPENAI_API_VERSION=2024-12-01-preview
DEPLOYMENT_NAME=dev-gpt-4.1-mini
SUSCRIPTION_ID=your_subscription_id
```

---

### 3️⃣ 패키지 설치
필요한 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Streamlit 앱 실행
로컬 환경에서 Streamlit 앱을 실행합니다.

```bash
streamlit run main.py
```

앱이 실행되면 웹 브라우저에서 자동으로 아래 주소로 열립니다:  
➡️ **http://localhost:8501**

> 💡 Azure App Service에 배포된 클라우드 버전은 아래 주소에서 바로 실행할 수 있습니다.  
> 🔗 [https://data-preprocessing-agent.azurewebsites.net](https://data-preprocessing-agent.azurewebsites.net)

---

## 🌐 4. 기술 스택 요약

| 분류 | 기술 |
|------|------|
| **Frontend/UI** | Streamlit |
| **Backend/AI** | Azure OpenAI (GPT-4.1-mini) |
| **ETL/전처리** | Pandas, NumPy |
| **Storage** | Azure Blob Storage |
| **Infra** | Python 3.11, dotenv, LangChain |

---
