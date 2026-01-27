-- Taskr Core Tables - SQLite
-- Migration: 001_core_tables

-- Create schema_migrations table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now'))
);

-- ============================================================================
-- TASKS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'done', 'cancelled')),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    assignee TEXT,
    tags TEXT DEFAULT '[]',  -- JSON array
    created_by TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    due_at TEXT,
    completed_at TEXT,
    deleted_at TEXT
);

-- Task indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_deleted ON tasks(deleted_at);

-- ============================================================================
-- DEVLOGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS devlogs (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    category TEXT NOT NULL CHECK (
        category IN ('feature', 'bugfix', 'deployment', 'config', 'incident',
                     'refactor', 'research', 'decision', 'migration', 'note')
    ),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT,
    agent_id TEXT DEFAULT 'claude-code',
    service_name TEXT,
    tags TEXT DEFAULT '[]',  -- JSON array
    metadata TEXT DEFAULT '{}',  -- JSON object
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    deleted_at TEXT
);

-- Devlog indexes
CREATE INDEX IF NOT EXISTS idx_devlogs_category ON devlogs(category) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_devlogs_service ON devlogs(service_name) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_devlogs_agent ON devlogs(agent_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_devlogs_created ON devlogs(created_at);
CREATE INDEX IF NOT EXISTS idx_devlogs_deleted ON devlogs(deleted_at);

-- ============================================================================
-- AGENT SESSIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_sessions (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    agent_id TEXT NOT NULL,
    started_at TEXT DEFAULT (datetime('now')),
    ended_at TEXT,
    summary TEXT,
    handoff_notes TEXT,
    context TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Session indexes
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON agent_sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON agent_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON agent_sessions(agent_id) WHERE ended_at IS NULL;

-- ============================================================================
-- AGENT ACTIVITY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_activity (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    agent_id TEXT NOT NULL,
    session_id TEXT REFERENCES agent_sessions(id),
    activity_type TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    repo TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Activity indexes
CREATE INDEX IF NOT EXISTS idx_activity_agent ON agent_activity(agent_id);
CREATE INDEX IF NOT EXISTS idx_activity_session ON agent_activity(session_id);
CREATE INDEX IF NOT EXISTS idx_activity_target ON agent_activity(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_activity_created ON agent_activity(created_at);

-- ============================================================================
-- AUTO-UPDATE TRIGGER (SQLite version)
-- ============================================================================

-- Tasks updated_at trigger
CREATE TRIGGER IF NOT EXISTS tr_tasks_updated
    AFTER UPDATE ON tasks
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE tasks SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Devlogs updated_at trigger
CREATE TRIGGER IF NOT EXISTS tr_devlogs_updated
    AFTER UPDATE ON devlogs
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE devlogs SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Sessions updated_at trigger
CREATE TRIGGER IF NOT EXISTS tr_sessions_updated
    AFTER UPDATE ON agent_sessions
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE agent_sessions SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Record this migration
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('001');
