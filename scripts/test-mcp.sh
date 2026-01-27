#!/bin/bash
# Test taskr MCP server using Claude CLI
#
# Usage:
#   ./scripts/test-mcp.sh           # Run all tests
#   ./scripts/test-mcp.sh devlog    # Run specific test
#
# Requirements:
#   - Claude CLI installed
#   - GITHUB_TOKEN env var set (for GitHub tools)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$REPO_DIR/.test-results"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p "$RESULTS_DIR"

# Create temporary MCP config for taskr
MCP_CONFIG=$(cat <<EOF
{
  "mcpServers": {
    "taskr": {
      "command": "python",
      "args": ["-m", "taskr_mcp"],
      "cwd": "$REPO_DIR/packages/taskr-mcp",
      "env": {
        "PYTHONPATH": "$REPO_DIR/packages/taskr-core:$REPO_DIR/packages/taskr-mcp",
        "GITHUB_TOKEN": "${GITHUB_TOKEN:-}"
      }
    }
  }
}
EOF
)

# Helper to run a test
run_test() {
    local name="$1"
    local prompt="$2"
    local output_file="$RESULTS_DIR/${name}.txt"

    echo -e "${YELLOW}Testing: $name${NC}"

    if claude -p \
        --mcp-config "$MCP_CONFIG" \
        --strict-mcp-config \
        --permission-mode bypassPermissions \
        --model haiku \
        "$prompt" > "$output_file" 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}: $name"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}: $name"
        echo "  Output: $output_file"
        return 1
    fi
}

# Test functions
test_devlog_add() {
    run_test "devlog_add" \
        "Use devlog_add to create a test entry with category='note', title='MCP Test', content='Testing the MCP server'. Return the devlog ID."
}

test_devlog_list() {
    run_test "devlog_list" \
        "Use devlog_list to show recent devlogs. List the titles."
}

test_devlog_search() {
    run_test "devlog_search" \
        "Use devlog_search to search for 'MCP Test'. Return what you found."
}

test_task_create() {
    run_test "task_create" \
        "Use taskr_create to create a task with title='Test Task from MCP', priority='low'. Return the task ID."
}

test_task_list() {
    run_test "task_list" \
        "Use taskr_list to show all tasks. List their titles and statuses."
}

test_task_search() {
    run_test "task_search" \
        "Use taskr_search to find tasks matching 'Test Task'. Return what you found."
}

test_session_start() {
    run_test "session_start" \
        "Use taskr_session_start with agent_id='test-agent' and context='MCP test session'. Return the session_id."
}

test_health() {
    run_test "health" \
        "Use taskr_health to check database connectivity. Report the status."
}

test_triage() {
    run_test "triage" \
        "Use taskr_triage with request='Test triage functionality'. Summarize the recommended workflow."
}

# GitHub tools (require GITHUB_TOKEN)
test_github_project_items() {
    if [ -z "$GITHUB_TOKEN" ]; then
        echo -e "${YELLOW}SKIPPED${NC}: github_project_items (no GITHUB_TOKEN)"
        return 0
    fi
    run_test "github_project_items" \
        "Use github_project_items to list items in rhea-impact org, project number 1. List the first 3 items."
}

# Run tests
echo "========================================"
echo "Taskr MCP Integration Tests"
echo "========================================"
echo ""

FAILED=0
PASSED=0
SKIPPED=0

# Parse arguments
if [ $# -gt 0 ]; then
    # Run specific test
    test_func="test_$1"
    if declare -f "$test_func" > /dev/null; then
        if $test_func; then
            PASSED=$((PASSED + 1))
        else
            FAILED=$((FAILED + 1))
        fi
    else
        echo "Unknown test: $1"
        echo "Available tests: devlog_add, devlog_list, devlog_search, task_create, task_list, task_search, session_start, health, triage, github_project_items"
        exit 1
    fi
else
    # Run all tests
    tests=(
        "health"
        "devlog_add"
        "devlog_list"
        "devlog_search"
        "task_create"
        "task_list"
        "task_search"
        "session_start"
        "triage"
        "github_project_items"
    )

    for test in "${tests[@]}"; do
        test_func="test_$test"
        if $test_func; then
            PASSED=$((PASSED + 1))
        else
            FAILED=$((FAILED + 1))
        fi
        echo ""
    done
fi

echo "========================================"
echo "Results: $PASSED passed, $FAILED failed"
echo "========================================"

if [ $FAILED -gt 0 ]; then
    echo ""
    echo "Test outputs saved to: $RESULTS_DIR/"
    exit 1
fi
