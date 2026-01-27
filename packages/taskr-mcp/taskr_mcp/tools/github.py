"""
GitHub integration tools for Taskr.

Core GitHub tools that are essential to the taskr workflow:
- Project management (create, list items, close/reopen)
- Issue creation with project linking
- PR creation with issue linking

Requires GITHUB_TOKEN environment variable.
"""

import os
from typing import Optional, List

import httpx

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def graphql_request(query: str, variables: dict) -> dict:
    """Execute a GitHub GraphQL request."""
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    response = httpx.post(
        GITHUB_GRAPHQL_URL,
        headers=headers,
        json={"query": query, "variables": variables},
        timeout=30.0,
    )
    response.raise_for_status()
    result = response.json()

    if "errors" in result:
        raise ValueError(f"GraphQL error: {result['errors']}")

    return result.get("data", {})


def get_owner_id(login: str) -> tuple[str, str]:
    """Get the node ID for a GitHub organization or user."""
    # Try as organization first
    query = """
    query($login: String!) {
        organization(login: $login) {
            id
        }
    }
    """
    try:
        result = graphql_request(query, {"login": login})
        if result.get("organization"):
            return result["organization"]["id"], "organization"
    except Exception:
        pass

    # Try as user
    query = """
    query($login: String!) {
        user(login: $login) {
            id
        }
    }
    """
    result = graphql_request(query, {"login": login})
    if result.get("user"):
        return result["user"]["id"], "user"

    raise ValueError(f"Could not find organization or user: {login}")


