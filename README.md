# 데이터 전처리 AI 에이전트 (ms_ai_project)

DB 넣기 전에 "이 데이터 믿어도 되는가?"를 대신 확인해주는 도구.  
여러 형식의 원시 데이터를 업로드하면 → 품질 점검 리포트 생성 → 전처리 권장안 제시 → 클릭으로 실제 전처리 수행 → Azure blob storage 적재까지 간다.

모든 흐름은 로컬(Streamlit)에서 한 화면으로 처리됩니다.

🌐 **실행 주소:** [https://data-preprocessing-agent.azurewebsites.net](https://data-preprocessing-agent.azurewebsites.net)
---

## 1. 📌 프로젝트 목적

현업에서 데이터를 DB(MySQL 등)에 적재하기 전에 반복적으로 하는 점검/정제 작업을 자동화하는 것이 목표입니다.

이 도구는 다음을 수행합니다:

1. **데이터 품질 사전 점검**
   - 결측치, 타입 불일치, 중복키 가능성, FK/PK 후보 등 확인
   - 테이블 간 관계 후보(참조 관계)까지 식별 시도

2. **전처리 전략 제안**
   - “이 컬럼은 날짜 문자열이라 datetime으로 바꿔야 함”
   - “이 테이블은 중복행 제거 필요”
   - “이 필드는 전부 동일값이므로 드롭 고려 가능”
   같은 전처리 권장 사항을 자동으로 리포트 형태로 제안

3. **전처리 실행**
   - 사용자가 체크박스만 선택하면 실제 전처리를 수행
   - 특정 테이블 하나만 처리할 수도 있고, 전체 업로드된 테이블에 공통 변환을 일괄 적용할 수도 있음

4. **DB 적재 준비**
   - 전처리 후 결과를 MySQL에 바로 업로드할 수 있도록 지원
   - 업로드 전 전/후 비교 리포트로 신뢰성 확보  
     (행 수 변화, 결측치 변화, 컬럼 타입 변화 등)


---

## 2. 🧱 아키텍처 구성 요소

### 2.1 Streamlit UI (`main.py`)
- 파일 업로드 (여러 파일, 여러 포맷 동시 업로드 가능)
- 품질 점검 보고서 생성 버튼 / 결과 표시
- 보고서 기반 Q&A (챗 형태)
- 전처리 옵션 선택 및 실행
- 전/후 비교 요약 표시
- MySQL 업로드 폼

### 2.2 데이터 로더 (`modules/loader.py`)
- CSV / XLSX / TXT / XML / JSON / ZIP 등 다양한 형식의 원시 파일을 `pandas.DataFrame`으로 변환
- ZIP 내부에 있는 여러 파일도 자동 분해하여 각각의 DataFrame으로 로딩
- 인코딩 자동 추정 (`utf-8`, `utf-8-sig`, `cp949`, `euc-kr` 등)으로 한글 CSV/TXT 안정적으로 처리
- JSON은 아래 모두 지원:
  - `[{"a":1}, {"a":2}]` 리스트 형태
  - `{"data":[...]}`
  - 단일 오브젝트 `{...}`

### 2.3 품질 분석기 (`modules/quality_checker.py`)
- 각 테이블에 대해:
  - 행/열 크기
  - 컬럼 타입
  - 결측치 개수
  - 유니크 값 개수
  - 샘플 행
- 테이블 간 관계 후보를 추출 (예: `USER_ID`, `*_ID` 등 컬럼명 패턴 기반으로 FK처럼 보이는 관계)
- 이 정보를 AI에게 전달 가능한 구조(`table_summaries`, `relations`)로 구성

### 2.4 AI 품질 리포트 & Q&A (`modules/ai_agent.py`)
- Azure OpenAI API를 사용해 “사전 적재 데이터 품질 점검 보고서”를 한국어로 생성
- 기본 섹션(예시):
  1. 데이터 개요  
  2. 결측치 현황  
  3. 데이터 타입 적합성  
  4. 중복 및 유일성  
  5. 명명 일관성 및 관계  
  6. PK/FK 후보 분석 (가능한 경우)  
  7. 종합 의견  
  8. 전처리 우선 권장 사항  
     - 실제 전처리 옵션명(`fillna_zero`, `drop_duplicates`, `strip_strings`, `convert_dates`, `convert_numeric_strings`) 단위로 어떤 처리를 추천하는지 서술

- 보고서는 `st.session_state["preload_quality_report"]`에 저장되어 유지  
  → 사용자가 Q&A를 반복해도 리포트 내용은 바뀌지 않고 동일한 기준을 사용

- 리포트 바로 아래에서 질문 가능:
  - 예: "결측치 제일 많은 컬럼은 어디야?"
  - 예: "어떤 테이블을 먼저 DB에 적재해야 해?"
  - 답변은 `run_qa()`가 `preload_quality_report`를 컨텍스트로 Azure OpenAI에 질문하여 생성


### 2.5 전처리 엔진 (`modules/cleaner.py`)
전처리는 사용자가 체크한 옵션을 기반으로 `preprocess_dataframe()`에서 실제로 이루어진다.

지원 옵션(확장 가능):

- `fillna_zero`  
  결측치를 0 등 기본값으로 채움 (주의: 의미 있는 결측까지 덮을 수 있으므로 주로 수치형 컬럼에 한정)

- `drop_duplicates`  
  중복 행 제거 (PK 후보 컬럼 정리용)

- `strip_strings`  
  문자열 컬럼의 앞뒤 공백 제거 및 공백/불필요 문자 정리

- `normalize_case`  
  문자열 컬럼 전체를 소문자 또는 대문자로 강제해 카테고리/코드값 일관성 확보

- `convert_dates`  
  날짜처럼 보이는 컬럼(예: `*_DT`, `*_DATE`, `REGIST_DT`)이 문자열(object)인 경우
  → `datetime64[ns]`로 변환  
  변환 성공률(파싱 성공 비율)이 일정 이상일 때만 실제 변환 수행

- `convert_numeric_strings`  
  `"1,234"`, `"10.5%"` 같은 문자열 숫자들을 쉼표/퍼센트 제거 후 float/int로 변환  
  비율이 충분히 높을 경우에만 컬럼 전체를 숫자형으로 변환

전처리 이후에는 즉시 전/후 비교 리포트가 Streamlit에 출력된다:
- 행 개수 변화(중복 제거 여부)
- 결측치 총 개수 변화
- 변경된 컬럼 타입 목록 (예: `FRST_REGIST_DT: object -> datetime64[ns]`)
- before / after 상위 5행 비교

전처리 결과 저장:
- 단일 테이블 처리 시 → `st.session_state["cleaned_df"]`
- 전체 일괄 처리 시 → `st.session_state["cleaned_all"][테이블명]`


### 2.6 DB 업로더 (`modules/db_uploader.py`)
- 전처리된 결과(`cleaned_df`)를 MySQL에 업로드
- Streamlit UI에서 호스트, 포트, 유저, 비밀번호, DB명, 테이블명을 입력
- SQLAlchemy를 이용하여 `to_sql(if_exists="replace")`로 밀어 넣는다

(차후 확장: 여러 테이블을 한 번에 업로드하고 FK/PK 제약까지 자동 설정하는 플로우도 가능)


---

## 3. 📂 지원 파일 포맷

업로드 가능한 입력 파일 형식:

- `.csv`
- `.xlsx`
- `.txt`
  - 구분자(콤마, 탭, 세미콜론 등) 자동 추정
  - 헤더 유무도 자동 추정
- `.xml`
  - `pandas.read_xml()` 시도
  - 안 되면 커스텀 파서로 반복 노드를 평탄화하여 DataFrame 구성
- `.json`
  - 리스트 형태(`[{"...":...}, {...}]`)
  - 래핑 형태(`{"data":[...]}`)
  - 단일 객체(`{"a":1,"b":2}`)
  → 전부 DataFrame으로 변환 시도
- `.zip`
  - ZIP 내부의 `.csv`, `.xlsx`, `.txt`, `.xml`, `.json` 파일을 전부 개별 테이블로 로딩

파일을 올리면 `dfs`라는 딕셔너리에 `{파일명: DataFrame}` 구조로 저장되어 이후 단계(리포트/전처리/업로드)에 사용된다.

인코딩은 `utf-8`, `utf-8-sig`, `cp949`, `euc-kr` 등을 자동으로 시도한다 (한글 CSV/TXT 방어).


---

## 4. 🖥️ Streamlit UI 플로우

### 단계 1: 파일 업로드
- 여러 파일 동시 업로드 가능
- 새로 업로드할 경우 세션 상태 초기화  
  (`preload_quality_report`, `qa_history`, 전처리 결과 등 초기화)

### 단계 2: "보고서 생성하기"
- 버튼 클릭 시 Azure OpenAI로 분석 요청
- “사전 적재 데이터 품질 점검 보고서”를 생성하고 `st.session_state["preload_quality_report"]`에 저장
- 리포트에는 다음이 포함:
  - 결측치 상황
  - 타입 적합성 (문자열 날짜/숫자 등)
  - PK/FK 후보 및 중복 위험
  - 테이블 간 관계 가능성
  - "전처리 우선 권장 사항" (아래 전처리 옵션 이름을 그대로 사용)

> 이 리포트는 세션에 고정되므로 이후 Q&A와 전처리에서 같은 보고서를 기준으로 계속 참조한다.

### 단계 3: 리포트 기반 Q&A
- 리포트 아래에서 바로 질문 가능
- Q&A는 채팅 UI로 누적 표시 (`qa_history`)
- 질문 예시:
  - "어떤 컬럼이 날짜 문자열로 되어 있어?"
  - "먼저 적재할 테이블 순서 추천해줘"
  - "결측치 많은 컬럼 어떻게 처리해야 해?"

### 단계 4: 전처리 실행
전처리는 두 가지 모드로 실행 가능:

1. **선택한 파일만 처리**
   - 특정 테이블 하나만 선택해서 처리
   - 비교적 공격적인 옵션(예: `drop_duplicates`, `fillna_zero`)도 사용자가 직접 체크해서 수행 가능
   - 결과는 `cleaned_df`에 저장되고 이후 바로 MySQL 업로드 가능

2. **전체 업로드된 파일에 일괄 적용**
   - 모든 테이블에 대해 공통적인 정규화 작업(안전한 변환)을 한 번에 수행  
     - 예) `strip_strings`, `convert_dates`, `convert_numeric_strings`
   - 위험도가 높은 작업(`fillna_zero`, `drop_duplicates`)은 일괄 모드에서는 기본적으로 자동 OFF 처리하여 데이터 손실/왜곡을 방지
   - 결과는 `cleaned_all[테이블명]`으로 저장

