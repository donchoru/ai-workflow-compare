# 실행 결과 예시

동일한 3가지 질문을 각 구현에 보내고, 응답 방식의 차이를 비교합니다.

---

## 질문 1: "과부하 장비 있어?"

### LangGraph 응답

```
[의도: overload_check]

과부하 장비 목록입니다.

| 장비 ID          | 유형      | 라인 | 구간   | 상태  | 부하율(%) |
|-----------------|---------|------|--------|-------|----------|
| CVR-L1-CELL-01  | CONVEYOR | L1   | CELL   | ERROR | 99.8     |
| SHT-L3-CELL-01  | SHUTTLE  | L3   | CELL   | ERROR | 99.3     |
| SHT-L3-MODULE-01| SHUTTLE  | L3   | MODULE | ERROR | 99.2     |
| AGV-L1-CELL-01  | AGV      | L1   | CELL   | ERROR | 99.1     |
| ...             | ...      | ...  | ...    | ...   | ...      |
```

**처리 흐름:**
```
IntentAgent → {"intent": "overload_check"} → InfoAgent → get_overloaded_equipment() → SQL 실행 → 응답 생성
```

### Dify 응답 (예상)

동일한 결과를 반환하지만, 경로가 다릅니다:
```
Question Classifier → "과부하 확인" → HTTP GET /tools/equipment/overloaded → LLM 응답 생성
```

- 도구 선택이 워크플로우에 고정 (Question Classifier가 분기)
- LangGraph는 LLM이 10개 도구 중 자율 선택

### Open WebUI Pipeline 응답 (예상)

```
_classify_intent() → {"intent": "overload_check"}
_call_tool() → GET /tools/equipment/overloaded
_generate_response() → 마크다운 표
```

- 코드에서 intent→endpoint 매핑이 하드코딩
- LangGraph와 달리 Function Calling 없이 직접 HTTP 호출

---

## 질문 2: "L1 컨베이어 상태 어때?"

### LangGraph 응답

```
[의도: equipment_status]

L1 라인 컨베이어의 상태는 다음과 같습니다.

| 상태    | 대수 |
|---------|------|
| RUNNING | 3    |
| ERROR   | 1    |

| 장비 ID        | 유형      | 라인 | 상태    | 구간   |
|---------------|---------|------|---------|--------|
| CVR-L1-CELL-01 | CONVEYOR | L1   | ERROR   | CELL   |
| CVR-L1-PACK-01 | CONVEYOR | L1   | RUNNING | PACK   |
| CVR-L1-TFT-01  | CONVEYOR | L1   | RUNNING | TFT    |
| CVR-L1-TFT-02  | CONVEYOR | L1   | RUNNING | TFT    |
```

**핵심 차이:**
- LangGraph: IntentAgent가 `equipment_type=CONVEYOR, line=L1`을 JSON으로 추출 → InfoAgent가 `get_equipment_status(equipment_type="CONVEYOR", line="L1")` 호출
- Dify: Question Classifier가 "장비 상태" 분기 → HTTP Request에 파라미터 전달이 제한적
- Open WebUI: `_classify_intent()`에서 detail 추출 → `_call_tool()`에서 query params로 전달

---

## 질문 3: "안녕하세요"

### LangGraph 응답

```
[의도: general_chat]

안녕하세요! 무엇을 도와드릴까요? 혹시 물류 장비 관리에 대해 궁금한 점이 있으신가요?
```

**처리 흐름:**
```
IntentAgent → {"intent": "general_chat"} → ResponseAgent (도구 호출 없이 직접 LLM)
```

- Tool 호출을 건너뛰고 바로 응답 생성
- 세 구현 모두 동일한 처리 (의도가 general_chat이면 LLM 직접 응답)

---

## 핵심 차이 요약

| 비교 포인트 | LangGraph | Dify | Open WebUI |
|------------|-----------|------|------------|
| **파라미터 추출** | LLM이 JSON으로 구조화 | 제한적 (변수 노드 필요) | LLM이 JSON으로 구조화 |
| **도구 선택** | LLM 자율 (10개 중) | 워크플로우 고정 분기 | 코드 매핑 (dict) |
| **동시 도구 호출** | 가능 (Lot 모호성 시) | 불가 (직렬 분기) | 수동 구현 필요 |
| **에러 처리** | try/except + fallback | 노드별 에러 핸들러 | try/except |
| **응답 품질** | 최고 (전체 컨텍스트) | 좋음 (단일 API 결과) | 좋음 (단일 API 결과) |