def register_github_tools(mcp):
    """Register GitHub tools with the MCP server."""

    @mcp.tool()
    def github_project_create(title: str, org: str) -> dict:
        """
        Create a GitHub Project v2.

        The official GitHub MCP server cannot create projects - this fills that gap.

        Args:
            title: Project name
            org: Organization or user login that will own the project

        Returns:
            Project details including id, number, title, and url
        """
        try:
            owner_id, _ = get_owner_id(org)

            mutation = """
            mutation($ownerId: ID!, $title: String!) {
                createProjectV2(input: { ownerId: $ownerId, title: $title }) {
                    projectV2 {
                        id
                        number
                        title
                        url
                    }
                }
            }
            """

            result = graphql_request(mutation, {"ownerId": owner_id, "title": title})
            project = result["createProjectV2"]["projectV2"]

            return {
                "id": project["id"],
                "number": project["number"],
                "title": project["title"],
                "url": project["url"],
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def github_project_add_item(project_id: str, content_id: str) -> dict:
        """
        Add an issue or PR to a GitHub Project v2.

        Args:
            project_id: The project's node ID (starts with PVT_)
            content_id: The issue or PR node ID (starts with I_ or PR_)

        Returns:
            Project item details
        """
        try:
            mutation = """
            mutation($projectId: ID!, $contentId: ID!) {
                addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
                    item {
                        id
                    }
                }
            }
            """

            result = graphql_request(mutation, {"projectId": project_id, "contentId": content_id})
            return {"item_id": result["addProjectV2ItemById"]["item"]["id"]}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def github_get_issue_id(owner: str, repo: str, issue_number: int) -> dict:
        """
        Get the node ID for a GitHub issue.

        Useful for getting IDs to pass to github_project_add_item.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            Issue node ID and title
        """
        try:
            query = """
            query($owner: String!, $repo: String!, $number: Int!) {
                repository(owner: $owner, name: $repo) {
                    issue(number: $number) {
                        id
                        title
                    }
                }
            }
            """

            result = graphql_request(query, {"owner": owner, "repo": repo, "number": issue_number})
            issue = result["repository"]["issue"]

            return {
                "id": issue["id"],
                "title": issue["title"],
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def github_get_org_id(login: str) -> dict:
        """
        Get the node ID for a GitHub organization or user.

        Useful for getting IDs to pass to github_project_create.

        Args:
            login: Organization or user login name

        Returns:
            Node ID and type (organization or user)
        """
        try:
            node_id, node_type = get_owner_id(login)
            return {"id": node_id, "type": node_type}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def github_project_close(project_id: str) -> dict:
        """
        Close a GitHub Project v2.

        Closing is reversible (use github_project_reopen to restore).

        Args:
            project_id: The project's node ID (starts with PVT_)

        Returns:
            Project details including closed status
        """
        try:
            mutation = """
            mutation($projectId: ID!) {
                updateProjectV2(input: { projectId: $projectId, closed: true }) {
                    projectV2 {
                        id
                        title
                        closed
                        url
                    }
                }
            }
            """

            result = graphql_request(mutation, {"projectId": project_id})
            project = result["updateProjectV2"]["projectV2"]

            return {
                "id": project["id"],
                "title": project["title"],
                "closed": project["closed"],
                "url": project["url"],
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def github_project_reopen(project_id: str) -> dict:
        """
        Reopen a closed GitHub Project v2.

        Args:
            project_id: The project's node ID (starts with PVT_)

        Returns:
            Project details including closed status
        """
        try:
            mutation = """
            mutation($projectId: ID!) {
                updateProjectV2(input: { projectId: $projectId, closed: false }) {
                    projectV2 {
                        id
                        title
                        closed
                        url
                    }
                }
            }
            """

            result = graphql_request(mutation, {"projectId": project_id})
            project = result["updateProjectV2"]["projectV2"]

            return {
                "id": project["id"],
                "title": project["title"],
                "closed": project["closed"],
                "url": project["url"],
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def github_create_issue_in_project(
        owner: str,
        repo: str,
        title: str,
        project_id: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> dict:
        """
        Create a GitHub issue AND add it to a project in one call.

        Solves the "orphaned issues" problem by atomically creating an issue
        and linking it to a project. No more forgetting to add issues to projects.

        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            project_id: Project node ID (starts with PVT_)
            body: Issue body/description (optional)
            labels: List of label names to apply (optional)
            assignees: List of usernames to assign (optional)

        Returns:
            Issue details including number, url, and project item id
        """
        if not GITHUB_TOKEN:
            return {"error": "GITHUB_TOKEN environment variable not set"}

        try:
            # Step 1: Create the issue via REST API
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            issue_data = {"title": title}
            if body:
                issue_data["body"] = body
            if labels:
                issue_data["labels"] = labels
            if assignees:
                issue_data["assignees"] = assignees

            response = httpx.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers=headers,
                json=issue_data,
                timeout=30.0,
            )
            response.raise_for_status()
            issue = response.json()
            issue_number = issue["number"]
            issue_url = issue["html_url"]

            # Step 2: Get the issue's node ID via GraphQL
            query = """
            query($owner: String!, $repo: String!, $number: Int!) {
                repository(owner: $owner, name: $repo) {
                    issue(number: $number) {
                        id
                    }
                }
            }
            """
            result = graphql_request(query, {"owner": owner, "repo": repo, "number": issue_number})
            issue_node_id = result["repository"]["issue"]["id"]

            # Step 3: Add the issue to the project
            mutation = """
            mutation($projectId: ID!, $contentId: ID!) {
                addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
                    item {
                        id
                    }
                }
            }
            """
            result = graphql_request(mutation, {"projectId": project_id, "contentId": issue_node_id})
            project_item_id = result["addProjectV2ItemById"]["item"]["id"]

            return {
                "issue_number": issue_number,
                "issue_url": issue_url,
                "issue_node_id": issue_node_id,
                "project_item_id": project_item_id,
                "message": f"Created issue #{issue_number} and added to project",
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub API error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def github_project_items(
        org: str,
        project_number: int,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        List project items with minimal output to save context tokens.

        Unlike the verbose GitHub MCP projects_list, this returns only essential data:
        - item_id, title, status, type (issue/pr), issue_number

        Args:
            org: Organization or user login
            project_number: Project number (e.g., 1)
            status: Optional filter by status name (e.g., 'Todo', 'In Progress', 'Done')
            limit: Max items to return (default 50)

        Returns:
            Lean list of project items
        """
        try:
            query = """
            query($org: String!, $number: Int!, $first: Int!) {
                organization(login: $org) {
                    projectV2(number: $number) {
                        id
                        title
                        items(first: $first) {
                            nodes {
                                id
                                fieldValueByName(name: "Status") {
                                    ... on ProjectV2ItemFieldSingleSelectValue {
                                        name
                                    }
                                }
                                content {
                                    ... on Issue {
                                        number
                                        title
                                        state
                                    }
                                    ... on PullRequest {
                                        number
                                        title
                                        state
                                    }
                                    ... on DraftIssue {
                                        title
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """

            result = graphql_request(query, {"org": org, "number": project_number, "first": min(limit, 100)})

            project = result.get("organization", {}).get("projectV2")
            if not project:
                # Try as user instead of org
                user_query = query.replace("organization(login: $org)", "user(login: $org)")
                result = graphql_request(user_query, {"org": org, "number": project_number, "first": min(limit, 100)})
                project = result.get("user", {}).get("projectV2")

            if not project:
                return {"error": f"Project #{project_number} not found for {org}"}

            items = []
            for node in project["items"]["nodes"]:
                content = node.get("content") or {}
                status_field = node.get("fieldValueByName") or {}
                item_status = status_field.get("name", "No Status")

                # Filter by status if specified
                if status and item_status.lower() != status.lower():
                    continue

                # Determine item type
                item_type = "draft"
                if "state" in content:
                    item_type = "issue" if content.get("number") else "pr"

                items.append({
                    "item_id": node["id"],
                    "number": content.get("number"),
                    "title": content.get("title", "Untitled"),
                    "status": item_status,
                    "state": content.get("state", "DRAFT"),
                    "type": item_type,
                })

            return {
                "project_id": project["id"],
                "project_title": project["title"],
                "count": len(items),
                "items": items,
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def github_pr_create(
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: Optional[str] = None,
        issue: Optional[int] = None,
        close_issue: bool = True,
        draft: bool = False,
        add_to_project: bool = True,
    ) -> dict:
        """
        Create a pull request with smart issue linking.

        Automatically adds 'Closes #X' to the PR body and optionally adds the PR
        to the same GitHub Project as the linked issue.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Branch containing changes
            base: Branch to merge into (default: main)
            body: PR description (issue link will be appended)
            issue: Issue number to link (uses 'Closes' or 'Relates to')
            close_issue: Use 'Closes' (True) vs 'Relates to' (False) for issue link
            draft: Create as draft PR (default: False)
            add_to_project: Add PR to same project as linked issue (default: True)

        Returns:
            PR details including number, url, and project info if linked
        """
        if not GITHUB_TOKEN:
            return {"error": "GITHUB_TOKEN environment variable not set"}

        try:
            # Build PR body with issue link
            pr_body = body or ""
            if issue:
                link_text = "Closes" if close_issue else "Relates to"
                issue_section = f"\n\n## Linked Issues\n{link_text} #{issue}"
                pr_body = pr_body + issue_section

            pr_body += "\n\n---\n*Created with [taskr](https://github.com/rhea-impact/taskr)*"

            # Create the PR via REST API
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            pr_data = {
                "title": title,
                "head": head,
                "base": base,
                "body": pr_body,
                "draft": draft,
            }

            response = httpx.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers=headers,
                json=pr_data,
                timeout=30.0,
            )
            response.raise_for_status()
            pr = response.json()
            pr_number = pr["number"]
            pr_url = pr["html_url"]

            result = {
                "pr_number": pr_number,
                "pr_url": pr_url,
                "linked_issue": issue,
                "message": f"Created PR #{pr_number}",
            }

            # If issue specified and add_to_project, find the issue's project and add PR
            if issue and add_to_project:
                try:
                    # Get PR node ID
                    pr_query = """
                    query($owner: String!, $repo: String!, $number: Int!) {
                        repository(owner: $owner, name: $repo) {
                            pullRequest(number: $number) {
                                id
                            }
                        }
                    }
                    """
                    pr_result = graphql_request(pr_query, {"owner": owner, "repo": repo, "number": pr_number})
                    pr_node_id = pr_result["repository"]["pullRequest"]["id"]

                    # Get issue's project items
                    issue_query = """
                    query($owner: String!, $repo: String!, $number: Int!) {
                        repository(owner: $owner, name: $repo) {
                            issue(number: $number) {
                                projectItems(first: 1) {
                                    nodes {
                                        project {
                                            id
                                            title
                                        }
                                    }
                                }
                            }
                        }
                    }
                    """
                    issue_result = graphql_request(issue_query, {"owner": owner, "repo": repo, "number": issue})
                    project_items = issue_result["repository"]["issue"]["projectItems"]["nodes"]

                    if project_items:
                        project_id = project_items[0]["project"]["id"]
                        project_title = project_items[0]["project"]["title"]

                        # Add PR to the project
                        add_mutation = """
                        mutation($projectId: ID!, $contentId: ID!) {
                            addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
                                item { id }
                            }
                        }
                        """
                        graphql_request(add_mutation, {"projectId": project_id, "contentId": pr_node_id})
                        result["added_to_project"] = project_title
                        result["message"] += f" and added to project '{project_title}'"

                except Exception as e:
                    result["project_warning"] = f"Could not add to project: {str(e)}"

            return result

        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub API error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}
