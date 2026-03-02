#!/bin/bash
# ─── AI Workflow Compare — 원클릭 데모 ───────────────────
# 사용법: ./run_demo.sh
#
# 수행 내용:
#   1. 가상환경 생성 + 의존성 설치
#   2. DB 시드 데이터 생성
#   3. Tool Server 기동 (:8400)
#   4. LangGraph로 데모 질문 3개 실행
#   5. Tool Server 종료
# ──────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

echo "=================================="
echo "  AI Workflow Compare — Demo"
echo "=================================="
echo ""

# ── 1. Gemini API Key 확인 ──
if [ -z "$GEMINI_API_KEY" ]; then
    # macOS Keychain에서 시도
    if command -v security &>/dev/null; then
        GEMINI_API_KEY=$(security find-generic-password -s GEMINI_API_KEY -w 2>/dev/null || true)
    fi
    if [ -z "$GEMINI_API_KEY" ]; then
        echo "GEMINI_API_KEY가 설정되지 않았습니다."
        echo ""
        echo "  export GEMINI_API_KEY='your-key'"
        echo "  ./run_demo.sh"
        echo ""
        exit 1
    fi
    export GEMINI_API_KEY
    echo "[OK] Gemini API Key (Keychain)"
fi

# ── 2. 가상환경 + 의존성 ──
if [ ! -d ".venv" ]; then
    echo ""
    echo "[1/4] 가상환경 생성..."
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "[1/4] 의존성 설치..."
pip install -q -r shared/tool_server/requirements.txt -r langgraph/requirements.txt 2>&1 | tail -1

# ── 3. DB 시드 ──
echo "[2/4] DB 시드 데이터 생성..."
python -m shared.db.seed

# ── 4. Tool Server 기동 ──
echo "[3/4] Tool Server 기동 (:8400)..."
python -m shared.tool_server.server &
TOOL_PID=$!
sleep 2

# 헬스체크
if curl -s localhost:8400/tools/equipment/list > /dev/null 2>&1; then
    echo "       Tool Server 정상 동작"
else
    echo "       Tool Server 기동 실패!"
    kill $TOOL_PID 2>/dev/null
    exit 1
fi

# ── 5. LangGraph 데모 ──
echo "[4/4] LangGraph 데모 실행..."
echo ""
echo "────────────────────────────────────"
echo "  질문 1: 과부하 장비 있어?"
echo "────────────────────────────────────"
cd langgraph
printf "과부하 장비 있어?\nquit\n" | python main.py 2>/dev/null | grep -A 100 "^\[의도" | head -30
echo ""

echo "────────────────────────────────────"
echo "  질문 2: L1 컨베이어 상태 어때?"
echo "────────────────────────────────────"
printf "L1 컨베이어 상태 어때?\nquit\n" | python main.py 2>/dev/null | grep -A 100 "^\[의도" | head -20
echo ""

echo "────────────────────────────────────"
echo "  질문 3: 안녕하세요"
echo "────────────────────────────────────"
printf "안녕하세요\nquit\n" | python main.py 2>/dev/null | grep -A 100 "^\[의도" | head -10
cd ..

# ── 6. 정리 ──
echo ""
echo "=================================="
echo "  데모 완료!"
echo "=================================="
echo ""
echo "  Tool Server: http://localhost:8400/docs (Swagger UI)"
echo "  LangGraph:   cd langgraph && python main.py"
echo ""
echo "  Tool Server 종료: kill $TOOL_PID"
echo ""

# Tool Server는 데모 후 계속 실행 (Swagger 확인용)
# 종료하려면: kill $TOOL_PID
