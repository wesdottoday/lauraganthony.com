#!/usr/bin/env python3
"""
Pull Request Helper for Claude Code Integration

This script helps create pull requests in Gitea repositories using Maya's credentials.
It's designed to be called by Claude Code after making commits on feature branches.

Usage:
    python pr-helper.py create --title "PR Title" --description "PR description" --base main --head feature-branch
    python pr-helper.py list --repo repo-name
"""

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request
import urllib.parse


class PullRequestHelper:
    """Helper for creating and managing pull requests via Gitea API."""
    
    def __init__(self, project_root: str = None):
        """Initialize PR helper with project configuration.
        
        Args:
            project_root: Path to project root. If None, uses current directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.config_file = self.project_root / ".claude-code-config.json"
        self.env_file = self.project_root / ".projects" / ".env"
        
        # Load configuration
        self.config = self._load_config()
        self.env_vars = self._load_env()
        
        # Setup API configuration
        self.api_base = self.config.get("gitea", {}).get("api_base_url", "https://git.y37.space/api/v1")
        self.api_token = self.config.get("gitea", {}).get("api_token") or self.env_vars.get("MAYA_GITEA_API_KEY")
        self.default_assignee = self.config.get("gitea", {}).get("default_assignee", "wk")
        self.organization = self.config.get("gitea", {}).get("organization", "y37.space")
        
        if not self.api_token:
            raise ValueError("No Gitea API token found in config or environment")
    
    def _load_config(self) -> Dict:
        """Load Claude Code configuration."""
        if not self.config_file.exists():
            return {}
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config file: {e}")
            return {}
    
    def _load_env(self) -> Dict:
        """Load environment variables from .env file."""
        env_vars = {}
        if not self.env_file.exists():
            return env_vars
        
        try:
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip('"\'')
                        env_vars[key] = value
        except IOError as e:
            print(f"Warning: Could not load .env file: {e}")
        
        return env_vars
    
    def _get_current_repo_info(self) -> tuple:
        """Get current repository name and organization from git remote."""
        try:
            # Get the remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            
            # Parse the URL to extract org/repo
            if remote_url.startswith("git@"):
                # SSH format: git@git.y37.space:y37.space/repo-name.git
                parts = remote_url.split(":")[-1].replace(".git", "").split("/")
                if len(parts) >= 2:
                    return parts[0], parts[1]
            elif remote_url.startswith("https://"):
                # HTTPS format: https://git.y37.space/y37.space/repo-name.git
                parts = remote_url.replace("https://", "").replace(".git", "").split("/")
                if len(parts) >= 3:
                    return parts[1], parts[2]
            
            raise ValueError(f"Could not parse remote URL: {remote_url}")
            
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Could not get git remote: {e}")
    
    def _get_current_branch(self) -> str:
        """Get the current git branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Could not get current branch: {e}")
    
    def _make_api_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Make an API request to Gitea.
        
        Args:
            endpoint: API endpoint (without base URL)
            method: HTTP method
            data: JSON data for POST/PUT requests
            
        Returns:
            Response data as dictionary
        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        
        # Prepare request
        headers = {
            "Authorization": f"token {self.api_token}",
            "Content-Type": "application/json"
        }
        
        # Prepare data
        request_data = None
        if data:
            request_data = json.dumps(data).encode('utf-8')
        
        # Create request
        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req) as response:
                response_data = response.read().decode('utf-8')
                if response_data:
                    return json.loads(response_data)
                return {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_data = json.loads(error_body)
                error_msg = error_data.get('message', error_body)
            except json.JSONDecodeError:
                error_msg = error_body
            raise ValueError(f"API request failed ({e.code}): {error_msg}")
        except Exception as e:
            raise ValueError(f"API request failed: {e}")
    
    def _enhance_pr_description(self, description: str, head: str, org: str, repo: str, 
                               auto_link: bool) -> str:
        """Enhance PR description with automatic linking and context.
        
        Args:
            description: Original description
            head: Head branch name
            org: Organization name
            repo: Repository name
            auto_link: Whether to add automatic linking
            
        Returns:
            Enhanced description with automatic links and context
        """
        enhanced_lines = []
        
        # Add original description
        if description:
            enhanced_lines.append(description)
            enhanced_lines.append("")
        
        # Add commit information
        try:
            commit_info = self._get_commit_info(head)
            if commit_info:
                enhanced_lines.append("## Commits")
                enhanced_lines.extend(commit_info)
                enhanced_lines.append("")
        except Exception:
            # Don't fail if we can't get commit info
            pass
        
        # Add automatic issue linking if enabled
        if auto_link:
            issue_links = self._detect_related_issues(description, head)
            if issue_links:
                enhanced_lines.append("## Related Issues")
                enhanced_lines.extend(issue_links)
                enhanced_lines.append("")
        
        # Add checklist for reviewer
        enhanced_lines.extend([
            "## Review Checklist",
            "- [ ] Code follows project standards",
            "- [ ] Tests pass and coverage is adequate", 
            "- [ ] Documentation is updated",
            "- [ ] Changes are backward compatible",
            "",
            "---",
            f"**Branch:** [{head}](https://git.y37.space/{org}/{repo}/src/branch/{head})",
            f"**Ready for review** - @wk please review when ready",
            "",
            "*Created by Claude Code pr-helper.py*"
        ])
        
        return "\n".join(enhanced_lines)
    
    def _get_commit_info(self, branch: str) -> List[str]:
        """Get commit information for the branch.
        
        Args:
            branch: Branch name
            
        Returns:
            List of commit info strings
        """
        try:
            # Get commits that are in this branch but not in main
            result = subprocess.run([
                "git", "log", "--oneline", "--no-merges", 
                f"main..{branch}"
            ], capture_output=True, text=True, check=True)
            
            commits = result.stdout.strip().split('\n')
            if not commits or not commits[0]:
                return []
            
            commit_lines = []
            for commit in commits[:5]:  # Limit to 5 most recent commits
                if commit.strip():
                    commit_lines.append(f"- {commit}")
            
            if len(commits) > 5:
                commit_lines.append(f"- ... and {len(commits) - 5} more commits")
            
            return commit_lines
        except Exception:
            return []
    
    def _detect_related_issues(self, description: str, branch: str) -> List[str]:
        """Detect related issues from description and branch name.
        
        Args:
            description: PR description
            branch: Branch name
            
        Returns:
            List of issue link strings
        """
        import re
        
        links = []
        text_to_search = f"{description} {branch}"
        
        # Look for issue patterns in description and branch name
        patterns = [
            r'#(\d+)',           # #123
            r'issue[:\s]+(\d+)', # issue: 123, issue 123
            r'bug[:\s]+(\d+)',   # bug: 123, bug 123
            r'task[:\s]+(\d+)',  # task: 123, task 123
            r'fix[:\s]+(\d+)',   # fix: 123, fix 123
        ]
        
        found_issues = set()
        for pattern in patterns:
            matches = re.findall(pattern, text_to_search, re.IGNORECASE)
            found_issues.update(matches)
        
        # Convert to linking format
        for issue_num in sorted(found_issues, key=int):
            links.append(f"- Addresses #{issue_num}")
        
        # Add generic linking if branch suggests task/bug work
        if not links:
            if 'task' in branch.lower():
                links.append("- Related to task implementation")
            elif 'bug' in branch.lower() or 'fix' in branch.lower():
                links.append("- Bug fix implementation")
            elif 'feature' in branch.lower():
                links.append("- New feature implementation")
        
        return links
    
    def generate_branch_link(self, branch_name: str, org: str = None, repo: str = None) -> str:
        """Generate a linked branch reference for use in comments.
        
        Args:
            branch_name: Name of the branch
            org: Organization name. If None, uses default
            repo: Repository name. If None, detects from git remote
            
        Returns:
            Markdown-formatted linked branch reference
        """
        if not org:
            org = self.organization
        if not repo:
            try:
                detected_org, detected_repo = self._get_current_repo_info()
                repo = detected_repo
                if not org or org == "auto":
                    org = detected_org
            except Exception:
                # Fallback if we can't detect
                org = "y37.space"
                repo = "project-template"
        
        return f"[{branch_name}](https://git.y37.space/{org}/{repo}/src/branch/{branch_name})"
    
    def _add_assignee_notification(self, pr_number: int, assignee: str, org: str, repo: str) -> None:
        """Add a notification comment for the assignee.
        
        Args:
            pr_number: PR number
            assignee: Assignee username
            org: Organization name
            repo: Repository name
        """
        try:
            comment_body = f"""@{assignee} This PR is ready for your review.

**Summary:** All commits have been made and the implementation is complete.

**Next Steps:**
1. Review the code changes
2. Test the functionality
3. Approve and merge when ready

Please let me know if you need any clarification or have feedback!"""

            endpoint = f"repos/{org}/{repo}/issues/{pr_number}/comments"
            self._make_api_request(endpoint, "POST", {"body": comment_body})
            print(f"Added notification comment for @{assignee}")
        except Exception as e:
            print(f"Warning: Could not add notification comment: {e}")
    
    def create_pull_request(self, title: str, description: str = "", 
                          base: str = "main", head: str = None,
                          assignee: str = None, repo: str = None, 
                          org: str = None, auto_link_issues: bool = True,
                          notify_assignee: bool = True) -> Dict:
        """Create a pull request.
        
        Args:
            title: PR title
            description: PR description
            base: Base branch (target)
            head: Head branch (source). If None, uses current branch
            assignee: Assignee username. If None, uses default
            repo: Repository name. If None, detects from git remote
            org: Organization name. If None, uses default
            auto_link_issues: Auto-detect and link related issues
            notify_assignee: Add assignee notification comment
            
        Returns:
            Created PR data
        """
        # Use defaults if not provided
        if not head:
            head = self._get_current_branch()
        if not assignee:
            assignee = self.default_assignee
        if not org:
            org = self.organization
        if not repo:
            detected_org, detected_repo = self._get_current_repo_info()
            repo = detected_repo
            if not org or org == "auto":
                org = detected_org
        
        # Validate that head branch is not the same as base
        if head == base:
            raise ValueError(f"Head branch '{head}' cannot be the same as base branch '{base}'")
        
        # Enhance description with automatic linking if requested
        enhanced_description = self._enhance_pr_description(
            description, head, org, repo, auto_link_issues
        )
        
        # Create PR data
        pr_data = {
            "title": title,
            "body": enhanced_description,
            "base": base,
            "head": head,
            "assignee": assignee
        }
        
        # Create the PR
        endpoint = f"repos/{org}/{repo}/pulls"
        result = self._make_api_request(endpoint, "POST", pr_data)
        
        # Add assignee notification comment if requested
        if notify_assignee and assignee and result.get('number'):
            self._add_assignee_notification(result['number'], assignee, org, repo)
        
        print(f"Created PR #{result.get('number')}: {title}")
        print(f"URL: {result.get('html_url')}")
        print(f"Assigned to: @{assignee}")
        
        return result
    
    def list_pull_requests(self, repo: str = None, org: str = None, state: str = "open") -> List[Dict]:
        """List pull requests for a repository.
        
        Args:
            repo: Repository name. If None, detects from git remote
            org: Organization name. If None, uses default
            state: PR state (open, closed, all)
            
        Returns:
            List of PR data
        """
        if not org:
            org = self.organization
        if not repo:
            detected_org, detected_repo = self._get_current_repo_info()
            repo = detected_repo
            if not org or org == "auto":
                org = detected_org
        
        endpoint = f"repos/{org}/{repo}/pulls?state={state}"
        return self._make_api_request(endpoint)
    
    def get_pull_request(self, pr_number: int, repo: str = None, org: str = None) -> Dict:
        """Get details of a specific pull request.
        
        Args:
            pr_number: PR number
            repo: Repository name. If None, detects from git remote
            org: Organization name. If None, uses default
            
        Returns:
            PR data
        """
        if not org:
            org = self.organization
        if not repo:
            detected_org, detected_repo = self._get_current_repo_info()
            repo = detected_repo
            if not org or org == "auto":
                org = detected_org
        
        endpoint = f"repos/{org}/{repo}/pulls/{pr_number}"
        return self._make_api_request(endpoint)
    
    def close_pull_request(self, pr_number: int, repo: str = None, org: str = None) -> Dict:
        """Close a pull request.
        
        Args:
            pr_number: PR number
            repo: Repository name. If None, detects from git remote
            org: Organization name. If None, uses default
            
        Returns:
            Updated PR data
        """
        if not org:
            org = self.organization
        if not repo:
            detected_org, detected_repo = self._get_current_repo_info()
            repo = detected_repo
            if not org or org == "auto":
                org = detected_org
        
        endpoint = f"repos/{org}/{repo}/pulls/{pr_number}"
        data = {"state": "closed"}
        return self._make_api_request(endpoint, "PATCH", data)


def main():
    """Main entry point for the PR helper tool."""
    parser = argparse.ArgumentParser(
        description="Create and manage pull requests via Gitea API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create PR from current branch to main
    python pr-helper.py create --title "Add new feature" --description "This PR adds feature X"
    
    # Create PR with specific branches
    python pr-helper.py create --title "Bug fix" --base main --head feature-branch
    
    # List open PRs
    python pr-helper.py list
    
    # List all PRs
    python pr-helper.py list --state all
    
    # Get specific PR details
    python pr-helper.py get --pr-number 5
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create PR command
    create_parser = subparsers.add_parser("create", help="Create a new pull request")
    create_parser.add_argument("--title", required=True, help="PR title")
    create_parser.add_argument("--description", default="", help="PR description")
    create_parser.add_argument("--base", default="main", help="Base branch (target)")
    create_parser.add_argument("--head", help="Head branch (source). Default: current branch")
    create_parser.add_argument("--assignee", help="Assignee username. Default: from config")
    create_parser.add_argument("--repo", help="Repository name. Default: auto-detect")
    create_parser.add_argument("--org", help="Organization name. Default: from config")
    create_parser.add_argument("--no-auto-link", action="store_true", help="Disable automatic issue linking")
    create_parser.add_argument("--no-notify", action="store_true", help="Disable assignee notification")
    
    # List PRs command
    list_parser = subparsers.add_parser("list", help="List pull requests")
    list_parser.add_argument("--repo", help="Repository name. Default: auto-detect")
    list_parser.add_argument("--org", help="Organization name. Default: from config")
    list_parser.add_argument("--state", default="open", choices=["open", "closed", "all"], help="PR state")
    
    # Get PR command
    get_parser = subparsers.add_parser("get", help="Get pull request details")
    get_parser.add_argument("--pr-number", type=int, required=True, help="PR number")
    get_parser.add_argument("--repo", help="Repository name. Default: auto-detect")
    get_parser.add_argument("--org", help="Organization name. Default: from config")
    
    # Close PR command
    close_parser = subparsers.add_parser("close", help="Close a pull request")
    close_parser.add_argument("--pr-number", type=int, required=True, help="PR number")
    close_parser.add_argument("--repo", help="Repository name. Default: auto-detect")
    close_parser.add_argument("--org", help="Organization name. Default: from config")
    
    # Generate branch link command
    link_parser = subparsers.add_parser("branch-link", help="Generate linked branch reference")
    link_parser.add_argument("--branch", help="Branch name. Default: current branch")
    link_parser.add_argument("--repo", help="Repository name. Default: auto-detect")
    link_parser.add_argument("--org", help="Organization name. Default: from config")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize helper
    try:
        helper = PullRequestHelper()
    except Exception as e:
        print(f"Error initializing PR helper: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        if args.command == "create":
            result = helper.create_pull_request(
                title=args.title,
                description=args.description,
                base=args.base,
                head=args.head,
                assignee=args.assignee,
                repo=args.repo,
                org=args.org,
                auto_link_issues=not args.no_auto_link,
                notify_assignee=not args.no_notify
            )
        
        elif args.command == "list":
            prs = helper.list_pull_requests(
                repo=args.repo,
                org=args.org,
                state=args.state
            )
            if prs:
                print(f"Pull Requests ({args.state}):")
                for pr in prs:
                    print(f"  #{pr['number']}: {pr['title']} ({pr['state']})")
                    print(f"    {pr['html_url']}")
            else:
                print(f"No {args.state} pull requests found")
        
        elif args.command == "get":
            pr = helper.get_pull_request(
                pr_number=args.pr_number,
                repo=args.repo,
                org=args.org
            )
            print(f"PR #{pr['number']}: {pr['title']}")
            print(f"State: {pr['state']}")
            print(f"Base: {pr['base']['ref']} ← Head: {pr['head']['ref']}")
            print(f"URL: {pr['html_url']}")
            if pr.get('body'):
                print(f"Description: {pr['body']}")
        
        elif args.command == "close":
            result = helper.close_pull_request(
                pr_number=args.pr_number,
                repo=args.repo,
                org=args.org
            )
            print(f"Closed PR #{result['number']}: {result['title']}")
        
        elif args.command == "branch-link":
            branch = args.branch
            if not branch:
                branch = helper._get_current_branch()
            
            link = helper.generate_branch_link(
                branch_name=branch,
                org=args.org,
                repo=args.repo
            )
            print(link)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()