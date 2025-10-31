# 🧠 데이터 품질 점검 & 전처리 에이전트  
*(Data Quality Check & Preprocessing Agent)*  

DB 적재 전에 “이 데이터, 믿어도 될까?”를 대신 점검해주는 **AI 기반 데이터 품질 관리 도구**입니다.  
Streamlit 기반 UI를 통해 **업로드 → 품질 점검 → 전처리 → AI 기반 수정 → Blob 업로드**까지  
한 화면에서 자동 처리할 수 있습니다.  

---

## 🎯 1. 프로젝트 목표  

데이터 엔지니어링에서 반복되는 “적재 전 점검/정제 작업”을 자동화하여  
**데이터 품질과 생산성을 동시에 향상**시키는 것이 목적입니다.  

### 🔍 핵심 기능

| 구분 | 설명 |
|------|------|
| ✅ 데이터 품질 점검 | 결측치, 중복, 타입 불일치, FK/PK 후보, 관계성 등 자동 분석 |
| 💡 AI 품질 리포트 | Azure OpenAI 기반으로 데이터 품질 리포트를 한국어로 생성 |
| 🧩 전처리 실행 | 체크박스로 전처리 옵션 선택 후 즉시 실행 (개별/일괄 적용 가능) |
| 🤖 AI 명령 전처리 | “날짜 포맷 바꿔줘”처럼 자연어로 데이터 수정 명령 수행 |
| ☁️ Azure 업로드 | 전처리 완료 데이터를 Azure Blob Storage로 업로드 |

---

## 🧱 2. 전체 아키텍처

데이터 품질 점검 & 전처리 에이전트의 전체 동작 흐름은 다음과 같습니다.

```
📂 [1] 데이터 업로드
 ┣ CSV / Excel / JSON / XML / ZIP 파일 지원
 ┗ ZIP 파일 내 여러 데이터도 자동 추출 및 개별 테이블 변환

⬇️

🧮 [2] 데이터 분석
 ┣ 결측치, 중복, 타입 불일치, 관계성 등 자동 점검
 ┗ 데이터 요약정보(table_summaries) 생성

⬇️

🤖 [3] AI 품질 리포트
 ┣ Azure OpenAI 모델을 통해 품질 리포트 자동 생성
 ┗ 품질, 결측, 타입, 중복, 관계, 전처리 권장사항 제시

⬇️

💬 [4] Q&A 인터페이스
 ┣ Streamlit 기반 대화형 질의응답
 ┗ 예: "결측치 제일 많은 컬럼은?" / "날짜형 컬럼은 어디 있어?"

⬇️

🧹 [5] 전처리 실행
 ┣ 개별 옵션 또는 전체 일괄 적용 가능
 ┗ 결측치 대체, 중복 제거, 문자열 정규화, 날짜 변환 등

⬇️

🧠 [6] AI 명령 전처리
 ┣ 자연어 기반 명령 수행
 ┗ 예: “age 컬럼 제거해줘”, “날짜 포맷 YYYY-MM-DD로 변경”

⬇️

☁️ [7] 클라우드 업로드
 ┣ 전처리 완료 데이터를 Azure Blob Storage에 저장
 ┗ 이후 DW 또는 파이프라인 적재 가능
```

---

## 💡 3. 주요 흐름 (데모 시 발표 포인트)

### ① 파일 업로드
- CSV, XLSX, JSON, XML, ZIP 파일 모두 지원  
- ZIP 안의 여러 파일도 자동 추출 및 개별 테이블로 변환  
- 인코딩 자동 감지 (utf-8, cp949, euc-kr 등)  
> 🗣 “이 단계에서 현업의 원천데이터를 그대로 올려도 안정적으로 처리됩니다.”

---

### ② AI 기반 품질 점검 리포트
- 각 파일별 요약정보(`table_summaries`)를 Azure OpenAI로 전달  
- 모델이 자동으로 8개 섹션의 품질 리포트를 생성:

1. 데이터 개요  
2. 결측치 현황  
3. 데이터 타입 적합성  
4. 중복 및 유일성  
5. 명명 일관성 및 관계  
6. 종합 의견  
7. 전처리 우선 권장 사항  

