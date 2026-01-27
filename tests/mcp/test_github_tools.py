"""
Tests for GitHub integration tools.

Uses mocking to avoid actual API calls.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGitHubToolsHelpers:
    """Tests for helper functions."""

    def test_graphql_request_missing_token(self):
        """Test that missing token raises error."""
        from taskr_mcp.tools.github import graphql_request

        with patch.dict("os.environ", {}, clear=True):
            with patch("taskr_mcp.tools.github.GITHUB_TOKEN", None):
                with pytest.raises(ValueError) as exc:
                    graphql_request("query { viewer { login } }", {})

                assert "GITHUB_TOKEN" in str(exc.value)

    @patch("taskr_mcp.tools.github.httpx.post")
    @patch("taskr_mcp.tools.github.GITHUB_TOKEN", "test-token")
    def test_graphql_request_success(self, mock_post):
        """Test successful GraphQL request."""
        from taskr_mcp.tools.github import graphql_request

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"viewer": {"login": "testuser"}}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = graphql_request("query { viewer { login } }", {})

        assert result == {"viewer": {"login": "testuser"}}
        mock_post.assert_called_once()

    @patch("taskr_mcp.tools.github.httpx.post")
    @patch("taskr_mcp.tools.github.GITHUB_TOKEN", "test-token")
    def test_graphql_request_handles_errors(self, mock_post):
        """Test that GraphQL errors are raised."""
        from taskr_mcp.tools.github import graphql_request

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "errors": [{"message": "Not found"}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with pytest.raises(ValueError) as exc:
            graphql_request("query { viewer { login } }", {})

        assert "GraphQL error" in str(exc.value)


class TestGetOwnerId:
    """Tests for get_owner_id function."""

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_get_org_id(self, mock_graphql):
        """Test getting organization ID."""
        from taskr_mcp.tools.github import get_owner_id

        mock_graphql.return_value = {"organization": {"id": "O_123"}}

        node_id, node_type = get_owner_id("rhea-impact")

        assert node_id == "O_123"
        assert node_type == "organization"

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_get_user_id_fallback(self, mock_graphql):
        """Test falling back to user when org not found."""
        from taskr_mcp.tools.github import get_owner_id

        # First call (org) returns None, second call (user) returns ID
        mock_graphql.side_effect = [
            {"organization": None},
            {"user": {"id": "U_456"}}
        ]

        node_id, node_type = get_owner_id("testuser")

        assert node_id == "U_456"
        assert node_type == "user"

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_get_owner_id_not_found(self, mock_graphql):
        """Test error when neither org nor user found."""
        from taskr_mcp.tools.github import get_owner_id

        mock_graphql.side_effect = [
            {"organization": None},
            {"user": None}
        ]

        with pytest.raises(ValueError) as exc:
            get_owner_id("nonexistent")

        assert "Could not find" in str(exc.value)


class TestGitHubProjectCreate:
    """Tests for github_project_create tool."""

    @patch("taskr_mcp.tools.github.get_owner_id")
    @patch("taskr_mcp.tools.github.graphql_request")
    def test_create_project_success(self, mock_graphql, mock_get_owner):
        """Test successfully creating a project."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        mock_get_owner.return_value = ("O_123", "organization")
        mock_graphql.return_value = {
            "createProjectV2": {
                "projectV2": {
                    "id": "PVT_abc",
                    "number": 1,
                    "title": "Test Project",
                    "url": "https://github.com/orgs/test/projects/1"
                }
            }
        }

        # Get the tool function
        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_project_create":
                tool_fn = tool.fn
                break

        result = tool_fn(title="Test Project", org="test-org")

        assert result["id"] == "PVT_abc"
        assert result["title"] == "Test Project"

    @patch("taskr_mcp.tools.github.get_owner_id")
    def test_create_project_error(self, mock_get_owner):
        """Test error handling when creation fails."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        mock_get_owner.side_effect = ValueError("Not found")

        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_project_create":
                tool_fn = tool.fn
                break

        result = tool_fn(title="Test", org="nonexistent")

        assert "error" in result


class TestGitHubProjectItems:
    """Tests for github_project_items tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_list_project_items(self, mock_graphql):
        """Test listing project items."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        mock_graphql.return_value = {
            "organization": {
                "projectV2": {
                    "id": "PVT_abc",
                    "title": "Test Project",
                    "items": {
                        "nodes": [
                            {
                                "id": "PVTI_1",
                                "fieldValueByName": {"name": "Todo"},
                                "content": {
                                    "number": 1,
                                    "title": "Issue 1",
                                    "state": "OPEN"
                                }
                            },
                            {
                                "id": "PVTI_2",
                                "fieldValueByName": {"name": "Done"},
                                "content": {
                                    "number": 2,
                                    "title": "Issue 2",
                                    "state": "CLOSED"
                                }
                            }
                        ]
                    }
                }
            }
        }

        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_project_items":
                tool_fn = tool.fn
                break

        result = tool_fn(org="test-org", project_number=1)

        assert result["project_id"] == "PVT_abc"
        assert result["count"] == 2
        assert len(result["items"]) == 2

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_list_project_items_with_status_filter(self, mock_graphql):
        """Test filtering items by status."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        mock_graphql.return_value = {
            "organization": {
                "projectV2": {
                    "id": "PVT_abc",
                    "title": "Test Project",
                    "items": {
                        "nodes": [
                            {
                                "id": "PVTI_1",
                                "fieldValueByName": {"name": "Todo"},
                                "content": {"number": 1, "title": "Issue 1", "state": "OPEN"}
                            },
                            {
                                "id": "PVTI_2",
                                "fieldValueByName": {"name": "Done"},
                                "content": {"number": 2, "title": "Issue 2", "state": "CLOSED"}
                            }
                        ]
                    }
                }
            }
        }

        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_project_items":
                tool_fn = tool.fn
                break

        result = tool_fn(org="test-org", project_number=1, status="Todo")

        assert result["count"] == 1
        assert result["items"][0]["status"] == "Todo"


