# Dify 구현 — 물류 장비 부하율 관리

비주얼 워크플로우 방식으로 동일한 유스케이스를 구현합니다.

## 아키텍처

```
사용자 질문
    ↓
[Question Classifier] ← Gemini 2.0 Flash
    ↓ (6가지 의도)
[HTTP Request] → tool_server (:8400)
    ↓
[LLM] ← Gemini 2.0 Flash (응답 생성)
    ↓
최종 응답
```

## 사전 준비

### 1. Tool Server 실행

```bash
cd ai-workflow-compare
python -m shared.db.seed          # DB 생성
python -m shared.tool_server.server  # :8400 실행
```

### 2. Dify 설치 (셀프호스트)

```bash
git clone https://github.com/langgenius/dify.git
cd dify/docker
cp .env.example .env
docker compose up -d
```

브라우저: `http://localhost` → 계정 생성

### 3. Gemini 플러그인 설정

1. Dify 설정 → 모델 공급자 → Google 추가
2. Gemini API Key 입력
3. `gemini-2.0-flash` 모델 활성화

### 4. Custom Tool 등록

1. Studio → Custom Tools → "Create Custom Tool"
2. `tools/openapi.yaml` 내용 붙여넣기
3. 서버 URL: `http://host.docker.internal:8400` (Docker 내부에서 호스트 접근)

### 5. 워크플로우 Import

1. Studio → "Create from DSL"
2. `workflows/equipment-agent.yml` 업로드
3. 모델 설정 확인 (Gemini 2.0 Flash)
4. Custom Tool 연결 확인

## 워크플로우 구조

```
Start
  └→ Question Classifier (의도분류, 6개 클래스)
       ├→ 장비 상태 → HTTP GET /tools/equipment/status → LLM → End
       ├→ 부하율   → HTTP GET /tools/equipment/load-rates → LLM → End
       ├→ 알림     → HTTP GET /tools/alerts/recent → LLM → End
       ├→ 과부하   → HTTP GET /tools/equipment/overloaded → LLM → End
       ├→ Lot      → HTTP GET /tools/zones/summary → LLM → End
       └→ 일반대화 → LLM (직접) → End
```

## LangGraph와의 차이

| 항목 | LangGraph | Dify |
|------|-----------|------|
| 의도분류 | Python 코드 (IntentAgent) | Question Classifier 노드 |
| 도구 호출 | @tool + Function Calling | HTTP Request 노드 |
| 도구 선택 | LLM이 자율 선택 (10개 중) | 워크플로우가 고정 라우팅 |
| 멀티턴 | conversation_history 직접 관리 | Dify 내장 대화 관리 |
| 모호성 해소 | LLM이 2개 Tool 동시 호출 | 워크플로우 분기로 처리 |
| 디버깅 | FM I/O 트레이스 파일 | Dify 내장 실행 로그 |
| 코드량 | ~600줄 Python | ~0줄 (YAML 설정) |

## 테스트

워크플로우 배포 후:

```
질문: "과부하 장비 있어?"
기대: 과부하 장비 목록 (장비ID, 부하율, 상태)

질문: "L1 장비 상태 어때?"
기대: L1 라인 장비 상태별 집계

질문: "안녕하세요"
기대: 일반 인사 + 물류 질문 유도
```