> 🗣 “이 리포트는 사람이 수동 점검하던 QA 과정을 자동화한 부분입니다.”

---

### ③ 리포트 기반 Q&A
- Streamlit 챗 UI로 리포트에 대해 자유롭게 질의 가능  

**예시 질문**
- “결측치 제일 많은 컬럼은?”  
- “먼저 적재해야 할 테이블은?”  
- “문자열인데 날짜로 바꿔야 하는 컬럼은?”  

> 🗣 “이 Q&A를 통해 품질 리포트를 ‘대화형 분석 보고서’로 사용할 수 있습니다.”

---

### ④ 전처리 실행 (옵션 기반)
- 개별 처리 모드와 전체 일괄 적용 모드 지원  

| 옵션 | 설명 |
|------|------|
| `fillna_zero` | 결측치를 0 혹은 문자열로 대체 |
| `drop_duplicates` | 중복 행 제거 |
| `strip_strings` | 문자열 앞뒤 공백 제거 |
| `normalize_case` | 문자열 대/소문자 통일 |
| `convert_dates` | 문자열 날짜를 datetime으로 변환 |
| `convert_numeric_strings` | 문자열 숫자("1,234") 변환 |
| `drop_empty_cols` | 완전 공백 컬럼 제거 |

**전/후 비교 화면**
- 행 수 변화  
- 결측치 총량 변화  
- 컬럼 타입 변화  
- 상위 5행 Before / After  

> 🗣 “데이터 엔지니어가 일일이 스크립트를 짜던 정제 과정을 클릭 몇 번으로 끝냅니다.”

---

### ⑤ AI 명령 기반 후속 전처리
자연어 명령으로 데이터 수정 가능  

**예시**
- “age 컬럼 제거해줘”  
- “날짜 포맷을 YYYY-MM-DD로 바꿔줘”  

`run_data_processing()` 함수가 명령을 해석 → Pandas 명령 자동 실행  
결과는 Streamlit UI에서 즉시 Before/After 비교 가능  

---

### ⑥ Azure Blob Storage 업로드
- 전처리 결과(`cleaned_results`)를 선택적으로 업로드  
- 업로드 후 Data Pipeline / DW 적재 자동화 가능  

> 🗣 “이제 정제된 데이터를 바로 클라우드 데이터레이크로 전달합니다.”

📸 **업로드 결과 예시 (Azure Storage Explorer)**  
아래는 전처리 완료된 파일들이 Azure Blob Storage의 `raw-data` 컨테이너에 업로드된 화면입니다.  

![Azure Blob Storage 업로드 결과](스크린샷%202025-10-31%20104645.png)

---

## 🧩 4. 폴더 구조

```
ms_ai_project/
├─ main.py                # Streamlit 앱 진입점
├─ requirements.txt       # 의존성 목록
├─ .env                   # Azure/OpenAI API 설정
└─ modules/
   ├─ loader.py           # 파일 업로드 및 파싱
   ├─ quality_checker.py  # 데이터 요약 및 관계 분석
   ├─ ai_agent.py         # Azure OpenAI 품질 리포트 / Q&A
   ├─ cleaner.py          # 전처리 옵션 로직
   └─ blob_uploader.py    # Azure Blob 업로드
```

---

## ⚙️ 5. 실행 방법

### 1️⃣ 환경 설정  
`.env` 파일 작성  

```env
AZURE_STORAGE_ACCOUNT_NAME=prosangwoostorage  
AZURE_STORAGE_ACCOUNT_KEY=xxxxxx  
AZURE_CONTAINER_NAME=raw-data  
AZURE_OPENAI_API_KEY=xxxxxx  
AZURE_OPENAI_ENDPOINT=https://pro-sangwoo-openai.openai.azure.com/  
OPENAI_API_VERSION=2024-12-01-preview  
DEPLOYMENT_NAME=dev-gpt-4.1-mini  
```

### 2️⃣ 패키지 설치  
```bash
pip install -r requirements.txt
```

### 3️⃣ 실행  
```bash
streamlit run main.py
```

---

> 📘 *이 프로젝트는 데이터 엔지니어의 반복적 품질 점검 작업을 자동화하여,  
보다 정확하고 효율적인 데이터 파이프라인 구축을 지원합니다.*
