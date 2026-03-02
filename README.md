# AI Workflow Compare

LangGraph vs Dify vs Open WebUI — 동일한 유스케이스를 3가지 AI 워크플로우 도구로 구현하여 비교하는 프로젝트.

## 유스케이스

**물류 장비 부하율 관리 AI 어시스턴트**

한국어 자연어 질문 → 의도 분류 → SQL 도구 호출 → 결과 요약 응답

```
"과부하 장비 있어?" → overload_check → get_overloaded_equipment() → "CRITICAL 장비 3대..."
"L1 컨베이어 상태"  → equipment_status → get_equipment_status() → "RUNNING 5대, ERROR 1대..."
```

## 아키텍처

```
┌──────────────────────────────────────────────────────────────────┐
│                     shared/                                      │
│  ┌────────────────┐    ┌─────────────────────────────────────┐   │
│  │ db/            │    │ tool_server/ (:8400)                │   │
│  │  schema.sql    │    │  FastAPI — 10개 REST API            │   │
│  │  seed.py       │◄───│  /tools/equipment/list              │   │
│  │  connection.py │    │  /tools/equipment/overloaded  ...   │   │
│  └────────────────┘    └─────────────────────────────────────┘   │
│         ▲                          ▲          ▲                  │
│         │                          │          │                  │
│  ┌──────┴──────┐    ┌──────────────┴┐  ┌──────┴──────────┐      │
│  │ langgraph/  │    │    dify/      │  │  open-webui/    │      │
│  │ (직접 SQL)  │    │ (HTTP 호출)   │  │ (HTTP 호출)     │      │
│  │ ~600줄      │    │ ~0줄 (YAML)   │  │ ~150줄          │      │
│  └─────────────┘    └───────────────┘  └─────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

## 3가지 구현 비교

| 항목 | LangGraph | Dify | Open WebUI |
|------|-----------|------|------------|
| **접근 방식** | Python 코드 | 비주얼 캔버스 | 채팅 UI + Pipeline |
| **의도분류** | IntentAgent (LLM) | Question Classifier 노드 | LLM 호출 (코드) |
| **도구 호출** | @tool + Function Calling | HTTP Request 노드 | requests (코드) |
| **도구 선택** | LLM이 10개 중 자율 선택 | 워크플로우 고정 라우팅 | 의도별 매핑 (코드) |
| **상태 관리** | TypedDict StateGraph | 자동 (내장) | 대화 히스토리 |
| **멀티턴** | conversation_history 직접 관리 | 내장 대화 관리 | Open WebUI 내장 |
| **모호성 해소** | LLM이 2개 Tool 동시 호출 | 워크플로우 분기 | 코드 매핑 |
| **디버깅** | FM I/O 트레이스 파일 | 내장 실행 로그 | print/로그 |
| **배포** | Python 스크립트 | API 즉시 배포 | Docker |
| **코드량** | ~600줄 | ~0줄 (YAML 설정) | ~150줄 |
| **유연성** | ★★★ 최고 | ★★☆ 중간 | ★★☆ 중간 |
| **진입장벽** | 높음 (Python) | 낮음 (노코드) | 중간 |

## 프로젝트 구조

```
ai-workflow-compare/
├── README.md
├── CLAUDE.md
├── shared/                      # 공유 컴포넌트
│   ├── db/
│   │   ├── schema.sql           # 6 테이블
│   │   ├── seed.py              # 샘플 데이터 (30장비, 720부하율, 40Lot)
│   │   └── connection.py        # SQLite 연결
│   └── tool_server/
│       ├── server.py            # FastAPI REST API (:8400)
│       └── requirements.txt
│
├── langgraph/                   # 구현 1: LangGraph
│   ├── agents/                  # IntentAgent, InfoAgent, ResponseAgent
│   ├── graph/                   # StateGraph + 조건부 라우팅
│   ├── tools/                   # @tool 10개
│   ├── main.py                  # 대화형 CLI
│   └── requirements.txt
│
├── dify/                        # 구현 2: Dify
│   ├── workflows/
│   │   └── equipment-agent.yml  # Dify DSL 워크플로우
│   ├── tools/
│   │   └── openapi.yaml         # OpenAPI 3.0 스펙
│   └── README.md
│
├── open-webui/                  # 구현 3: Open WebUI
│   ├── pipelines/
│   │   └── equipment_agent.py   # Pipeline 클래스
│   ├── docker-compose.yml
│   └── README.md
│
└── docs/
    └── comparison.md            # 상세 비교 분석
```

## 빠른 시작

### 공통: DB + Tool Server

```bash
cd ai-workflow-compare

# 가상환경 + 의존성
python3 -m venv .venv
source .venv/bin/activate
pip install -r shared/tool_server/requirements.txt

# DB 생성
python -m shared.db.seed

# Tool Server 실행 (Dify, Open WebUI용)
python -m shared.tool_server.server  # :8400
```

### LangGraph

```bash
pip install -r langgraph/requirements.txt
export GEMINI_API_KEY="your-key"
cd langgraph && python main.py
```

### Dify

1. Dify 셀프호스트 설치 ([공식 가이드](https://docs.dify.ai))
2. Gemini 플러그인 + API Key 설정
3. `dify/tools/openapi.yaml`로 Custom Tool 등록
4. `dify/workflows/equipment-agent.yml` Import

### Open WebUI

```bash
cd open-webui
docker compose up -d
# http://localhost:3005 접속
# Pipeline Valves에 Gemini API Key 설정
```

## DB 스키마 (6 테이블)

```
equipment (30대)       — 장비 마스터 (CONVEYOR, AGV, CRANE, SORTER, STACKER, SHUTTLE)
load_rate (720건)      — 부하율 이력 (10분 간격, 최근 4시간)
alert_threshold (6건)  — 장비 유형별 경고/위험 임계값
alert_history (~250건) — 알림 이력 (WARNING, CRITICAL)
lot (40건)             — 생산 단위 (SCHEDULED, IN_TRANSIT, IN_PROCESS, COMPLETED)
lot_schedule (~58건)   — Lot 생산 스케줄
```

## SQL 도구 10개

| # | 도구 | API 엔드포인트 |
|---|------|----------------|
| 1 | get_equipment_list | `GET /tools/equipment/list` |
| 2 | get_equipment_status | `GET /tools/equipment/status` |
| 3 | get_load_rates | `GET /tools/equipment/load-rates` |
| 4 | get_overloaded_equipment | `GET /tools/equipment/overloaded` |
| 5 | get_equipment_detail | `GET /tools/equipment/{id}/detail` |
| 6 | get_recent_alerts | `GET /tools/alerts/recent` |
| 7 | get_zone_summary | `GET /tools/zones/summary` |
| 8 | get_lots_on_equipment | `GET /tools/lots/on-equipment/{id}` |
| 9 | get_lots_scheduled | `GET /tools/lots/scheduled/{id}` |
| 10 | get_lot_detail | `GET /tools/lots/{id}/detail` |

## 포트 할당

| 포트 | 서비스 |
|------|--------|
| 8400 | shared/tool_server (FastAPI) |
| 80 | Dify (nginx, Docker) |
| 3005 | Open WebUI (Docker) |

## 기술 스택

- **LLM**: Gemini 2.0 Flash (`google-generativeai`)
- **DB**: SQLite
- **LangGraph**: `langgraph` + `langchain-google-genai`
- **Dify**: 셀프호스트 (Docker)
- **Open WebUI**: Docker + Pipelines

## 상세 비교

[docs/comparison.md](docs/comparison.md) 참고
