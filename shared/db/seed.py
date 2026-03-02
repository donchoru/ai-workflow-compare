"""샘플 데이터 생성 — 장비 30대, 부하율 720건, 알림 이력, Lot 40건."""
import random
from datetime import datetime, timedelta
from pathlib import Path
from shared.db.connection import get_connection

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

EQUIPMENT_TYPES = ["CONVEYOR", "AGV", "CRANE", "SORTER", "STACKER", "SHUTTLE"]
TYPE_PREFIX = {
    "CONVEYOR": "CVR", "AGV": "AGV", "CRANE": "CRN",
    "SORTER": "SRT", "STACKER": "STK", "SHUTTLE": "SHT",
}
LINES = ["L1", "L2", "L3"]
ZONES = ["TFT", "CELL", "MODULE", "PACK"]
STATUSES = ["RUNNING", "RUNNING", "RUNNING", "IDLE", "MAINTENANCE", "ERROR"]

THRESHOLDS = {
    "CONVEYOR": (80.0, 95.0),
    "AGV":      (75.0, 90.0),
    "CRANE":    (70.0, 85.0),
    "SORTER":   (80.0, 95.0),
    "STACKER":  (75.0, 90.0),
    "SHUTTLE":  (78.0, 92.0),
}


def seed():
    conn = get_connection()
    try:
        # 스키마 생성
        conn.executescript(SCHEMA_PATH.read_text())

        # 기존 데이터 삭제 (FK 순서)
        for table in ["lot_schedule", "lot", "alert_history", "load_rate", "alert_threshold", "equipment"]:
            conn.execute(f"DELETE FROM {table}")

        random.seed(42)
        now = datetime.now()

        # 장비 30대 생성
        equipments = []
        seq = {}
        for _ in range(30):
            etype = random.choice(EQUIPMENT_TYPES)
            line = random.choice(LINES)
            zone = random.choice(ZONES)
            key = (etype, line, zone)
            seq[key] = seq.get(key, 0) + 1
            eid = f"{TYPE_PREFIX[etype]}-{line}-{zone}-{seq[key]:02d}"
            status = random.choice(STATUSES)
            installed = (now - timedelta(days=random.randint(30, 730))).strftime("%Y-%m-%d")
            equipments.append((eid, etype, line, zone, status, installed, f"{etype} {line}-{zone}"))

        conn.executemany(
            "INSERT INTO equipment VALUES (?,?,?,?,?,?,?)", equipments
        )

        # 임계값 설정
        for etype, (warn, crit) in THRESHOLDS.items():
            conn.execute(
                "INSERT INTO alert_threshold VALUES (?,?,?)", (etype, warn, crit)
            )

        # 부하율 720건 (장비당 24건 = 최근 4시간, 10분 간격)
        load_rows = []
        alert_rows = []
        for eid, etype, line, zone, status, _, _ in equipments:
            warn_pct, crit_pct = THRESHOLDS[etype]

            if status == "ERROR":
                base, spread = 92.0, 8.0
            elif status == "MAINTENANCE":
                base, spread = 10.0, 5.0
            elif status == "IDLE":
                base, spread = 5.0, 3.0
            else:
                base, spread = 55.0, 30.0

            for i in range(24):
                ts = (now - timedelta(minutes=10 * (23 - i))).strftime("%Y-%m-%d %H:%M:%S")
                rate = max(0, min(100, base + random.uniform(-spread, spread)))
                throughput = int(rate * random.uniform(0.8, 1.2))
                queue = max(0, int((rate - 60) * random.uniform(0, 0.5))) if rate > 60 else 0

                load_rows.append((eid, ts, round(rate, 1), throughput, queue))

                if rate >= crit_pct:
                    alert_rows.append((
                        eid, "CRITICAL", round(rate, 1), crit_pct, ts, None,
                        f"{eid} 부하율 {rate:.1f}% — 임계값 {crit_pct}% 초과"
                    ))
                elif rate >= warn_pct:
                    alert_rows.append((
                        eid, "WARNING", round(rate, 1), warn_pct, ts, None,
                        f"{eid} 부하율 {rate:.1f}% — 경고 {warn_pct}% 초과"
                    ))

        conn.executemany(
            "INSERT INTO load_rate (equipment_id, recorded_at, load_rate_pct, throughput, queue_length) VALUES (?,?,?,?,?)",
            load_rows,
        )
        conn.executemany(
            "INSERT INTO alert_history (equipment_id, alert_type, load_rate_pct, threshold_pct, triggered_at, resolved_at, message) VALUES (?,?,?,?,?,?,?)",
            alert_rows,
        )

        # ── Lot 40건 + 스케줄 생성 ──────────────────────────
        PRODUCT_TYPES = ["OLED_A", "OLED_B", "LCD_C"]
        LOT_STATUSES = (
            ["SCHEDULED"] * 10 + ["IN_TRANSIT"] * 8
            + ["IN_PROCESS"] * 15 + ["COMPLETED"] * 7
        )
        random.shuffle(LOT_STATUSES)

        equipment_ids = [e[0] for e in equipments]
        running_ids = [e[0] for e in equipments if e[4] == "RUNNING"]
        agv_ids = [e[0] for e in equipments if e[1] == "AGV"]

        lot_rows = []
        schedule_rows = []

        for i in range(40):
            lot_id = f"LOT-{i + 1:03d}"
            product = random.choice(PRODUCT_TYPES)
            qty = random.randint(100, 500)
            status = LOT_STATUSES[i]
            created = (now - timedelta(hours=random.randint(1, 48))).strftime("%Y-%m-%d %H:%M:%S")
            updated = (now - timedelta(minutes=random.randint(0, 120))).strftime("%Y-%m-%d %H:%M:%S")

            if status == "SCHEDULED":
                current_equip = None
            elif status == "IN_TRANSIT":
                current_equip = random.choice(agv_ids) if agv_ids else random.choice(equipment_ids)
            elif status == "IN_PROCESS":
                current_equip = random.choice(running_ids) if running_ids else random.choice(equipment_ids)
            else:
                current_equip = random.choice(equipment_ids)

            lot_rows.append((lot_id, product, qty, status, current_equip, created, updated))

            num_schedules = random.randint(1, 2)
            for j in range(num_schedules):
                sched_equip = random.choice(running_ids) if running_ids else random.choice(equipment_ids)
                sched_start = (now + timedelta(hours=random.randint(-2, 8))).strftime("%Y-%m-%d %H:%M:%S")
                sched_end = (now + timedelta(hours=random.randint(9, 16))).strftime("%Y-%m-%d %H:%M:%S")

                if status == "COMPLETED":
                    actual_start = (now - timedelta(hours=random.randint(3, 10))).strftime("%Y-%m-%d %H:%M:%S")
                    actual_end = (now - timedelta(hours=random.randint(0, 2))).strftime("%Y-%m-%d %H:%M:%S")
                elif status == "IN_PROCESS" and j == 0:
                    sched_equip = current_equip
                    actual_start = (now - timedelta(minutes=random.randint(10, 60))).strftime("%Y-%m-%d %H:%M:%S")
                    actual_end = None
                else:
                    actual_start = None
                    actual_end = None

                schedule_rows.append((lot_id, sched_equip, sched_start, sched_end, actual_start, actual_end))

        # ── 의미 모호성 시나리오 강제 삽입 ──────────────────
        if len(lot_rows) >= 5:
            old = lot_rows[4]
            target_agv = agv_ids[0] if agv_ids else equipment_ids[0]
            target_cvr = [e[0] for e in equipments if e[1] == "CONVEYOR"]
            target_cvr = target_cvr[0] if target_cvr else equipment_ids[1]
            lot_rows[4] = (old[0], old[1], old[2], "IN_TRANSIT", target_agv, old[5], old[6])
            sched_start = (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            sched_end = (now + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
            schedule_rows.append((old[0], target_cvr, sched_start, sched_end, None, None))

        conn.executemany(
            "INSERT INTO lot VALUES (?,?,?,?,?,?,?)", lot_rows,
        )
        conn.executemany(
            "INSERT INTO lot_schedule (lot_id, equipment_id, scheduled_start, scheduled_end, actual_start, actual_end) VALUES (?,?,?,?,?,?)",
            schedule_rows,
        )

        conn.commit()

        eq_count = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
        lr_count = conn.execute("SELECT COUNT(*) FROM load_rate").fetchone()[0]
        al_count = conn.execute("SELECT COUNT(*) FROM alert_history").fetchone()[0]
        lot_count = conn.execute("SELECT COUNT(*) FROM lot").fetchone()[0]
        sched_count = conn.execute("SELECT COUNT(*) FROM lot_schedule").fetchone()[0]
        print(f"Seed 완료: 장비 {eq_count}대, 부하율 {lr_count}건, 알림 {al_count}건, Lot {lot_count}건, 스케줄 {sched_count}건")

    finally:
        conn.close()


if __name__ == "__main__":
    seed()