전처리 실행 후에는 각 테이블별로:
- 행 개수 전/후 비교
- 결측치 총량 전/후 비교
- 타입 변경된 컬럼 목록
- before / after 상위 5행 미리보기  
를 즉시 출력하여 사람이 검증 가능하게 한다.

### 단계 5: MySQL 업로드
- 단일 테이블 전처리 결과(`cleaned_df`)를 대상으로 업로드 가능
- UI에서 DB 접속 정보와 테이블 이름을 입력하고 업로드를 실행
- 업로드 성공/실패 메시지 표시

(멀티 테이블 업로드(`cleaned_all`)는 후속 확장 포인트)


---

## 5. 🤖 AI 리포트 구조 (품질 보고서)

`modules/ai_agent.py`의 `run_ai_report()`는 Azure OpenAI에게 아래 정보를 준다:
- `table_summaries`: 각 테이블 요약(행 수, 컬럼 타입, 결측치 등)
- `relations`: 테이블 간 FK 후보 관계

모델은 아래와 같은 섹션 순서로 보고서를 생성한다 (한국어):

1. **데이터 개요**  
   - 파일명, 행/열 수 등 기본 스펙

2. **결측치 현황**  
   - 결측률이 높은 컬럼
   - “이 컬럼은 90%가 비어있으므로 분석/적재 시 주의”

