CREATE TABLE IF NOT EXISTS equipment (
    equipment_id   TEXT PRIMARY KEY,
    equipment_type TEXT NOT NULL,  -- CONVEYOR, AGV, CRANE, SORTER, STACKER, SHUTTLE
    line           TEXT NOT NULL,  -- L1, L2, L3
    zone           TEXT NOT NULL,  -- TFT, CELL, MODULE, PACK
    status         TEXT NOT NULL DEFAULT 'RUNNING',  -- RUNNING, IDLE, MAINTENANCE, ERROR
    installed_date TEXT NOT NULL,
    description    TEXT
);

CREATE TABLE IF NOT EXISTS load_rate (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id  TEXT NOT NULL REFERENCES equipment(equipment_id),
    recorded_at   TEXT NOT NULL,
    load_rate_pct REAL NOT NULL,
    throughput    INTEGER NOT NULL DEFAULT 0,
    queue_length  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alert_threshold (
    equipment_type TEXT PRIMARY KEY,
    warning_pct    REAL NOT NULL DEFAULT 80.0,
    critical_pct   REAL NOT NULL DEFAULT 95.0
);

CREATE TABLE IF NOT EXISTS alert_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id TEXT NOT NULL REFERENCES equipment(equipment_id),
    alert_type   TEXT NOT NULL,  -- WARNING, CRITICAL
    load_rate_pct REAL NOT NULL,
    threshold_pct REAL NOT NULL,
    triggered_at TEXT NOT NULL,
    resolved_at  TEXT,
    message      TEXT
);

CREATE INDEX IF NOT EXISTS idx_load_rate_equip_time ON load_rate(equipment_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_alert_history_time ON alert_history(triggered_at);

-- ── Lot(생산 단위) ──────────────────────────────────────
-- 하나의 Lot은 여러 상태를 거침: SCHEDULED → IN_TRANSIT → IN_PROCESS → COMPLETED
-- ⚠ "설비의 Lot" 질문 시 의미 모호성:
--   (A) lot.current_equipment_id = ? → 현재 물리적으로 설비에 있는 Lot
--   (B) lot_schedule.equipment_id = ? → 해당 설비에 예정된 Lot
--   (C) lot.status = 'IN_PROCESS' AND lot.current_equipment_id = ? → 가동 중인 Lot
CREATE TABLE IF NOT EXISTS lot (
    lot_id               TEXT PRIMARY KEY,        -- LOT-001
    product_type         TEXT NOT NULL,            -- OLED_A, OLED_B, LCD_C
    quantity             INTEGER NOT NULL,         -- 수량 (장)
    status               TEXT NOT NULL,            -- SCHEDULED, IN_TRANSIT, IN_PROCESS, COMPLETED
    current_equipment_id TEXT REFERENCES equipment(equipment_id),  -- 현재 위치 (NULL=미배정)
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

-- ── Lot 스케줄(생산 계획) ───────────────────────────────
-- 특정 설비에서 특정 시간에 처리될 예정인 Lot
-- lot.current_equipment_id와 lot_schedule.equipment_id는 다를 수 있음!
-- 예: Lot이 AGV로 이동 중(current=AGV)이지만 스케줄은 컨베이어(schedule=CVR)
CREATE TABLE IF NOT EXISTS lot_schedule (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id          TEXT NOT NULL REFERENCES lot(lot_id),
    equipment_id    TEXT NOT NULL REFERENCES equipment(equipment_id),
    scheduled_start TEXT NOT NULL,
    scheduled_end   TEXT NOT NULL,
    actual_start    TEXT,   -- NULL이면 아직 시작 안 함
    actual_end      TEXT
);

CREATE INDEX IF NOT EXISTS idx_lot_status ON lot(status);
CREATE INDEX IF NOT EXISTS idx_lot_equipment ON lot(current_equipment_id);
CREATE INDEX IF NOT EXISTS idx_lot_schedule_equip ON lot_schedule(equipment_id);
