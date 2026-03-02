# 아키텍처 결정 기록 (ADR)

> **결론: Open WebUI + LangGraph 조합을 선택한다.**
>
> 채팅 UI는 Open WebUI, 에이전트 로직은 LangGraph로 분리하여
> 도구 연동이 필요한 사내 AI 챗봇의 백엔드를 구성한다.

---

## 1. 배경

### 만들려는 것

물류 장비 부하율 관리 AI 챗봇 — 사용자가 자연어로 질문하면 내부 DB를 조회하여 답변.

```
"과부하 장비 있어?" → DB 조회 → "CVR-L1-CELL-01 부하율 99.8% (CRITICAL)"
"L1 컨베이어 상태"  → DB 조회 → "RUNNING 3대, ERROR 1대"
```

### 요구사항

| 항목 | 내용 |
|------|------|
| 사용자 인터페이스 | 웹 기반 채팅 (ChatGPT 스타일) |
| 핵심 기능 | 자연어 → 의도분류 → **10개 SQL 도구** 자율 호출 → 응답 생성 |
| 모호성 처리 | "설비 Lot 알려줘" → 물리적 위치 + 스케줄 **2개 도구 동시 호출** |
| LLM | 현재 Gemini 2.0 Flash → **향후 사내 watsonx (QWEN)으로 전환** |
| 배포 환경 | 사내 서버 (Docker 가능) |

---

## 2. 검토한 선택지

### 선택지 A: Open WebUI → LLM 직접 연결

```
Open WebUI ──→ Gemini / QWEN
                 (Function Calling)
                     ↓
                   DB 조회
```

**장점:**
- 구조가 가장 단순
- 미들웨어 없음

**단점:**
- 의도분류 → 도구선택 → 응답생성 파이프라인을 **직접 구현**해야 함
- 멀티턴 대화 이력 관리 직접 구현
- 모호성 해소 (2개 도구 동시 호출) 직접 구현
- LLM 교체 시 Function Calling 스펙이 달라 **코드 전면 수정**
- 토큰 관리(트리밍) 직접 구현

→ 결국 LangGraph가 해주는 것을 전부 직접 짜야 한다.

### 선택지 B: Open WebUI → Dify → 도구

```
Open WebUI ──→ Dify API ──→ Tool Server ──→ DB
               (워크플로우)    (HTTP)
```

**장점:**
- 워크플로우를 코드 없이 시각적으로 구성
- 프롬프트를 UI에서 실시간 수정 가능
- 배포 시 API 자동 생성
- 비개발자도 워크플로우 수정 가능

**단점:**
- **도구 자율 선택 불가** — 워크플로우에서 의도별 API를 미리 고정해야 함
  - LangGraph: LLM이 10개 도구 중 상황에 맞게 자율 선택
  - Dify: Question Classifier가 분기 → 의도 1개당 API 1개 고정
- **2개 도구 동시 호출 불가** — "설비 Lot" 모호성 해소 패턴 구현 불가
- **인프라 무거움** — Dify 셀프호스트에 PostgreSQL, Redis, Sandbox 등 필요
- **watsonx QWEN 지원 불확실** — Dify 플러그인 생태계에 의존
- **플랫폼 종속** — 워크플로우 DSL이 Dify 전용 포맷

### 선택지 C: Open WebUI → LangGraph (API) → 도구 ✅

```
Open WebUI ──→ LangGraph + LangServe ──→ DB 직접 접근
  (채팅 UI)      (에이전트 로직)           (@tool → SQL)
```

**장점:**
- **도구 자율 선택** — LLM이 10개 도구 중 상황에 맞게 선택
- **동시 호출** — 모호한 질문 시 2개 도구 병렬 호출 (핵심 기능)
- **LLM 교체 용이** — LangChain 추상화 덕에 config 한 줄 변경
  ```python
  # Gemini → watsonx 전환
  # from langchain_google_genai import ChatGoogleGenerativeAI
  from langchain_ibm import ChatWatsonx
  ```
- **이미 구현됨** — 물류 에이전트 코드 600줄이 있음 (재활용)
- **인프라 가벼움** — Python 환경만 있으면 됨
- **테스트 가능** — pytest로 에이전트 로직 단위 테스트
- **Git 친화적** — 코드 리뷰, PR, 버전 관리 자연스러움

**단점:**
- Python 코드 작성/유지보수 필요
- LangChain 생태계 학습 비용
- 배포 시 LangServe 또는 FastAPI 추가 설정

---

## 3. 결정

### Open WebUI + LangGraph를 선택한다.

핵심 근거 3가지:

### 근거 1: 도구 자율 선택이 핵심 요구사항

이 시스템의 가치는 **사용자가 모호하게 물어도 AI가 알아서 맞는 도구를 골라 답하는 것**에 있다.