3. **데이터 타입 적합성**  
   - 날짜가 object 문자열로 되어 있는 컬럼
   - 숫자가 문자열("1,234", "10.5%")로 들어간 컬럼 등

4. **중복 및 유일성**  
   - PK 후보로 보이는 컬럼에서 중복 여부
   - 중복 제거 필요성(drop_duplicates)

5. **명명 일관성 및 관계**  
   - 컬럼 네이밍 규칙(대문자/스네이크 등)
   - `*_ID` 형태 컬럼이 다른 테이블의 키를 참조할 가능성

6. **PK/FK 후보 분석** (존재할 경우)  
   - 어떤 컬럼이 PK로 쓰일 수 있는지
   - 어떤 컬럼이 다른 테이블을 참조(FK)하는지
   - 적재 순서 (부모 테이블 → 자식 테이블)

7. **종합 의견**  
   - 적재 전 주의해야 할 포인트 요약

8. **전처리 우선 권장 사항**  
   - 실제 전처리 엔진 옵션명 그대로 사용:
     - `fillna_zero`
     - `drop_duplicates`
     - `strip_strings`
     - `convert_dates`
     - `convert_numeric_strings`
   - 어떤 테이블/컬럼에 어느 옵션을 우선 적용해야 하는지 불릿으로 제안
   - 예:
     - `convert_dates`: `FRST_REGIST_DT`, `LAST_UPDT_DT` 컬럼은 문자열 상태이므로 datetime 변환 필요  
     - `convert_numeric_strings`: 금액/비율 컬럼은 쉼표·% 제거 후 숫자화 필요  
     - `drop_duplicates`: `CD_ID` 값이 중복될 가능성이 있어 중복 행 확인/정리 필요  
     - `fillna_zero`: 일부 보조 수치 컬럼은 대부분 결측이므로 기본값 채우기 검토  
     - `strip_strings`: 코드성 필드(Y/N 등)는 공백 및 대소문자 정규화 필요

보고서 마지막 문장은  
**"이상으로 사전 적재 데이터 품질 점검 보고서를 마칩니다."**  
로 끝나며, “문의 바랍니다” 같은 비즈니스/영업성 멘트는 나오지 않도록 프롬프트에서 제한한다.

이 리포트는 Streamlit 세션에 저장되어 Q&A와 전처리 UI의 기준선 역할을 한다.


---

## 6. 📁 디렉터리 구조 (예시)

```text
ms_ai_project/
├─ main.py                        # Streamlit 앱 엔트리포인트 (UI)
├─ requirements.txt               # 의존성 패키지
├─ .env                           # Azure/OpenAI API 설정 등
└─ modules/
   ├─ loader.py                   # 파일 업로드 → DataFrame 변환
   ├─ quality_checker.py          # 테이블 요약 및 관계 후보 분석
   ├─ ai_agent.py                 # Azure OpenAI 호출 (품질 보고서 / Q&A)
   ├─ cleaner.py                  # 전처리 로직 (fillna_zero, convert_dates 등)
   └─ db_uploader.py              # MySQL 업로드
