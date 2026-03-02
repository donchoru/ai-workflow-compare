"""대화형 실행 진입점 — LangGraph 멀티 에이전트 물류 장비 부하율 관리."""
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 path에 추가 (shared 모듈 접근)
# append로 추가하여 pip langgraph 패키지보다 뒤에 위치
sys.path.append(str(Path(__file__).parent.parent))

from config import TRACES_DIR
from graph.workflow import build_graph


def save_trace(user_input: str, intent: str, trace_lines: list[str]) -> Path:
    TRACES_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = TRACES_DIR / f"trace_{ts}.md"

    header = [
        "# Agent Trace Log",
        f"- **시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **사용자 입력**: {user_input}",
        f"- **최종 의도**: {intent}",
        "",
        "---",
    ]

    path.write_text("\n".join(header + trace_lines), encoding="utf-8")
    return path


def main():
    print("=" * 60)
    print("  물류 장비 부하율 관리 — LangGraph 멀티 에이전트")
    print("  종료: 'quit' 또는 'q' 입력")
    print("=" * 60)

    app = build_graph()
    conversation_history = []

    while True:
        try:
            user_input = input("\n질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "q", "exit"):
            print("종료합니다.")
            break
        if user_input.lower() == "clear":
            conversation_history.clear()
            print("대화 이력 초기화.")
            continue

        print(f"\n처리 중...")

        try:
            result = app.invoke({
                "messages": [],
                "intent": "",
                "intent_detail": "",
                "trace_log": [],
                "user_input": user_input,
                "final_answer": "",
                "conversation_history": list(conversation_history),
            })

            answer = result.get("final_answer", "응답을 생성하지 못했습니다.")
            intent = result.get("intent", "unknown")
            trace_log = result.get("trace_log", [])

            print(f"\n[의도: {intent}]")
            print("-" * 40)
            print(answer)
            print("-" * 40)

            conversation_history.append({
                "user": user_input,
                "answer": answer[:300],
                "intent": intent,
            })
            if len(conversation_history) > 10:
                conversation_history = conversation_history[-10:]

            trace_path = save_trace(user_input, intent, trace_log)
            print(f"Trace 저장: {trace_path.name}")

        except Exception as e:
            print(f"\n오류: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
