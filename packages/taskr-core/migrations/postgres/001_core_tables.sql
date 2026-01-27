-- Taskr Core Tables - PostgreSQL
-- Migration: 001_core_tables

-- Create schema
CREATE SCHEMA IF NOT EXISTS taskr;

-- Create schema_migrations table if not exists
CREATE TABLE IF NOT EXISTS taskr.schema_migrations (
    version VARCHAR(10) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- TASKS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS taskr.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    assignee VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    due_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,

    CONSTRAINT chk_task_status CHECK (status IN ('open', 'in_progress', 'done', 'cancelled')),
    CONSTRAINT chk_task_priority CHECK (priority IN ('low', 'medium', 'high', 'critical'))
);

-- Task indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status ON taskr.tasks(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON taskr.tasks(assignee) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_created ON taskr.tasks(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_tags ON taskr.tasks USING gin(tags) WHERE deleted_at IS NULL;

-- Task full-text search
ALTER TABLE taskr.tasks ADD COLUMN IF NOT EXISTS search_vector TSVECTOR
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_tasks_search ON taskr.tasks USING gin(search_vector);

-- ============================================================================
-- DEVLOGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS taskr.devlogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(100),
    agent_id VARCHAR(100) DEFAULT 'claude-code',
    service_name VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT chk_devlog_category CHECK (
        category IN ('feature', 'bugfix', 'deployment', 'config', 'incident',
                     'refactor', 'research', 'decision', 'migration', 'note')
    )
);

-- Devlog indexes
CREATE INDEX IF NOT EXISTS idx_devlogs_category ON taskr.devlogs(category) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_devlogs_service ON taskr.devlogs(service_name) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_devlogs_agent ON taskr.devlogs(agent_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_devlogs_created ON taskr.devlogs(created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_devlogs_tags ON taskr.devlogs USING gin(tags) WHERE deleted_at IS NULL;

-- Devlog full-text search
ALTER TABLE taskr.devlogs ADD COLUMN IF NOT EXISTS search_vector TSVECTOR
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'B')
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_devlogs_search ON taskr.devlogs USING gin(search_vector);

-- ============================================================================
-- AGENT SESSIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS taskr.agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    summary TEXT,
    handoff_notes TEXT,
    context TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Session indexes
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON taskr.agent_sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON taskr.agent_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON taskr.agent_sessions(agent_id) WHERE ended_at IS NULL;

-- ============================================================================
-- AGENT ACTIVITY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS taskr.agent_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,
    session_id UUID REFERENCES taskr.agent_sessions(id),
    activity_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_id VARCHAR(255),
    repo VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Activity indexes
CREATE INDEX IF NOT EXISTS idx_activity_agent ON taskr.agent_activity(agent_id);
CREATE INDEX IF NOT EXISTS idx_activity_session ON taskr.agent_activity(session_id);
CREATE INDEX IF NOT EXISTS idx_activity_target ON taskr.agent_activity(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_activity_created ON taskr.agent_activity(created_at DESC);

-- ============================================================================
-- AUTO-UPDATE TRIGGER
-- ============================================================================

CREATE OR REPLACE FUNCTION taskr.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
DROP TRIGGER IF EXISTS tr_tasks_updated ON taskr.tasks;
CREATE TRIGGER tr_tasks_updated
    BEFORE UPDATE ON taskr.tasks
    FOR EACH ROW
    EXECUTE FUNCTION taskr.update_updated_at();

DROP TRIGGER IF EXISTS tr_devlogs_updated ON taskr.devlogs;
CREATE TRIGGER tr_devlogs_updated
    BEFORE UPDATE ON taskr.devlogs
    FOR EACH ROW
    EXECUTE FUNCTION taskr.update_updated_at();

DROP TRIGGER IF EXISTS tr_sessions_updated ON taskr.agent_sessions;
CREATE TRIGGER tr_sessions_updated
    BEFORE UPDATE ON taskr.agent_sessions
    FOR EACH ROW
    EXECUTE FUNCTION taskr.update_updated_at();

-- Record this migration
INSERT INTO taskr.schema_migrations (version) VALUES ('001')
ON CONFLICT (version) DO NOTHING;
