# 상세 비교 분석 — LangGraph vs Dify vs Open WebUI

## 1. 개발 경험 (Developer Experience)

### LangGraph — 코드 퍼스트

**장점:**
- 완전한 코드 제어 — 모든 동작을 정확히 정의 가능
- IDE 지원 (자동완성, 타입 체크, 디버깅)
- 테스트 작성 용이 (pytest)
- Git 기반 버전 관리 자연스러움
- LangSmith 연동으로 프로덕션 모니터링

**단점:**
- 높은 진입장벽 (LangChain 생태계 이해 필요)
- 보일러플레이트 코드 많음 (StateGraph, TypedDict, 라우팅 함수 등)
- 디버깅 시 State 추적이 복잡

**적합한 경우:**
- 복잡한 멀티 에이전트 워크플로우
- 프로덕션 수준의 안정성 필요
- 세밀한 에러 핸들링, 재시도 로직 필요
- 기존 Python 코드베이스와 통합

### Dify — 비주얼 캔버스

**장점:**
- 노코드/로우코드 — 비개발자도 워크플로우 구성 가능
- 즉시 배포 — 워크플로우 저장 시 API 자동 생성
- 내장 모니터링, 로깅, 비용 추적
- 프롬프트 엔지니어링 UI 내장

**단점:**
- 복잡한 로직 표현 제한 (조건 분기는 가능하나 루프 제약)
- 도구 선택 유연성 부족 (워크플로우에서 미리 정의)
- 커스텀 로직 삽입 어려움 (Code 노드로 가능하지만 제한적)
- YAML DSL이 플랫폼 종속적

**적합한 경우:**
- 빠른 프로토타이핑
- 비개발자가 워크플로우 관리하는 팀
- 단순한 LLM 파이프라인 (입력 → 처리 → 출력)
- 멀티 모델 A/B 테스트

### Open WebUI — 채팅 UI + Pipeline

**장점:**
- 즉시 사용 가능한 ChatGPT 스타일 UI
- Pipeline 코드가 간결 (~150줄)
- Docker 한 줄로 배포
- 다양한 모델 지원 (Ollama, OpenAI, Gemini 등)
- Valves로 런타임 설정 변경 가능

**단점:**
- Pipeline 구조가 단순 (복잡한 워크플로우는 코드로 직접 구현)
- 에이전트 패턴(루프, 상태 관리)이 기본 제공되지 않음
- 디버깅 도구 제한적

**적합한 경우:**
- 내부 도구/데모 (ChatGPT 대체)
- 기존 LLM을 빠르게 채팅 UI로 노출
- 비교적 단순한 파이프라인
- Ollama + 로컬 모델 활용

---

## 2. 유연성

| 기능 | LangGraph | Dify | Open WebUI |
|------|-----------|------|------------|
| 루프 (재시도/반복) | StateGraph 루프 | 제한적 (이터레이션 노드) | 코드로 직접 |
| 도구 동적 선택 | LLM Function Calling | 워크플로우 고정 | 코드로 직접 |
| 상태 관리 | TypedDict (완전 제어) | 변수 노드 | 없음 (직접 구현) |
| 에러 핸들링 | try/except + fallback | 에러 핸들러 노드 | try/except |
| 멀티 에이전트 | 내장 지원 | 제한적 | 미지원 |
| 스트리밍 | 내장 | 내장 | Pipeline에서 가능 |

### 핵심 차이: 도구 선택

**LangGraph**: LLM이 10개 도구 중 자율 선택 → 모호한 질문에 2개 동시 호출 가능
```
"설비 Lot 알려줘" → LLM이 get_lots_on_equipment + get_lots_scheduled_for_equipment 동시 호출
```

**Dify**: 워크플로우 분기에서 미리 결정 → 의도별 1개 API 고정 호출
```
"설비 Lot 알려줘" → lot_query 분기 → /tools/zones/summary (고정)
```

**Open WebUI**: 코드에서 의도→엔드포인트 매핑 → 확장 가능하지만 수동
```
"설비 Lot 알려줘" → intent_to_endpoint["lot_query"] → /tools/zones/summary
```

---

## 3. 배포

| 항목 | LangGraph | Dify | Open WebUI |
|------|-----------|------|------------|
| 배포 방식 | Python 스크립트 / LangServe | Docker (셀프호스트) / Cloud | Docker |
| 최소 리소스 | Python 환경만 | 4GB+ RAM (PostgreSQL, Redis 등) | 2GB+ RAM |
| 스케일링 | 직접 구현 | 내장 (워커 수 설정) | 수평 확장 가능 |
| API 노출 | FastAPI/LangServe 추가 필요 | 자동 생성 | Pipeline API |
| 인증 | 직접 구현 | 내장 (API Key, OAuth) | 내장 (로컬 계정) |

---

## 4. 유지보수

| 항목 | LangGraph | Dify | Open WebUI |
|------|-----------|------|------------|
| 코드 리뷰 | Git PR — 자연스러움 | DSL YAML 비교 — 어려움 | Git PR — 자연스러움 |
| 버전 관리 | Git | Dify 내장 버전 | Git |
| 프롬프트 변경 | 코드 수정 + 배포 | UI에서 즉시 수정 | 코드 수정 + 재시작 |
| 모델 변경 | config.py 수정 | UI에서 드롭다운 | Valves에서 변경 |
| 모니터링 | LangSmith 또는 커스텀 | 내장 대시보드 | 로그 파일 |

---

## 5. 비용

| 항목 | LangGraph | Dify | Open WebUI |
|------|-----------|------|------------|
| 라이선스 | 오픈소스 (MIT) | Community (오픈소스) / Cloud ($) | 오픈소스 (MIT) |
| LLM 비용 | Gemini API 직접 | Gemini API 직접 | Gemini API 직접 |
| 인프라 | Python 서버만 | Docker (DB, Redis, 앱 등) | Docker |
| 추가 비용 | LangSmith (선택) | Dify Cloud 플랜 (선택) | 없음 |

---

## 6. 추천 시나리오

### LangGraph를 선택할 때
- 복잡한 에이전트 로직 (루프, 조건부 도구 선택, 멀티 에이전트)
- 프로덕션 수준의 안정성 + 테스트 필요
- Python 개발 팀
- 기존 코드베이스와 깊은 통합

### Dify를 선택할 때
- 빠른 프로토타이핑 → 즉시 API 배포
- 비개발자가 프롬프트/워크플로우 관리
- 단순한 파이프라인 (입력 → 처리 → 출력)
- 멀티 모델 A/B 테스트

### Open WebUI를 선택할 때
- 내부 도구/데모용 채팅 인터페이스
- Ollama + 로컬 모델 활용
- ChatGPT 대체 (프라이버시 중요)
- 간단한 Pipeline으로 충분한 경우

---

## 7. 결론

> **"복잡한 로직은 LangGraph, 빠른 배포는 Dify, 채팅 UI는 Open WebUI"**

세 도구는 경쟁이 아니라 보완 관계입니다:
- **LangGraph**: 백엔드 에이전트 로직 (뇌)
- **Dify**: 워크플로우 오케스트레이션 + API 배포 (몸)
- **Open WebUI**: 사용자 인터페이스 (얼굴)

실무에서는 LangGraph로 핵심 에이전트를 개발하고, Dify나 Open WebUI로 UI를 씌우는 조합도 가능합니다.
