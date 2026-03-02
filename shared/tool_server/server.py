"""FastAPI 서버 — 10개 SQL 도구를 REST API로 노출.

Dify, Open WebUI 등 외부 도구에서 HTTP로 호출.
LangGraph는 직접 SQLite 접근 (이 서버 불필요).
"""
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
import uvicorn

# shared.db 모듈 접근을 위한 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.db.connection import query

app = FastAPI(
    title="물류 장비 부하율 관리 API",
    description="물류 장비 상태, 부하율, 알림, Lot 정보를 조회하는 도구 API",
    version="1.0.0",
)


@app.get("/tools/equipment/list", summary="장비 목록 조회", tags=["Equipment"])
def equipment_list(
    equipment_type: Optional[str] = Query(None, description="장비 유형 (CONVEYOR/AGV/CRANE/SORTER/STACKER/SHUTTLE)"),
    line: Optional[str] = Query(None, description="라인 (L1/L2/L3)"),
    zone: Optional[str] = Query(None, description="구간 (TFT/CELL/MODULE/PACK)"),
):
    """장비 목록을 조회합니다. 유형, 라인, 구간으로 필터링 가능."""
    conditions, params = [], []
    if equipment_type:
        conditions.append("equipment_type = ?")
        params.append(equipment_type.upper())
    if line:
        conditions.append("line = ?")
        params.append(line.upper())
    if zone:
        conditions.append("zone = ?")
        params.append(zone.upper())
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    return query(f"SELECT * FROM equipment{where} ORDER BY equipment_id", tuple(params))


@app.get("/tools/equipment/status", summary="장비 상태 현황", tags=["Equipment"])
def equipment_status(
    equipment_type: Optional[str] = Query(None, description="장비 유형"),
    line: Optional[str] = Query(None, description="라인"),
):
    """상태별 장비 집계 + 목록."""
    conditions, params = [], []
    if equipment_type:
        conditions.append("equipment_type = ?")
        params.append(equipment_type.upper())
    if line:
        conditions.append("line = ?")
        params.append(line.upper())
    where = " WHERE " + " AND ".join(conditions) if conditions else ""

    summary = query(
        f"SELECT status, COUNT(*) as cnt FROM equipment{where} GROUP BY status ORDER BY cnt DESC",
        tuple(params),
    )
    detail = query(
        f"SELECT equipment_id, equipment_type, line, zone, status FROM equipment{where} ORDER BY status, equipment_id",
        tuple(params),
    )
    return {"summary": summary, "equipment": detail}


@app.get("/tools/equipment/load-rates", summary="부하율 조회", tags=["Equipment"])
def load_rates(
    equipment_type: Optional[str] = Query(None, description="장비 유형"),
    line: Optional[str] = Query(None, description="라인"),
    zone: Optional[str] = Query(None, description="구간"),
    hours: int = Query(1, description="최근 N시간", ge=1),
):
    """최근 N시간 부하율 데이터 조회."""
    conditions = [f"lr.recorded_at >= datetime('now', 'localtime', '-{int(hours)} hours')"]
    params = []
    if equipment_type:
        conditions.append("e.equipment_type = ?")
        params.append(equipment_type.upper())
    if line:
        conditions.append("e.line = ?")
        params.append(line.upper())
    if zone:
        conditions.append("e.zone = ?")
        params.append(zone.upper())
    where = " WHERE " + " AND ".join(conditions)
    return query(
        f"""SELECT e.equipment_id, e.equipment_type, e.line, e.zone, e.status,
                   lr.recorded_at, lr.load_rate_pct, lr.throughput, lr.queue_length
            FROM load_rate lr
            JOIN equipment e ON lr.equipment_id = e.equipment_id
            {where}
            ORDER BY lr.recorded_at DESC, e.equipment_id""",
        tuple(params),
    )


@app.get("/tools/equipment/overloaded", summary="과부하 장비 조회", tags=["Equipment"])
def overloaded_equipment(
    threshold_pct: Optional[float] = Query(None, description="임계값 (0 이면 장비 유형별 기본값 사용)"),
):
    """최근 1시간 내 과부하 장비 조회."""
    if threshold_pct is not None and threshold_pct > 0:
        return query(
            """SELECT e.equipment_id, e.equipment_type, e.line, e.zone, e.status,
                      lr.recorded_at, lr.load_rate_pct
               FROM load_rate lr
               JOIN equipment e ON lr.equipment_id = e.equipment_id
               WHERE lr.load_rate_pct >= ?
                 AND lr.recorded_at >= datetime('now', 'localtime', '-1 hours')
               ORDER BY lr.load_rate_pct DESC""",
            (threshold_pct,),
        )
    return query(
        """SELECT e.equipment_id, e.equipment_type, e.line, e.zone, e.status,
                  lr.recorded_at, lr.load_rate_pct, at.warning_pct, at.critical_pct
           FROM load_rate lr
           JOIN equipment e ON lr.equipment_id = e.equipment_id
           JOIN alert_threshold at ON e.equipment_type = at.equipment_type
           WHERE lr.load_rate_pct >= at.warning_pct
             AND lr.recorded_at >= datetime('now', 'localtime', '-1 hours')
           ORDER BY lr.load_rate_pct DESC""",
    )


