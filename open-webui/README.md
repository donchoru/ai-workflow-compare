# Open WebUI 구현 — 물류 장비 부하율 관리

채팅 UI + Pipeline 방식으로 동일한 유스케이스를 구현합니다.

## 아키텍처

```
사용자 (Open WebUI 채팅)
    ↓
[Pipeline: equipment_agent.py]
    ├─ 1. 의도분류 (Gemini 직접 호출)
    ├─ 2. Tool 호출 (tool_server HTTP)
    └─ 3. 응답생성 (Gemini 직접 호출)
    ↓
채팅 응답
```

## 설정 방법

### 1. Tool Server 실행

```bash
cd ai-workflow-compare
python -m shared.db.seed             # DB 생성
python -m shared.tool_server.server  # :8400 실행
```

### 2. Open WebUI + Pipelines 기동

```bash
cd open-webui
docker compose up -d
```

- Open WebUI: `http://localhost:3005`
- Pipelines: `http://localhost:9099`

### 3. Pipeline 설정

Pipeline 파일 `pipelines/equipment_agent.py`가 자동으로 마운트됩니다.

1. Open WebUI 접속 → 설정 → Pipelines
2. `물류 장비 부하율 관리` 파이프라인 확인
3. Valves 설정:
   - `gemini_api_key`: Gemini API 키 입력
   - `tool_server_url`: `http://host.docker.internal:8400`
   - `model_name`: `gemini-2.0-flash`

### 4. 모델 선택

채팅 화면에서 모델 드롭다운 → `물류 장비 부하율 관리` 선택

## Pipeline 구조

```python
class Pipeline:
    Valves:
        gemini_api_key, tool_server_url, model_name

    pipe(body) → str:
        1. _classify_intent(query)  # Gemini → JSON {intent, detail}
        2. _call_tool(intent, detail)  # HTTP GET → tool_server
        3. _generate_response(query, intent, tool_result)  # Gemini → 텍스트
```

## LangGraph/Dify와의 차이

| 항목 | LangGraph | Dify | Open WebUI |
|------|-----------|------|------------|
| 의도분류 | LangChain LLM | QC 노드 | Gemini 직접 호출 |
| 도구 호출 | @tool + FC | HTTP 노드 | requests.get |
| UI | 터미널 | Dify 웹 | Open WebUI 채팅 |
| 상태 관리 | StateGraph | 자동 | Pipeline 단순 |
| 코드량 | ~600줄 | ~0줄 | ~150줄 |
| 확장성 | 최고 | 중간 | 중간 |

## 테스트

```
질문: "과부하 장비 있어?"
질문: "L2 장비 상태"
질문: "최근 알림 보여줘"
질문: "안녕하세요"
```

## 의존성

Pipeline 내부:
- `google-generativeai` — Gemini API
- `requests` — HTTP 클라이언트
