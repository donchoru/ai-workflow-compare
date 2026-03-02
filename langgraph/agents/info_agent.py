"""정보조회 Agent — 의도 기반으로 Tool 호출 후 응답 생성."""
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.state import AgentState, dump_state
from agents.prompts import INFO_SYSTEM_PROMPT
from agents.message_trimmer import prepare_messages
from tools.sql_tools import ALL_TOOLS
from config import GEMINI_API_KEY, GEMINI_MODEL


llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GEMINI_API_KEY,
    temperature=0,
).bind_tools(ALL_TOOLS)


def info_node(state: AgentState) -> dict:
    intent = state["intent"]
    intent_detail = state["intent_detail"]
    user_input = state["user_input"]
    messages = state.get("messages", [])

    reentry = bool(messages)
    step_label = "InfoAgent 재진입 (Tool 결과 수신)" if reentry else "InfoAgent (정보조회)"

    trace = [
        f"\n---\n## Step 2: {step_label}",
        f"### State BEFORE",
    ]
    trace += dump_state(state)

    if reentry:
        trimmed = prepare_messages(list(messages))
        llm_messages = [SystemMessage(content=INFO_SYSTEM_PROMPT)] + trimmed
        trim_note = (f"원본 {len(messages)}건 → 트리밍 {len(trimmed)}건"
                     if len(trimmed) < len(messages)
                     else f"메시지 히스토리 {len(messages)}건 포함")
        trace.append(f"### FM 입력 (재진입): {trim_note}")
    else:
        history = state.get("conversation_history", [])
        history_ctx = ""
        if history:
            ctx_lines = ["[이전 대화 이력]"]
            for h in history[-3:]:
                ctx_lines.append(f"- Q: {h['user']} → intent: {h.get('intent', '')}, 응답: {h.get('answer', '')[:200]}")
            history_ctx = "\n".join(ctx_lines) + "\n\n"

        prompt = (
            f"{history_ctx}"
            f"사용자 질문: {user_input}\n"
            f"의도: {intent}\n"
            f"상세: {intent_detail}\n\n"
            f"위 의도에 맞는 도구를 호출하여 정보를 조회하세요."
        )
        llm_messages = [
            SystemMessage(content=INFO_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        trace.append(f"### FM 입력 (첫 호출): `{prompt[:200]}`")

    try:
        response = llm.invoke(llm_messages)
    except Exception as e:
        error_msg = f"LLM 호출 실패: {type(e).__name__}: {e}"
        trace.append(f"### ERROR: `{error_msg}`")
        fallback = AIMessage(content="죄송합니다. 정보 조회 중 오류가 발생했습니다.")
        return {
            "messages": [fallback],
            "trace_log": state.get("trace_log", []) + trace,
        }

    if response.tool_calls:
        trace.append(f"### FM 출력 → Tool 호출: {[tc['name'] for tc in response.tool_calls]}")
    else:
        trace.append(f"### FM 출력 → 텍스트 응답: `{response.content[:200]}`")

    updated = dict(state)
    updated["messages"] = list(state.get("messages", [])) + [response]
    trace += [f"### State AFTER"]
    trace += dump_state(updated)

    return {
        "messages": [response],
        "trace_log": state.get("trace_log", []) + trace,
    }


def respond_node(state: AgentState) -> dict:
    intent = state["intent"]
    messages = state["messages"]
    user_input = state["user_input"]

    trace = [f"\n---\n## Step 3: ResponseAgent (응답생성)"]

    if intent == "general_chat":
        chat_system = "당신은 친절한 물류 장비 관리 시스템 어시스턴트입니다. 물류와 무관한 질문에는 간단히 답하고, 물류 관련 질문을 유도하세요."
        simple_llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0.7,
        )
        response = simple_llm.invoke([
            SystemMessage(content=chat_system),
            HumanMessage(content=user_input),
        ])
        answer = response.content
    else:
        last_ai = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                last_ai = msg
                break
        answer = last_ai.content if (last_ai and last_ai.content) else "조회 결과를 처리하지 못했습니다."

    trace.append(f"### 최종 응답: `{answer[:200]}`")

    return {
        "final_answer": answer,
        "trace_log": state.get("trace_log", []) + trace,
    }
