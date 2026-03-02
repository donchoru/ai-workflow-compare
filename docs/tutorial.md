# 교육용 튜토리얼 — AI 에이전트 워크플로우 이해하기

> 이 문서는 AI 에이전트가 어떻게 동작하는지 **처음부터 끝까지** 따라가며 이해할 수 있도록 구성했습니다.
> 코드를 읽기 전에 이 문서를 먼저 읽으면, 전체 구조가 머릿속에 잡힙니다.

---

## 목차

1. [학습 경로 (어디서부터 읽을까?)](#1-학습-경로)
2. [용어 사전](#2-용어-사전)
3. [동일 질문 처리 과정 비교](#3-동일-질문-처리-과정-비교)
4. [핵심 코드 스니펫](#4-핵심-코드-스니펫)
5. [FM I/O 트레이스 읽는 법](#5-fm-io-트레이스-읽는-법)
6. [자주 묻는 질문 (FAQ)](#6-자주-묻는-질문)

---

## 1. 학습 경로

> **"600줄 코드를 처음부터 다 읽지 마세요."** 아래 순서대로 5단계로 나눠서 읽으면 됩니다.

### Step 1: 큰 그림 잡기 (10분)

| 순서 | 파일 | 읽을 내용 |
|------|------|-----------|
| 1-1 | `README.md` | 전체 구조, 비교 표, Mermaid 다이어그램 |
| 1-2 | `docs/comparison.md` | LangGraph vs Dify 7가지 관점 비교 |
| 1-3 | `docs/architecture-decision.md` | **왜** 이 조합을 선택했는지 (ADR) |

**이 단계의 목표:** "LangGraph는 코드로 짜고, Dify는 캔버스에서 드래그&드롭" 정도만 이해하면 됩니다.

### Step 2: 데이터 구조 이해 (10분)

| 순서 | 파일 | 읽을 내용 |
|------|------|-----------|
| 2-1 | `shared/db/schema.sql` | 6개 테이블 구조 (장비, 부하율, 알림, Lot) |
| 2-2 | `shared/db/seed.py` | 샘플 데이터가 어떻게 생기는지 |
| 2-3 | `shared/tool_server/server.py` | 10개 REST API 엔드포인트 |

**이 단계의 목표:** "장비 30대, 부하율 720건, 알림 250건이 SQLite에 들어있고, FastAPI로 노출된다"

### Step 3: LangGraph 에이전트 흐름 (20분) ← 가장 중요

| 순서 | 파일 | 핵심 |
|------|------|------|
| 3-1 | `langgraph/agents/state.py` | **AgentState** — 에이전트가 공유하는 상태 구조 |
| 3-2 | `langgraph/agents/prompts.py` | 프롬프트가 LLM에게 **무엇을 시키는지** |
| 3-3 | `langgraph/graph/workflow.py` | **그래프 정의** — 누가 → 누구에게 → 언제 전달하는지 |
| 3-4 | `langgraph/agents/intent_agent.py` | 의도분류 Agent (LLM 호출 → JSON 파싱) |
| 3-5 | `langgraph/agents/info_agent.py` | 정보조회 Agent (Tool 호출 + 재진입 루프) |
| 3-6 | `langgraph/tools/sql_tools.py` | 10개 SQL 도구 구현체 |

**이 단계의 목표:** "질문이 들어오면 의도분류 → 도구 선택 → SQL 실행 → 응답 생성" 흐름을 코드로 추적할 수 있다.

### Step 4: Dify 워크플로우 비교 (10분)

| 순서 | 파일 | 핵심 |
|------|------|------|
| 4-1 | `dify/workflows/equipment-agent.yml` | 노드/엣지를 YAML로 정의하는 방식 |
| 4-2 | `dify/tools/openapi.yaml` | Dify가 Tool Server를 인식하는 방법 |
| 4-3 | `docs/examples.md` | 같은 질문에 대한 처리 흐름 차이 |

**이 단계의 목표:** "LangGraph에서 코드 60줄로 한 걸, Dify는 YAML 설정으로 하는구나"

### Step 5: 실제 돌려보기 (10분)

```bash
# 원클릭 데모
export GEMINI_API_KEY="your-key"
./run_demo.sh
```

**이 단계의 목표:** 실제 LLM이 어떤 응답을 내놓는지 직접 확인. 같은 질문의 답이 같은지 다른지 비교.

---

## 2. 용어 사전

AI 에이전트 개발에서 자주 등장하는 용어를 정리합니다.

### 핵심 개념

| 용어 | 영문 | 설명 | 이 프로젝트에서의 예시 |
|------|------|------|----------------------|
| **에이전트 (Agent)** | Agent | LLM이 스스로 판단하고 도구를 호출하는 자율적 프로그램 | IntentAgent, InfoAgent |
| **도구 (Tool)** | Tool | 에이전트가 호출할 수 있는 함수/API | `get_overloaded_equipment()` |
| **의도 (Intent)** | Intent | 사용자 질문의 목적을 분류한 것 | `overload_check`, `equipment_status` |
| **상태 (State)** | State | 에이전트들이 공유하는 데이터 구조 | `AgentState` TypedDict |
| **프롬프트 (Prompt)** | Prompt | LLM에게 보내는 지시 텍스트 | `INTENT_SYSTEM_PROMPT` |
| **트레이스 (Trace)** | Trace | 에이전트의 실행 과정을 기록한 로그 | `traces/trace_*.md` 파일 |

### LangGraph 전용 용어

| 용어 | 설명 | 코드 위치 |
|------|------|-----------|
| **StateGraph** | 노드와 엣지로 구성된 상태 기반 그래프 | `graph/workflow.py` |
| **Node** | 그래프에서 실행 단위 (함수) | `intent_node`, `info_node`, `respond_node` |
| **Edge** | 노드 간 연결. 조건부 라우팅 가능 | `add_conditional_edges()` |
| **ToolNode** | LangGraph가 제공하는 도구 실행 노드 | `from langgraph.prebuilt import ToolNode` |
| **@tool** | LangChain 데코레이터 — 함수를 도구로 등록 | `tools/sql_tools.py` |
| **Function Calling** | LLM이 "이 함수를 이 인자로 호출해"라고 응답하는 기능 | InfoAgent의 `bind_tools()` |
| **add_messages** | 메시지 리스트를 누적하는 LangGraph 어노테이션 | `Annotated[list, add_messages]` |

### Dify 전용 용어

| 용어 | 설명 | 파일 위치 |
|------|------|-----------|
| **DSL** | Dify Specific Language — 워크플로우 정의 포맷 | `dify/workflows/*.yml` |
| **Question Classifier** | 질문을 카테고리로 분류하는 내장 노드 | `question_classifier` 노드 |
| **HTTP Request 노드** | 외부 API를 호출하는 노드 | `http_equipment_status` 등 |
| **캔버스 (Canvas)** | 워크플로우를 시각적으로 편집하는 UI | Dify 웹 인터페이스 |

### Open WebUI 전용 용어

| 용어 | 설명 | 파일 위치 |
|------|------|-----------|
| **Pipeline** | 메시지 처리 파이프라인 클래스 | `open-webui/pipelines/*.py` |
| **Valves** | 파이프라인 설정값 (UI에서 수정 가능) | `Pipeline.Valves` 내부 클래스 |
| **pipe()** | 메시지 수신 시 호출되는 메인 함수 | `Pipeline.pipe()` |

### LLM/AI 공통 용어

| 용어 | 설명 |
|------|------|
| **FM (Foundation Model)** | 기반 모델 — Gemini, GPT, QWEN 등 |
| **FM I/O** | FM에 보낸 입력(Input)과 받은 출력(Output) |
| **Temperature** | LLM 응답의 창의성 조절 (0=결정적, 1=창의적) |
| **Token** | LLM이 처리하는 텍스트 단위 (한글 1자 ≈ 2~3 토큰) |
| **토큰 트리밍** | 컨텍스트 윈도우 초과를 방지하기 위한 메시지 축소 |
| **Disambiguation** | 의미 모호성 해소 — 여러 해석 가능 시 모두 처리 |

---

## 3. 동일 질문 처리 과정 비교

> **"과부하 장비 있어?"** — 같은 질문이 LangGraph와 Dify에서 어떻게 다르게 처리되는지 단계별로 따라갑니다.

### LangGraph: 5단계 처리

```
사용자: "과부하 장비 있어?"
```

#### Step 1. IntentAgent (의도분류)

```
┌─────────────────────────────────────────────────────────┐
│  FM 입력 (→ Gemini)                                     │
│  ─────────────────                                       │
│  System: "당신은 물류 장비 부하율 관리 시스템의          │
│           의도분석 Agent입니다..."  (984자)               │
│  Human:  "과부하 장비 있어?"                             │
│                                                          │
│  FM 출력 (← Gemini)                                     │
│  ─────────────────                                       │
│  {                                                       │
│    "intent": "overload_check",                           │
│    "detail": { "equipment_type": "", "line": "" ... },   │
│    "reasoning": "과부하 장비 확인 요청"                   │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
```

**무슨 일이 일어났나?**
- LLM에게 시스템 프롬프트(6가지 의도 목록)와 사용자 질문을 보냄
- LLM이 JSON으로 `overload_check` 의도 반환
- `detail`은 비어있음 (특정 장비/라인 지정 없음)

#### Step 2. 라우팅 (route_by_intent)

```
intent == "overload_check" (≠ "general_chat")
  → info_agent로 이동  ✓
```

#### Step 3. InfoAgent (도구 선택)

```
┌─────────────────────────────────────────────────────────┐
│  FM 입력 (→ Gemini + 10개 도구 바인딩)                  │
│  ─────────────────                                       │
│  System: INFO_SYSTEM_PROMPT (10개 도구 설명)             │
│  Human:  "사용자 질문: 과부하 장비 있어?                 │
│           의도: overload_check                            │
│           상세: {...}                                     │
│           위 의도에 맞는 도구를 호출하여 정보를 조회하세요."│
│                                                          │
│  FM 출력 (← Gemini)                                     │
│  ─────────────────                                       │
│  tool_calls: [                                           │
│    { name: "get_overloaded_equipment", args: {} }        │
│  ]                                                       │
└─────────────────────────────────────────────────────────┘
```

**무슨 일이 일어났나?**
- LLM이 `.bind_tools(ALL_TOOLS)`로 10개 도구를 "알고 있는" 상태
- 질문과 의도를 보고 `get_overloaded_equipment` 도구를 **스스로 선택**
- Function Calling — 텍스트가 아닌 `tool_calls` 형태로 응답

#### Step 4. ToolNode (SQL 실행)

```
get_overloaded_equipment({})
  ↓
  SQL: SELECT e.*, lr.load_rate_pct, at.warning_pct, at.critical_pct
       FROM equipment e
       JOIN (SELECT ... MAX(load_rate_pct) ...) lr ON ...
       JOIN alert_threshold at ON ...
       WHERE lr.load_rate_pct >= at.critical_pct
  ↓
  결과: [
    {"equipment_id": "CVR-L1-CELL-01", "load_rate_pct": 99.8, ...},
    {"equipment_id": "SHT-L3-CELL-01", "load_rate_pct": 99.3, ...},
    ...
  ]
```

#### Step 5. InfoAgent 재진입 → ResponseAgent

```
┌─────────────────────────────────────────────────────────┐
│  InfoAgent가 Tool 결과를 받고 다시 LLM 호출              │
│  → tool_calls 없이 텍스트 응답 생성                      │
│  → ResponseAgent가 최종 응답으로 확정                     │
│                                                          │
│  최종 응답:                                              │
│  "🚨 과부하 장비 목록입니다.                              │
│                                                          │
│   | 장비 ID         | 유형     | 부하율(%) |              │
│   | CVR-L1-CELL-01  | CONVEYOR | 99.8     |              │
│   | SHT-L3-CELL-01  | SHUTTLE  | 99.3     |              │
│   | ..."                                                 │
└─────────────────────────────────────────────────────────┘
```

**핵심 포인트:**
- InfoAgent → ToolNode → InfoAgent 재진입 — **루프** 구조
- 도구를 더 호출할 필요 없으면 텍스트 응답 → ResponseAgent로 이동

---

### Dify: 4단계 처리 (같은 질문)

```
사용자: "과부하 장비 있어?"
```

#### Step 1. Question Classifier

```
┌─────────────────────────────────────────────────────────┐
│  Gemini에게 질문 전달                                    │
│  → 6개 클래스 중 "과부하 확인" 선택                      │
│  → sourceHandle: overload_check                          │
│  → 다음 노드: http_overloaded                            │
└─────────────────────────────────────────────────────────┘
```

#### Step 2. HTTP Request (고정 엔드포인트)

```
GET http://host.docker.internal:8400/tools/equipment/overloaded
→ JSON 응답 수신
```

#### Step 3. LLM 응답 생성

```
┌─────────────────────────────────────────────────────────┐
│  System: "과부하 장비를 분석하여 긴급도 순으로 보고하세요"│
│  User:   "사용자 질문: 과부하 장비 있어?                 │
│           과부하 장비: {API 결과}"                        │
│  → LLM이 표 형식 한국어 응답 생성                        │
└─────────────────────────────────────────────────────────┘
```

#### Step 4. End (응답 출력)

```
→ result 변수에 LLM 응답 저장
→ 사용자에게 전달
```

---

### 차이가 극명하게 드러나는 질문: "설비 Lot 알려줘"

이 질문이 왜 중요한지 — **모호한 질문**이기 때문입니다.

"설비에 있는 Lot"은 두 가지 의미:
- 📍 **물리적으로** 지금 설비에 있는 Lot
- 📅 **스케줄상** 예정된 Lot

```
┌── LangGraph ──────────────────────────────────────┐
│  LLM이 판단: "모호하다 → 두 도구 모두 호출"       │
│                                                    │
│  tool_calls: [                                     │
│    get_lots_on_equipment({equipment_id: "..."}),   │
│    get_lots_scheduled_for_equipment({...})          │
│  ]                                                 │
│                                                    │
│  결과:                                             │
│  📍 현재 있는 Lot: LOT-012                        │
│  📅 예정된 Lot: LOT-005, LOT-023                  │
└────────────────────────────────────────────────────┘

┌── Dify ───────────────────────────────────────────┐
│  Question Classifier → "Lot 조회"                  │
│  → http_zones (구간별 요약 API 1개만 호출)         │
│                                                    │
│  결과:                                             │
│  구간별 요약 데이터만 표시                         │
│  (물리적 위치 vs 스케줄 구분 불가)                 │
└────────────────────────────────────────────────────┘
```

**결론:** LangGraph는 LLM이 **자율적으로** 2개 도구를 동시 호출합니다.
Dify는 워크플로우에 **고정된** 1개 엔드포인트만 호출합니다.

---

## 4. 핵심 코드 스니펫

> 600줄 전체를 읽지 않아도, 아래 5개 스니펫만 이해하면 핵심이 잡힙니다.

### 4-1. AgentState — 에이전트가 공유하는 상태

```python
# langgraph/agents/state.py

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # 메시지 누적
    intent: str                    # 분류된 의도 (overload_check 등)
    intent_detail: str             # 상세 파라미터 (JSON 문자열)
    trace_log: list[str]           # 실행 트레이스 로그
    user_input: str                # 원본 사용자 입력
    final_answer: str              # 최종 응답
    conversation_history: list[dict]  # 멀티턴 대화 이력
```

**왜 중요한가?**
- 모든 에이전트(IntentAgent, InfoAgent, ResponseAgent)가 **이 하나의 State를 공유**
- `messages`에 `add_messages` 어노테이션 → 메시지가 **덮어쓰기가 아닌 누적**
- 각 에이전트는 State의 일부를 읽고, 일부를 업데이트

### 4-2. 그래프 정의 — 누가 → 누구에게

```python
# langgraph/graph/workflow.py

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # 노드 등록 (이름 → 함수)
    graph.add_node("intent_agent", intent_node)
    graph.add_node("info_agent", info_node)
    graph.add_node("tools", tool_node_with_trace)
    graph.add_node("respond", respond_node)

    # 시작점
    graph.set_entry_point("intent_agent")

    # 조건부 라우팅: intent_agent 다음에 어디로?
    graph.add_conditional_edges("intent_agent", route_by_intent, {
        "info_agent": "info_agent",   # 장비 관련 질문
        "respond": "respond",          # 일반 대화
    })

    # 조건부 라우팅: info_agent 다음에 어디로?
    graph.add_conditional_edges("info_agent", should_use_tools, {
        "tools": "tools",     # 도구 호출 필요
        "respond": "respond", # 텍스트 응답 완료
    })

    # 도구 실행 후 → 다시 info_agent로 (재진입 루프)
    graph.add_edge("tools", "info_agent")

    # 응답 생성 후 → 종료
    graph.add_edge("respond", END)

    return graph.compile()
```

**왜 중요한가?**
- 이 30줄이 **전체 에이전트 흐름**을 정의
- `tools → info_agent` 엣지가 **재진입 루프**를 만듦 (도구 결과 수신 → 추가 도구 호출 또는 응답)
- `route_by_intent`와 `should_use_tools`가 **분기 로직**

### 4-3. Intent 분류 — LLM에게 "분류해줘"

```python
# langgraph/agents/intent_agent.py (핵심 부분)

def intent_node(state: AgentState) -> dict:
    user_input = state["user_input"]
    history = state.get("conversation_history", [])

    prompt_text = _build_context(user_input, history)  # 멀티턴 컨텍스트 구성
    response = llm.invoke([
        SystemMessage(content=INTENT_SYSTEM_PROMPT),   # "6가지 의도 중 분류하세요"
        HumanMessage(content=prompt_text),             # "과부하 장비 있어?"
    ])

    raw = response.content.strip()
    parsed = json.loads(raw)  # JSON 파싱

    return {
        "intent": parsed["intent"],          # "overload_check"
        "intent_detail": json.dumps(parsed["detail"]),
    }
```

**왜 중요한가?**
- LLM에게 시스템 프롬프트로 **분류 규칙**을 알려주고, JSON으로 받음
- `_build_context()`로 **멀티턴 대화 이력**을 포함 — "그럼", "거기" 같은 대명사 해소
- 에러 시 `general_chat`으로 폴백

### 4-4. Function Calling — LLM이 도구를 "선택"

```python
# langgraph/agents/info_agent.py (핵심 부분)

# LLM에 10개 도구를 바인딩 (LLM이 이 도구들의 존재를 "안다")
llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GEMINI_API_KEY,
    temperature=0,
).bind_tools(ALL_TOOLS)  # ← 핵심!

def info_node(state: AgentState) -> dict:
    # ...
    response = llm.invoke(llm_messages)

    # LLM이 도구를 호출하면 → tool_calls가 있음
    if response.tool_calls:
        # [{"name": "get_overloaded_equipment", "args": {}}]
        # → ToolNode가 실제 SQL 실행
        pass
    else:
        # 텍스트 응답 → ResponseAgent로 이동
        pass

    return {"messages": [response]}
```

**왜 중요한가?**
- `.bind_tools(ALL_TOOLS)` — LLM이 10개 도구의 이름, 설명, 파라미터를 앎
- LLM은 텍스트 대신 `tool_calls`로 응답 → LangGraph가 자동으로 해당 함수 실행
- **이것이 Dify와의 핵심 차이** — Dify는 워크플로우에서 고정 분기, LangGraph는 LLM이 자율 선택

### 4-5. @tool 데코레이터 — SQL을 도구로 등록

```python
# langgraph/tools/sql_tools.py (1개 도구 예시)

@tool
def get_overloaded_equipment(
    equipment_type: str = "",
    line: str = "",
) -> str:
    """과부하(CRITICAL 임계값 이상) 장비를 조회합니다.
    최근 1시간 내 가장 높은 부하율이 임계값을 넘는 장비를 반환합니다.
    """
    conditions = ["lr.recorded_at >= datetime('now', '-1 hour')"]
    params = []
    if equipment_type:
        conditions.append("e.equipment_type = ?")
        params.append(equipment_type)
    if line:
        conditions.append("e.line = ?")
        params.append(line)

    sql = f"""
    SELECT e.equipment_id, e.equipment_type, e.line, e.zone, e.status,
           lr.recorded_at, lr.load_rate_pct,
           at.warning_pct, at.critical_pct
    FROM equipment e
    JOIN (...) lr ON e.equipment_id = lr.equipment_id
    JOIN alert_threshold at ON e.equipment_type = at.equipment_type
    WHERE {' AND '.join(conditions)}
      AND lr.load_rate_pct >= at.critical_pct
    ORDER BY lr.load_rate_pct DESC
    """
    rows = query(sql, params)
    return json.dumps(rows, ensure_ascii=False)
```

**왜 중요한가?**
- `@tool` 데코레이터 하나로 **일반 함수가 LLM 호출 가능한 도구**가 됨
- 독스트링(docstring)이 LLM에게 전달됨 → LLM이 이걸 읽고 언제 호출할지 판단
- 파라미터 타입/기본값도 LLM에 전달 → LLM이 적절한 인자를 넣어 호출

---

## 5. FM I/O 트레이스 읽는 법

> 에이전트가 **실제로** 어떤 입력을 LLM에 보내고, 어떤 출력을 받았는지 확인할 수 있습니다.
> 이것은 디버깅과 프롬프트 튜닝에 핵심적인 정보입니다.

### 트레이스 파일 구조

```
traces/
├── trace_20260302_164603.md   ← "과부하 장비 있어?" 트레이스
└── trace_20260302_172819.md   ← "안녕하세요" 트레이스
```

### 트레이스 읽는 법

트레이스 파일은 마크다운으로 작성되며, 각 Step마다 **State BEFORE → FM I/O → State AFTER** 구조입니다.

#### 예시: "과부하 장비 있어?" 트레이스

```markdown
## Step 1: IntentAgent (의도분석)
### State BEFORE                          ← 이 시점의 상태
- user_input: "과부하 장비 있어?"
- intent: ""                              ← 아직 분류 안 됨
- messages (0건)                          ← 메시지 없음

### FM 입력 (→ Gemini gemini-2.0-flash)   ← LLM에 보낸 것
- System: INTENT_SYSTEM_PROMPT (984자)
- Human: "과부하 장비 있어?"

### FM 출력 (← Gemini)                    ← LLM이 응답한 것
{
  "intent": "overload_check",
  "reasoning": "과부하 장비 확인 요청"
}

### State AFTER                           ← 업데이트된 상태
- intent: "overload_check"                ← 분류 완료!
- messages (0건)

---
## Step 2: InfoAgent (정보조회)
### FM 입력 (첫 호출)
  "의도: overload_check"

### FM 출력 → Tool 호출: ['get_overloaded_equipment']
                                          ← LLM이 도구 선택!
---
## Step 2.5: ToolNode (SQL 실행)
### 실행할 Tool
- get_overloaded_equipment({})

### Tool 실행 결과
- ToolMessage: [{"equipment_id": "CVR-L1-CELL-01", ...}]
                                          ← SQL 쿼리 결과

---
## Step 2: InfoAgent 재진입 (Tool 결과 수신)
### FM 출력 → 텍스트 응답: "🚨 과부하 장비..."
                                          ← 더 이상 tool_calls 없음 → 응답 완료

---
## Step 3: ResponseAgent (응답생성)
### 최종 응답: "🚨 과부하 장비 목록입니다..."
```

### 트레이스에서 주목할 포인트

| 구간 | 주목할 것 | 왜? |
|------|-----------|-----|
| **State BEFORE** | `messages` 건수 | 0건이면 첫 호출, N건이면 재진입 |
| **FM 입력** | System 프롬프트 길이 | 프롬프트가 너무 길면 비용/성능 이슈 |
| **FM 출력** | `tool_calls` vs 텍스트 | 도구를 호출했는지, 응답을 생성했는지 |
| **Tool 결과** | 데이터 크기 | 트리밍이 필요한지 (MAX_TOOL_RESULT_CHARS=3000) |
| **State AFTER** | `intent`, `messages` | 상태가 올바르게 업데이트되었는지 |

### "안녕하세요" vs "과부하 장비 있어?" 비교

| 항목 | "안녕하세요" | "과부하 장비 있어?" |
|------|-------------|-------------------|
| Step 수 | 2 (Intent → Respond) | 5 (Intent → Info → Tool → Info → Respond) |
| 도구 호출 | 없음 | `get_overloaded_equipment` |
| LLM 호출 횟수 | 2회 (분류 + 응답) | 3회 (분류 + 도구선택 + 응답생성) |
| 라우팅 | `general_chat` → respond 직행 | `overload_check` → info_agent |

> 실제 트레이스 파일: `docs/traces/` 디렉토리 참고

---

## 6. 자주 묻는 질문

### Q1. LangGraph가 Dify보다 항상 좋은가요?

**아닙니다.** 용도가 다릅니다.

| 상황 | 추천 |
|------|------|
| 도구 10개 중 LLM이 골라야 한다 | LangGraph |
| 모호한 질문에 2개 동시 호출 필요 | LangGraph |
| 비개발자가 워크플로우 수정해야 한다 | Dify |
| 빠르게 프로토타입 만들어 데모 | Dify |
| 단순한 파이프라인 (입력→처리→출력) | Dify |

### Q2. Function Calling이 정확히 뭔가요?

일반적인 LLM 호출:
```
입력: "오늘 서울 날씨 알려줘"
출력: "죄송합니다, 실시간 날씨 정보에 접근할 수 없습니다."  (할 수 있는 게 없음)
```

Function Calling이 있는 LLM 호출:
```
입력: "오늘 서울 날씨 알려줘" + [도구: get_weather(city)]
출력: tool_calls: [{ name: "get_weather", args: { city: "Seoul" } }]
      → 프로그램이 get_weather("Seoul") 실행
      → 결과를 다시 LLM에 전달
      → LLM: "서울은 현재 맑음, 기온 12°C입니다."
```

**핵심:** LLM이 "이 함수를 이 인자로 호출해줘"라고 **구조화된 응답**을 하는 것.

### Q3. StateGraph의 `add_messages` 어노테이션은 왜 필요한가요?

일반 TypedDict에서:
```python
# 노드 A가 반환: {"messages": [msg1]}
# 노드 B가 반환: {"messages": [msg2]}
# → 결과: messages = [msg2]  (덮어쓰기!)
```

`add_messages` 어노테이션 사용 시:
```python
# 노드 A가 반환: {"messages": [msg1]}
# 노드 B가 반환: {"messages": [msg2]}
# → 결과: messages = [msg1, msg2]  (누적!)
```

이게 없으면 InfoAgent → ToolNode → InfoAgent 재진입 시 이전 메시지가 사라집니다.

### Q4. 토큰 트리밍은 왜 필요한가요?

LLM에는 **컨텍스트 윈도우** 한계가 있습니다 (Gemini 2.0 Flash: ~100만 토큰).
도구 결과가 길면 (예: 장비 30대의 상세 정보) 빠르게 한계에 도달합니다.

```python
# langgraph/agents/message_trimmer.py — 3계층 방어

# 1계층: 개별 ToolMessage 축소 (3000자 제한)
MAX_TOOL_RESULT_CHARS = 3000

# 2계층: 메시지 윈도우 (최근 12개만 유지)
MAX_MESSAGES = 12

# 3계층: 전체 총량 제한 (30000자)
MAX_TOTAL_CHARS = 30000
```

### Q5. Open WebUI는 왜 비교 대상에서 빠졌나요?

Open WebUI는 **채팅 프론트엔드**이고, LangGraph/Dify는 **워크플로우 오케스트레이션 도구**입니다.

비유하면:
- LangGraph/Dify = **요리사** (재료를 가공하여 요리)
- Open WebUI = **접시** (요리를 예쁘게 담아 제공)

실무에서는 **조합**합니다: Open WebUI(접시) + LangGraph(요리사).

---

## 다음 단계

이 튜토리얼을 마쳤다면:

1. **`./run_demo.sh`** 로 실제 동작 확인
2. **`langgraph/traces/`** 에서 실제 트레이스 파일 분석
3. **`langgraph/agents/prompts.py`** 의 프롬프트를 수정해보며 결과 변화 관찰
4. **새로운 도구 추가** — `tools/sql_tools.py`에 11번째 도구를 만들어보기
5. **Dify import** — `dify/workflows/equipment-agent.yml`을 실제 Dify에 불러와서 비교
