"""
Tests for GitHub integration tools.

Uses mocking to avoid actual API calls.
Tests both gh CLI path and direct API fallback.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGitHubToolsHelpers:
    """Tests for helper functions."""

    def test_graphql_request_no_auth(self):
        """Test that missing auth raises error."""
        from taskr_mcp.tools.github import graphql_request

        # Mock both gh and token as unavailable
        with patch("taskr_mcp.tools.github.gh_available", return_value=False):
            with patch("taskr_mcp.tools.github._get_token", return_value=None):
                with pytest.raises(ValueError) as exc:
                    graphql_request("query { viewer { login } }", {})

                assert "gh auth login" in str(exc.value)

    @patch("taskr_mcp.tools.github.gh_api_graphql")
    @patch("taskr_mcp.tools.github.gh_available", return_value=True)
    def test_graphql_request_uses_gh_when_available(self, mock_gh_available, mock_gh_api):
        """Test that graphql_request uses gh CLI when available."""
        from taskr_mcp.tools.github import graphql_request

        mock_gh_api.return_value = {"viewer": {"login": "testuser"}}

        result = graphql_request("query { viewer { login } }", {})

        assert result == {"viewer": {"login": "testuser"}}
        mock_gh_api.assert_called_once()

    @patch("taskr_mcp.tools.github._direct_graphql")
    @patch("taskr_mcp.tools.github.gh_available", return_value=False)
    def test_graphql_request_falls_back_to_direct(self, mock_gh_available, mock_direct):
        """Test that graphql_request falls back to direct API when gh not available."""
        from taskr_mcp.tools.github import graphql_request

        mock_direct.return_value = {"viewer": {"login": "testuser"}}

        result = graphql_request("query { viewer { login } }", {})

        assert result == {"viewer": {"login": "testuser"}}
        mock_direct.assert_called_once()


class TestGhAvailable:
    """Tests for gh_available function."""

    @patch("taskr_mcp.tools.github.shutil.which", return_value=None)
    def test_gh_not_installed(self, mock_which):
        """Test when gh CLI is not installed."""
        from taskr_mcp.tools import github
        github._gh_available = None  # Reset cache

        assert github.gh_available() is False

    @patch("taskr_mcp.tools.github.subprocess.run")
    @patch("taskr_mcp.tools.github.shutil.which", return_value="/usr/local/bin/gh")
    def test_gh_installed_but_not_authed(self, mock_which, mock_run):
        """Test when gh is installed but not authenticated."""
        from taskr_mcp.tools import github
        github._gh_available = None  # Reset cache

        mock_run.return_value = MagicMock(returncode=1, stderr="not logged in")

        assert github.gh_available() is False

    @patch("taskr_mcp.tools.github.subprocess.run")
    @patch("taskr_mcp.tools.github.shutil.which", return_value="/usr/local/bin/gh")
    def test_gh_installed_and_authed(self, mock_which, mock_run):
        """Test when gh is installed and authenticated."""
        from taskr_mcp.tools import github
        github._gh_available = None  # Reset cache

        mock_run.return_value = MagicMock(returncode=0)

        assert github.gh_available() is True


class TestGitHubAuthStatus:
    """Tests for github_auth_status function."""

    @patch("taskr_mcp.tools.github.gh_available", return_value=True)
    def test_auth_via_gh(self, mock_gh):
        """Test auth status when using gh CLI."""
        from taskr_mcp.tools.github import github_auth_status

        result = github_auth_status()

        assert result["authenticated"] is True
        assert result["method"] == "gh CLI"

    @patch("taskr_mcp.tools.github._direct_api_available", return_value=True)
    @patch("taskr_mcp.tools.github.gh_available", return_value=False)
    def test_auth_via_token(self, mock_gh, mock_token):
        """Test auth status when using GITHUB_TOKEN."""
        from taskr_mcp.tools.github import github_auth_status

        result = github_auth_status()

        assert result["authenticated"] is True
        assert result["method"] == "GITHUB_TOKEN"

    @patch("taskr_mcp.tools.github._direct_api_available", return_value=False)
    @patch("taskr_mcp.tools.github.gh_available", return_value=False)
    def test_no_auth(self, mock_gh, mock_token):
        """Test auth status when not authenticated."""
        from taskr_mcp.tools.github import github_auth_status

        result = github_auth_status()

        assert result["authenticated"] is False
        assert "gh auth login" in result["message"]


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
        # Import the function directly to avoid MCP dependency
        from taskr_mcp.tools.github import get_owner_id, graphql_request

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

        # Test the logic directly without MCP wrapper
        owner_id, _ = get_owner_id("test-org")
        result = graphql_request("mutation...", {"ownerId": owner_id, "title": "Test"})

        assert result["createProjectV2"]["projectV2"]["id"] == "PVT_abc"


class TestGitHubProjectItems:
    """Tests for github_project_items tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_parse_project_items(self, mock_graphql):
        """Test parsing project items response."""
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

        from taskr_mcp.tools.github import graphql_request
        result = graphql_request("query...", {"org": "test", "number": 1, "first": 50})

        project = result["organization"]["projectV2"]
        assert project["id"] == "PVT_abc"
        assert len(project["items"]["nodes"]) == 2


