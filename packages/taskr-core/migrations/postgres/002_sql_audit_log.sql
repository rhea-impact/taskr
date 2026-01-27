-- SQL Audit Log Table
-- Tracks all SQL migrations run via taskr_sql_migrate

CREATE TABLE IF NOT EXISTS sql_audit_log (
    id SERIAL PRIMARY KEY,
    sql_text TEXT NOT NULL,
    reason TEXT NOT NULL,
    executed_by TEXT NOT NULL DEFAULT 'unknown',
    execution_time_ms NUMERIC(10, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for querying by executor
CREATE INDEX IF NOT EXISTS idx_sql_audit_log_executed_by ON sql_audit_log(executed_by);

-- Index for querying by time
CREATE INDEX IF NOT EXISTS idx_sql_audit_log_created_at ON sql_audit_log(created_at DESC);

COMMENT ON TABLE sql_audit_log IS 'Audit log for SQL migrations run via taskr_sql_migrate';