class TestGitHubGetIssueId:
    """Tests for github_get_issue_id tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_get_issue_id(self, mock_graphql):
        """Test getting issue node ID."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        mock_graphql.return_value = {
            "repository": {
                "issue": {
                    "id": "I_123",
                    "title": "Test Issue"
                }
            }
        }

        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_get_issue_id":
                tool_fn = tool.fn
                break

        result = tool_fn(owner="test-owner", repo="test-repo", issue_number=1)

        assert result["id"] == "I_123"
        assert result["title"] == "Test Issue"


class TestGitHubProjectAddItem:
    """Tests for github_project_add_item tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_add_item_to_project(self, mock_graphql):
        """Test adding an item to a project."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        mock_graphql.return_value = {
            "addProjectV2ItemById": {
                "item": {"id": "PVTI_new"}
            }
        }

        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_project_add_item":
                tool_fn = tool.fn
                break

        result = tool_fn(project_id="PVT_abc", content_id="I_123")

        assert result["item_id"] == "PVTI_new"


class TestGitHubProjectClose:
    """Tests for github_project_close tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_close_project(self, mock_graphql):
        """Test closing a project."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        mock_graphql.return_value = {
            "updateProjectV2": {
                "projectV2": {
                    "id": "PVT_abc",
                    "title": "Test Project",
                    "closed": True,
                    "url": "https://github.com/orgs/test/projects/1"
                }
            }
        }

        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_project_close":
                tool_fn = tool.fn
                break

        result = tool_fn(project_id="PVT_abc")

        assert result["closed"] is True


class TestGitHubProjectReopen:
    """Tests for github_project_reopen tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_reopen_project(self, mock_graphql):
        """Test reopening a project."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        mock_graphql.return_value = {
            "updateProjectV2": {
                "projectV2": {
                    "id": "PVT_abc",
                    "title": "Test Project",
                    "closed": False,
                    "url": "https://github.com/orgs/test/projects/1"
                }
            }
        }

        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_project_reopen":
                tool_fn = tool.fn
                break

        result = tool_fn(project_id="PVT_abc")

        assert result["closed"] is False


class TestGitHubCreateIssueInProject:
    """Tests for github_create_issue_in_project tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    @patch("taskr_mcp.tools.github.httpx.post")
    @patch("taskr_mcp.tools.github.GITHUB_TOKEN", "test-token")
    def test_create_issue_in_project(self, mock_post, mock_graphql):
        """Test creating an issue and adding to project."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        # Mock REST API response for issue creation
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "number": 42,
            "html_url": "https://github.com/test/repo/issues/42"
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Mock GraphQL responses
        mock_graphql.side_effect = [
            {"repository": {"issue": {"id": "I_42"}}},  # Get issue ID
            {"addProjectV2ItemById": {"item": {"id": "PVTI_new"}}}  # Add to project
        ]

        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_create_issue_in_project":
                tool_fn = tool.fn
                break

        result = tool_fn(
            owner="test",
            repo="repo",
            title="New Issue",
            project_id="PVT_abc",
            body="Issue description",
        )

        assert result["issue_number"] == 42
        assert result["project_item_id"] == "PVTI_new"


class TestGitHubPRCreate:
    """Tests for github_pr_create tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    @patch("taskr_mcp.tools.github.httpx.post")
    @patch("taskr_mcp.tools.github.GITHUB_TOKEN", "test-token")
    def test_create_pr_basic(self, mock_post, mock_graphql):
        """Test creating a basic PR."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        # Mock REST API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "number": 10,
            "html_url": "https://github.com/test/repo/pull/10"
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_pr_create":
                tool_fn = tool.fn
                break

        result = tool_fn(
            owner="test",
            repo="repo",
            title="New Feature",
            head="feature-branch",
            base="main",
        )

        assert result["pr_number"] == 10
        assert "pr_url" in result

    @patch("taskr_mcp.tools.github.graphql_request")
    @patch("taskr_mcp.tools.github.httpx.post")
    @patch("taskr_mcp.tools.github.GITHUB_TOKEN", "test-token")
    def test_create_pr_with_issue_link(self, mock_post, mock_graphql):
        """Test creating a PR linked to an issue."""
        from mcp.server.fastmcp import FastMCP
        from taskr_mcp.tools.github import register_github_tools

        mcp = FastMCP("test")
        register_github_tools(mcp)

        # Mock REST API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "number": 10,
            "html_url": "https://github.com/test/repo/pull/10"
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Mock GraphQL responses for getting PR ID and issue's project
        mock_graphql.side_effect = [
            {"repository": {"pullRequest": {"id": "PR_10"}}},
            {"repository": {"issue": {"projectItems": {"nodes": [
                {"project": {"id": "PVT_abc", "title": "Project"}}
            ]}}}},
            {"addProjectV2ItemById": {"item": {"id": "PVTI_new"}}}
        ]

        tool_fn = None
        for tool in mcp._tools.values():
            if tool.name == "github_pr_create":
                tool_fn = tool.fn
                break

        result = tool_fn(
            owner="test",
            repo="repo",
            title="Fix Issue",
            head="fix-branch",
            base="main",
            issue=5,
            close_issue=True,
        )

        assert result["pr_number"] == 10
        assert result["linked_issue"] == 5
        assert result["added_to_project"] == "Project"

        # Verify PR body includes "Closes #5"
        call_args = mock_post.call_args
        pr_body = call_args[1]["json"]["body"]
        assert "Closes #5" in pr_body
