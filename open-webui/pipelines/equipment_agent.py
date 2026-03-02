"""Open WebUI Pipeline — 물류 장비 부하율 관리 에이전트.

Open WebUI의 Pipelines 서버에 등록하여 사용.
의도분류 → tool_server HTTP 호출 → 응답 생성 (Gemini).
"""
import json
import requests
from typing import Optional

import google.generativeai as genai


class Pipeline:
    """물류 장비 부하율 관리 파이프라인."""

    class Valves:
        """파이프라인 설정값 — Open WebUI 관리 화면에서 변경 가능."""
        gemini_api_key: str = ""
        tool_server_url: str = "http://localhost:8400"
        model_name: str = "gemini-2.0-flash"

    def __init__(self):
        self.name = "물류 장비 부하율 관리"
        self.valves = self.Valves()

    async def on_startup(self):
        """파이프라인 시작 시 Gemini 초기화."""
        if self.valves.gemini_api_key:
            genai.configure(api_key=self.valves.gemini_api_key)

    async def on_shutdown(self):
        pass

    async def on_valves_updated(self):
        """설정 변경 시 Gemini 재초기화."""
        if self.valves.gemini_api_key:
            genai.configure(api_key=self.valves.gemini_api_key)

    def _classify_intent(self, query: str) -> dict:
        """Gemini로 의도 분류."""
        model = genai.GenerativeModel(self.valves.model_name)

        prompt = f"""사용자의 질문을 분석하여 아래 6가지 의도 중 하나로 분류하세요.

의도 목록:
1. equipment_status — 장비 상태 조회
2. load_rate_query — 부하율 수치 조회
3. alert_check — 알림 이력 확인
4. overload_check — 과부하 장비 확인
5. lot_query — Lot(생산 단위) 조회
6. general_chat — 일반 대화

장비 유형: CONVEYOR, AGV, CRANE, SORTER, STACKER, SHUTTLE
라인: L1, L2, L3
구간: TFT, CELL, MODULE, PACK

반드시 JSON만 출력:
{{"intent": "의도명", "detail": {{"equipment_type": "", "line": "", "zone": "", "equipment_id": "", "lot_id": ""}}, "reasoning": "이유"}}

질문: {query}"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        if "```" in raw:
            raw = raw.split("```json")[-1].split("```")[0].strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"intent": "general_chat", "detail": {}, "reasoning": "파싱 실패"}

    def _call_tool(self, intent: str, detail: dict) -> Optional[str]:
        """의도에 따라 tool_server API 호출."""
        base = self.valves.tool_server_url
        params = {}

        # 공통 파라미터 추출
        eq_type = detail.get("equipment_type", "")
        line = detail.get("line", "")
        zone = detail.get("zone", "")
        eq_id = detail.get("equipment_id", "")
        lot_id = detail.get("lot_id", "")

        if eq_type:
            params["equipment_type"] = eq_type
        if line:
            params["line"] = line
        if zone:
            params["zone"] = zone

        intent_to_endpoint = {
            "equipment_status": "/tools/equipment/status",
            "load_rate_query": "/tools/equipment/load-rates",
            "alert_check": "/tools/alerts/recent",
            "overload_check": "/tools/equipment/overloaded",
            "lot_query": "/tools/zones/summary",
        }

        # 특정 장비 ID가 있으면 상세 조회
        if eq_id:
            url = f"{base}/tools/equipment/{eq_id}/detail"
            params = {}
        elif lot_id:
            url = f"{base}/tools/lots/{lot_id}/detail"
            params = {}
        elif intent in intent_to_endpoint:
            url = f"{base}{intent_to_endpoint[intent]}"
        else:
            return None

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return json.dumps(resp.json(), ensure_ascii=False, indent=2)
        except Exception as e:
            return f"API 호출 실패: {e}"

    def _generate_response(self, query: str, intent: str, tool_result: Optional[str]) -> str:
        """Gemini로 최종 응답 생성."""
        model = genai.GenerativeModel(self.valves.model_name)

        if intent == "general_chat" or tool_result is None:
            prompt = f"""당신은 친절한 물류 장비 관리 어시스턴트입니다.
물류와 무관한 질문에는 간단히 답하고, 물류 관련 질문을 유도하세요.

질문: {query}"""
        else:
            prompt = f"""당신은 물류 장비 관리 어시스턴트입니다.
API 조회 결과를 바탕으로 사용자에게 이해하기 쉬운 한국어 응답을 생성하세요.

규칙:
- 표 형식 사용 (마크다운)
- 수치는 소수점 1자리
- 이상 수치 강조

사용자 질문: {query}

API 조회 결과:
{tool_result[:5000]}

위 데이터를 바탕으로 질문에 답해주세요."""

        response = model.generate_content(prompt)
        return response.text

    def pipe(self, body: dict) -> str:
        """메인 파이프라인 — Open WebUI에서 호출.

        Args:
            body: {"messages": [{"role": "user", "content": "..."}]}

        Returns:
            최종 응답 문자열
        """
        # 마지막 사용자 메시지 추출
        messages = body.get("messages", [])
        if not messages:
            return "질문을 입력해주세요."

        query = messages[-1].get("content", "")
        if not query:
            return "질문을 입력해주세요."

        # 1. 의도 분류
        classification = self._classify_intent(query)
        intent = classification.get("intent", "general_chat")

        # 2. 도구 호출
        tool_result = self._call_tool(intent, classification.get("detail", {}))

        # 3. 응답 생성
        response = self._generate_response(query, intent, tool_result)

        return response