@app.get("/tools/equipment/{equipment_id}/detail", summary="장비 상세", tags=["Equipment"])
def equipment_detail(equipment_id: str):
    """특정 장비 상세 정보 + 최근 부하율 24건 + 알림 10건."""
    equip = query("SELECT * FROM equipment WHERE equipment_id = ?", (equipment_id.upper(),))
    history = query(
        """SELECT recorded_at, load_rate_pct, throughput, queue_length
           FROM load_rate WHERE equipment_id = ?
           ORDER BY recorded_at DESC LIMIT 24""",
        (equipment_id.upper(),),
    )
    alerts = query(
        """SELECT alert_type, load_rate_pct, threshold_pct, triggered_at, message
           FROM alert_history WHERE equipment_id = ?
           ORDER BY triggered_at DESC LIMIT 10""",
        (equipment_id.upper(),),
    )
    return {"equipment": equip, "load_history": history, "recent_alerts": alerts}


@app.get("/tools/alerts/recent", summary="최근 알림 이력", tags=["Alerts"])
def recent_alerts(
    hours: int = Query(24, description="최근 N시간", ge=1),
    alert_type: Optional[str] = Query(None, description="알림 유형 (WARNING/CRITICAL)"),
):
    """최근 N시간 알림 이력 조회."""
    conditions = [f"triggered_at >= datetime('now', 'localtime', '-{int(hours)} hours')"]
    params = []
    if alert_type:
        conditions.append("alert_type = ?")
        params.append(alert_type.upper())
    where = " WHERE " + " AND ".join(conditions)
    return query(
        f"""SELECT ah.*, e.equipment_type, e.line, e.zone
            FROM alert_history ah
            JOIN equipment e ON ah.equipment_id = e.equipment_id
            {where}
            ORDER BY triggered_at DESC""",
        tuple(params),
    )


@app.get("/tools/zones/summary", summary="구간별 부하율 요약", tags=["Zones"])
def zone_summary(
    line: Optional[str] = Query(None, description="라인 (L1/L2/L3)"),
):
    """구간(zone)별 최근 1시간 평균/최대/최소 부하율."""
    conditions = ["lr.recorded_at >= datetime('now', 'localtime', '-1 hours')"]
    params = []
    if line:
        conditions.append("e.line = ?")
        params.append(line.upper())
    where = " WHERE " + " AND ".join(conditions)
    return query(
        f"""SELECT e.line, e.zone,
                   COUNT(DISTINCT e.equipment_id) as equipment_count,
                   ROUND(AVG(lr.load_rate_pct), 1) as avg_load,
                   ROUND(MAX(lr.load_rate_pct), 1) as max_load,
                   ROUND(MIN(lr.load_rate_pct), 1) as min_load
            FROM load_rate lr
            JOIN equipment e ON lr.equipment_id = e.equipment_id
            {where}
            GROUP BY e.line, e.zone
            ORDER BY e.line, e.zone""",
        tuple(params),
    )


@app.get("/tools/lots/on-equipment/{equipment_id}", summary="설비의 현재 Lot", tags=["Lots"])
def lots_on_equipment(equipment_id: str):
    """설비에 현재 물리적으로 위치한 Lot 조회."""
    return query(
        """SELECT l.lot_id, l.product_type, l.quantity, l.status,
                  l.current_equipment_id, l.created_at, l.updated_at
           FROM lot l
           WHERE l.current_equipment_id = ?
             AND l.status IN ('IN_TRANSIT', 'IN_PROCESS')
           ORDER BY l.updated_at DESC""",
        (equipment_id.upper(),),
    )


@app.get("/tools/lots/scheduled/{equipment_id}", summary="설비의 예정 Lot", tags=["Lots"])
def lots_scheduled(equipment_id: str):
    """설비에 예정(스케줄)된 Lot 조회."""
    return query(
        """SELECT ls.lot_id, l.product_type, l.quantity, l.status,
                  l.current_equipment_id,
                  ls.equipment_id AS scheduled_equipment_id,
                  ls.scheduled_start, ls.scheduled_end,
                  ls.actual_start, ls.actual_end
           FROM lot_schedule ls
           JOIN lot l ON ls.lot_id = l.lot_id
           WHERE ls.equipment_id = ?
             AND ls.actual_end IS NULL
           ORDER BY ls.scheduled_start""",
        (equipment_id.upper(),),
    )


@app.get("/tools/lots/{lot_id}/detail", summary="Lot 상세", tags=["Lots"])
def lot_detail(lot_id: str):
    """특정 Lot 상세 정보 + 스케줄 이력."""
    lot_info = query("SELECT * FROM lot WHERE lot_id = ?", (lot_id.upper(),))
    schedules = query(
        """SELECT ls.*, e.equipment_type, e.line, e.zone
           FROM lot_schedule ls
           JOIN equipment e ON ls.equipment_id = e.equipment_id
           WHERE ls.lot_id = ?
           ORDER BY ls.scheduled_start""",
        (lot_id.upper(),),
    )
    return {"lot": lot_info, "schedules": schedules}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8400)