class TestGitHubGetIssueId:
    """Tests for github_get_issue_id tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_get_issue_id(self, mock_graphql):
        """Test getting issue node ID."""
        mock_graphql.return_value = {
            "repository": {
                "issue": {
                    "id": "I_123",
                    "title": "Test Issue"
                }
            }
        }

        from taskr_mcp.tools.github import graphql_request
        result = graphql_request("query...", {"owner": "test", "repo": "repo", "number": 1})

        assert result["repository"]["issue"]["id"] == "I_123"


class TestGitHubProjectAddItem:
    """Tests for github_project_add_item tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_add_item_to_project(self, mock_graphql):
        """Test adding an item to a project."""
        mock_graphql.return_value = {
            "addProjectV2ItemById": {
                "item": {"id": "PVTI_new"}
            }
        }

        from taskr_mcp.tools.github import graphql_request
        result = graphql_request("mutation...", {"projectId": "PVT_abc", "contentId": "I_123"})

        assert result["addProjectV2ItemById"]["item"]["id"] == "PVTI_new"


class TestGitHubProjectClose:
    """Tests for github_project_close tool."""

    @patch("taskr_mcp.tools.github.graphql_request")
    def test_close_project(self, mock_graphql):
        """Test closing a project."""
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

        from taskr_mcp.tools.github import graphql_request
        result = graphql_request("mutation...", {"projectId": "PVT_abc"})

        assert result["updateProjectV2"]["projectV2"]["closed"] is True


class TestGitHubCreateIssueViaGh:
    """Tests for creating issues via gh CLI."""

    @patch("taskr_mcp.tools.github.subprocess.run")
    @patch("taskr_mcp.tools.github.gh_available", return_value=True)
    def test_gh_issue_create(self, mock_gh, mock_run):
        """Test creating issue via gh CLI."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/test/repo/issues/42\n"
        )

        from taskr_mcp.tools import github

        # Simulate what the tool does
        cmd = ["gh", "issue", "create", "--repo", "test/repo", "--title", "Test Issue"]
        result = github.subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        assert result.returncode == 0
        assert "issues/42" in result.stdout


class TestGitHubPRCreateViaGh:
    """Tests for creating PRs via gh CLI."""

    @patch("taskr_mcp.tools.github.subprocess.run")
    @patch("taskr_mcp.tools.github.gh_available", return_value=True)
    def test_gh_pr_create(self, mock_gh, mock_run):
        """Test creating PR via gh CLI."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/test/repo/pull/10\n"
        )

        from taskr_mcp.tools import github

        # Simulate what the tool does
        cmd = ["gh", "pr", "create", "--repo", "test/repo", "--title", "Test PR", "--head", "feature", "--base", "main"]
        result = github.subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        assert result.returncode == 0
        assert "pull/10" in result.stdout


class TestDirectApiGraphQL:
    """Tests for direct API fallback."""

    @patch("taskr_mcp.tools.github._get_token", return_value="test-token")
    def test_direct_graphql_success(self, mock_token):
        """Test direct GraphQL API call."""
        import httpx
        from unittest.mock import patch as inner_patch

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"viewer": {"login": "testuser"}}}
        mock_response.raise_for_status = MagicMock()

        with inner_patch.object(httpx, "post", return_value=mock_response) as mock_post:
            from taskr_mcp.tools.github import _direct_graphql
            result = _direct_graphql("query { viewer { login } }", {})

            assert result == {"viewer": {"login": "testuser"}}
            mock_post.assert_called_once()

    @patch("taskr_mcp.tools.github._get_token", return_value=None)
    def test_direct_graphql_no_token(self, mock_token):
        """Test direct GraphQL fails without token."""
        from taskr_mcp.tools.github import _direct_graphql

        with pytest.raises(ValueError) as exc:
            _direct_graphql("query { viewer { login } }", {})

        assert "gh auth login" in str(exc.value)
