"""
GitHub MCP tools for Taskr.

Tools for GitHub Projects V2 integration.
"""

from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from taskr_github.plugin import GitHubPlugin


def register(mcp: "FastMCP", plugin: "GitHubPlugin") -> None:
    """Register GitHub tools with the MCP server."""

    @mcp.tool()
    async def github_create_issue(
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> dict:
        """
        Create a GitHub issue.

        Args:
            owner: Repository owner (e.g., 'rhea-impact')
            repo: Repository name (e.g., 'taskr')
            title: Issue title
            body: Issue body/description
            labels: List of label names
            assignees: List of usernames to assign

        Returns:
            Issue details including number and URL
        """
        import httpx

        token = plugin.get_github_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                json={
                    "title": title,
                    "body": body,
                    "labels": labels or [],
                    "assignees": assignees or [],
                },
            )
            response.raise_for_status()
            data = response.json()

        return {
            "number": data["number"],
            "url": data["html_url"],
            "title": data["title"],
            "state": data["state"],
        }

    @mcp.tool()
    async def github_list_issues(
        owner: str,
        repo: str,
        state: str = "open",
        labels: Optional[str] = None,
        limit: int = 30,
    ) -> dict:
        """
        List GitHub issues.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)
            labels: Comma-separated label names
            limit: Maximum results

        Returns:
            List of issues
        """
        import httpx

        token = plugin.get_github_token()

        params = {
            "state": state,
            "per_page": min(limit, 100),
        }
        if labels:
            params["labels"] = labels

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                params=params,
            )
            response.raise_for_status()
            issues = response.json()

        return {
            "issues": [
                {
                    "number": i["number"],
                    "title": i["title"],
                    "state": i["state"],
                    "url": i["html_url"],
                    "assignees": [a["login"] for a in i.get("assignees", [])],
                    "labels": [l["name"] for l in i.get("labels", [])],
                }
                for i in issues
                if "pull_request" not in i  # Exclude PRs
            ],
            "count": len([i for i in issues if "pull_request" not in i]),
        }

    @mcp.tool()
    async def github_create_pr(
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: Optional[str] = None,
        issue: Optional[int] = None,
        draft: bool = False,
    ) -> dict:
        """
        Create a pull request with optional issue linking.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Branch containing changes
            base: Branch to merge into (default: main)
            body: PR description
            issue: Issue number to link (adds "Closes #X")
            draft: Create as draft PR

        Returns:
            PR details including number and URL
        """
        import httpx

        token = plugin.get_github_token()

        # Add issue link to body
        pr_body = body or ""
        if issue:
            pr_body = f"{pr_body}\n\nCloses #{issue}".strip()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                json={
                    "title": title,
                    "head": head,
                    "base": base,
                    "body": pr_body,
                    "draft": draft,
                },
            )
            response.raise_for_status()
            data = response.json()

        return {
            "number": data["number"],
            "url": data["html_url"],
            "title": data["title"],
            "state": data["state"],
            "draft": data["draft"],
            "linked_issue": issue,
        }