```
사용자: "CVR-L1-TFT-01에 Lot 뭐 있어?"

LangGraph (자율 선택):
  → LLM이 판단: "모호하다 — 물리적 위치 + 스케줄 둘 다 보여주자"
  → get_lots_on_equipment() + get_lots_scheduled_for_equipment() 동시 호출
  → "📍 현재 있는 Lot: LOT-012  📅 예정된 Lot: LOT-005, LOT-023"

Dify (고정 분기):
  → Question Classifier: "lot_query"
  → 미리 정한 API 1개만 호출
  → 물리적 위치 또는 스케줄 중 하나만 답변 (정보 손실)
```

Dify의 워크플로우 분기로는 이 패턴을 구현할 수 없다.

### 근거 2: LLM 교체가 예정되어 있다

Gemini → watsonx QWEN 전환이 확정된 상황에서:

| 도구 | LLM 교체 비용 |
|------|--------------|
| LangGraph | `config.py` 1줄 변경 (LangChain 추상화) |
| Dify | watsonx 플러그인 존재 여부에 의존. 없으면 커스텀 모델 프로바이더 개발 필요 |
| 직접 연결 | Function Calling 스펙 차이로 코드 전면 수정 |

LangChain은 이미 `langchain-ibm` 패키지로 watsonx를 지원한다:
```python
from langchain_ibm import ChatWatsonx

llm = ChatWatsonx(
    model_id="qwen2.5-72b-instruct",
    url="https://your-watsonx-url",
    project_id="your-project-id",
)
```

### 근거 3: 이미 구현된 코드를 재활용

`langgraph-agent` 프로젝트에 600줄의 검증된 에이전트 코드가 있다:
- IntentAgent (의도분류 + 대명사 해소)
- InfoAgent (도구 호출 + 재진입 루프)
- ResponseAgent (응답 생성)
- 10개 SQL 도구
- 3계층 토큰 관리
- FM I/O 트레이싱

LangServe로 API 래핑만 추가하면 Open WebUI에서 바로 호출 가능.

---

## 4. 최종 아키텍처

```
┌─────────────────┐     OpenAI 호환 API     ┌──────────────────────┐
│                 │ ◄──────────────────────► │                      │
│   Open WebUI    │    POST /chat/completions│  LangGraph +         │
│   (채팅 UI)     │                          │  LangServe           │
│                 │                          │                      │
│  • 대화 이력    │                          │  • IntentAgent       │
│  • 사용자 관리  │                          │  • InfoAgent         │
│  • 파일 업로드  │                          │  • 10개 SQL 도구     │
│                 │                          │  • 토큰 관리         │
└─────────────────┘                          └──────────┬───────────┘
                                                        │
                                                        │ 직접 SQL
                                                        ▼
                                              ┌──────────────────┐
                                              │   SQLite / DB    │
                                              │   (물류 장비)     │
                                              └──────────────────┘
```

### 역할 분리

| 계층 | 담당 | 기술 |
|------|------|------|
| **프론트엔드** | 채팅 UI, 사용자 관리, 대화 이력 표시 | Open WebUI |
| **에이전트 로직** | 의도분류, 도구 선택, 응답 생성, 토큰 관리 | LangGraph + LangServe |
| **데이터** | 물류 장비 DB, SQL 도구 | SQLite (→ 사내 DB) |
| **LLM** | 추론 엔진 | Gemini → watsonx QWEN |

### LLM 전환 로드맵

```
Phase 1 (현재):  Gemini 2.0 Flash  — langchain-google-genai
Phase 2 (전환):  watsonx QWEN      — langchain-ibm
```

변경 범위: `config.py`의 LLM 초기화 코드 **1곳만** 수정.
에이전트 로직, 도구, 프롬프트는 그대로 유지.

---

## 5. Dify는 언제 쓰면 좋은가

Dify가 나쁜 도구라는 뜻이 아니다. **용도가 다르다:**

| 상황 | 추천 |
|------|------|
| 도구 10개 중 LLM이 자율 선택해야 한다 | **LangGraph** |
| 모호한 질문에 2개 도구 동시 호출이 필요하다 | **LangGraph** |
| 비개발자가 워크플로우를 직접 수정해야 한다 | **Dify** |
| 빠르게 프로토타입을 만들어 데모해야 한다 | **Dify** |
| 단순한 파이프라인 (입력→처리→출력)이다 | **Dify** |
| 여러 LLM을 A/B 테스트하고 싶다 | **Dify** |
| LLM 교체가 예정되어 있고 코드 제어가 필요하다 | **LangGraph** |

---

## 6. 이 문서의 범위

| 항목 | 내용 |
|------|------|
| **결정일** | 2026-03-02 |
| **결정자** | 동철 |
| **상태** | 승인됨 |
| **영향 범위** | 물류 장비 AI 챗봇 아키텍처 |
| **관련 코드** | `langgraph/`, `open-webui/`, `shared/` |
| **다음 단계** | LangServe API 래핑 → Open WebUI 연결 → watsonx 전환 테스트 |
