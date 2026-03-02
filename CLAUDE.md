# AI Workflow Compare

LangGraph vs Dify vs Open WebUI 비교 데모 — 물류 장비 부하율 관리.

## 기술 스택
- LLM: Gemini 2.0 Flash (google-generativeai)
- DB: SQLite (logistics.db)
- Python 3.12+ / `.venv/`

## 구조
```
shared/db/           — 공유 DB (schema.sql, seed.py, connection.py)
shared/tool_server/  — FastAPI REST API (:8400)
langgraph/           — 구현 1: LangGraph (코드 퍼스트, ~600줄)
dify/                — 구현 2: Dify (비주얼 워크플로우, YAML)
open-webui/          — 구현 3: Open WebUI (채팅 + Pipeline, ~150줄)
docs/                — 상세 비교 분석
```

## 실행
```bash
python -m shared.db.seed              # DB 생성
python -m shared.tool_server.server   # Tool Server :8400
cd langgraph && python main.py        # LangGraph CLI
```

## DB 테이블 6개
equipment(30), load_rate(720), alert_threshold(6), alert_history(~250), lot(40), lot_schedule(~58)

## SQL 도구 10개 → REST API
1. /tools/equipment/list
2. /tools/equipment/status
3. /tools/equipment/load-rates
4. /tools/equipment/overloaded
5. /tools/equipment/{id}/detail
6. /tools/alerts/recent
7. /tools/zones/summary
8. /tools/lots/on-equipment/{id}
9. /tools/lots/scheduled/{id}
10. /tools/lots/{id}/detail

## 포트
- 8400: Tool Server
- 80: Dify (Docker)
- 3005: Open WebUI (Docker)
