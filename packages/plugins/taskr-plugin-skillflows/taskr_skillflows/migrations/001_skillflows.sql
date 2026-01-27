-- Skillflows Plugin Migration
-- Creates tables for workflow definitions and execution tracking

-- ============================================================================
-- SKILLFLOWS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS taskr.skillflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    version INTEGER NOT NULL DEFAULT 1,
    inputs JSONB[] DEFAULT '{}',
    outputs JSONB[] DEFAULT '{}',
    preconditions JSONB[] DEFAULT '{}',
    steps JSONB[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    author VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT chk_skillflow_status CHECK (status IN ('draft', 'active', 'deprecated'))
);

-- Skillflow indexes
CREATE INDEX IF NOT EXISTS idx_skillflows_name ON taskr.skillflows(name) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_skillflows_status ON taskr.skillflows(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_skillflows_tags ON taskr.skillflows USING gin(tags) WHERE deleted_at IS NULL;

-- Full-text search on skillflows
ALTER TABLE taskr.skillflows ADD COLUMN IF NOT EXISTS search_vector TSVECTOR
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', array_to_string(tags, ' ')), 'C')
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_skillflows_search ON taskr.skillflows USING gin(search_vector);

-- ============================================================================
-- SKILLFLOW EXECUTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS taskr.skillflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skillflow_id UUID REFERENCES taskr.skillflows(id),
    skillflow_name VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    inputs JSONB DEFAULT '{}',
    outputs JSONB DEFAULT '{}',
    step_results JSONB[] DEFAULT '{}',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    error_message TEXT,
    deleted_at TIMESTAMPTZ,

    CONSTRAINT chk_execution_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'cancelled')
    )
);

-- Execution indexes
CREATE INDEX IF NOT EXISTS idx_executions_skillflow ON taskr.skillflow_executions(skillflow_id);
CREATE INDEX IF NOT EXISTS idx_executions_name ON taskr.skillflow_executions(skillflow_name);
CREATE INDEX IF NOT EXISTS idx_executions_status ON taskr.skillflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_executions_started ON taskr.skillflow_executions(started_at DESC);

-- ============================================================================
-- VIEW: Skillflows with metrics
-- ============================================================================

CREATE OR REPLACE VIEW taskr.v_skillflows AS
SELECT
    s.*,
    COUNT(e.id) as execution_count,
    COUNT(CASE WHEN e.status = 'completed' THEN 1 END) as success_count,
    COUNT(CASE WHEN e.status = 'failed' THEN 1 END) as failure_count,
    COALESCE(AVG(CASE WHEN e.status = 'completed' THEN 1.0 ELSE 0.0 END), 0) as success_rate,
    AVG(e.duration_ms) as avg_duration_ms
FROM taskr.skillflows s
LEFT JOIN taskr.skillflow_executions e ON s.id = e.skillflow_id AND e.deleted_at IS NULL
WHERE s.deleted_at IS NULL
GROUP BY s.id;

-- ============================================================================
-- AUTO-UPDATE TRIGGER
-- ============================================================================

DROP TRIGGER IF EXISTS tr_skillflows_updated ON taskr.skillflows;
CREATE TRIGGER tr_skillflows_updated
    BEFORE UPDATE ON taskr.skillflows
    FOR EACH ROW
    EXECUTE FUNCTION taskr.update_updated_at();
