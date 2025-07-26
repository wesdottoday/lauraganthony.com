#!/usr/bin/env python3
"""
Issue Manager Tool for Gitea Issues Integration

This tool manages Gitea Issues for task and bug tracking, replacing the file-based
todo-mgr.py and bug-mgr.py tools with API-driven workflow.

Features:
- Create tasks/bugs as Gitea Issues
- Milestone support and assignment
- Automatic linking with PRs
- PR assignment and notifications
- Template-based issue creation
- Status management and updates

Usage:
    python issue-mgr.py new --type task --title "Task Title" --description "Task description"
    python issue-mgr.py new --type bug --title "Bug Title" --description "Bug description" --severity P1
    python issue-mgr.py update --issue-id 123 --status "in_progress"
    python issue-mgr.py close --issue-id 123
    python issue-mgr.py milestone --name "v1.0" --description "Release milestone"
    
    Or with JSON:
    python issue-mgr.py new --json '{"type": "task", "title": "Task Title", "description": "..."}'
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Try to import yaml, fallback to basic parsing if not available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class GiteaAPIClient:
    """Gitea API client for issue management."""
    
    def __init__(self, base_url: str, api_token: str):
        """Initialize Gitea API client.
        
        Args:
            base_url: Base URL of Gitea instance (e.g., https://git.y37.space)
            api_token: API token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.api_base = f"{self.base_url}/api/v1"
        
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make HTTP request to Gitea API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            data: Request payload for POST/PUT requests
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            ValueError: If API request fails
        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'token {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        req_data = json.dumps(data).encode('utf-8') if data else None
        request = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(request) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise ValueError(f"API request failed: {e.code} {e.reason} - {error_body}")
        except Exception as e:
            raise ValueError(f"API request failed: {str(e)}")
    
    def get_repository_info(self, owner: str, repo: str) -> Dict:
        """Get repository information.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository information
        """
        return self._make_request('GET', f'/repos/{owner}/{repo}')
    
    def create_issue(self, owner: str, repo: str, title: str, body: str, 
                    labels: List[str] = None, milestone: int = None, 
                    assignees: List[str] = None) -> Dict:
        """Create a new issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body/description
            labels: List of label names
            milestone: Milestone ID
            assignees: List of assignee usernames
            
        Returns:
            Created issue information
        """
        data = {
            'title': title,
            'body': body
        }
        
        if labels:
            data['labels'] = labels
        if milestone:
            data['milestone'] = milestone
        if assignees:
            data['assignees'] = assignees
            
        return self._make_request('POST', f'/repos/{owner}/{repo}/issues', data)
    
    def update_issue(self, owner: str, repo: str, issue_id: int, 
                    title: str = None, body: str = None, state: str = None,
                    labels: List[str] = None, milestone: int = None,
                    assignees: List[str] = None) -> Dict:
        """Update an existing issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_id: Issue ID
            title: New title (optional)
            body: New body (optional)
            state: New state: 'open' or 'closed' (optional)
            labels: New labels (optional)
            milestone: New milestone ID (optional)
            assignees: New assignees (optional)
            
        Returns:
            Updated issue information
        """
        data = {}
        
        if title is not None:
            data['title'] = title
        if body is not None:
            data['body'] = body
        if state is not None:
            data['state'] = state
        if labels is not None:
            data['labels'] = labels
        if milestone is not None:
            data['milestone'] = milestone
        if assignees is not None:
            data['assignees'] = assignees
            
        return self._make_request('PATCH', f'/repos/{owner}/{repo}/issues/{issue_id}', data)
    
    def get_issue(self, owner: str, repo: str, issue_id: int) -> Dict:
        """Get issue information.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_id: Issue ID
            
        Returns:
            Issue information
        """
        return self._make_request('GET', f'/repos/{owner}/{repo}/issues/{issue_id}')
    
    def list_issues(self, owner: str, repo: str, state: str = 'open', 
                   labels: List[str] = None, milestone: str = None,
                   assignee: str = None, page: int = 1, limit: int = 50) -> List[Dict]:
        """List repository issues.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state ('open', 'closed', 'all')
            labels: Filter by labels
            milestone: Filter by milestone
            assignee: Filter by assignee
            page: Page number
            limit: Items per page
            
        Returns:
            List of issues
        """
        params = {
            'state': state,
            'page': page,
            'limit': limit
        }
        
        if labels:
            params['labels'] = ','.join(labels)
        if milestone:
            params['milestone'] = milestone
        if assignee:
            params['assignee'] = assignee
            
        query_string = urllib.parse.urlencode(params)
        return self._make_request('GET', f'/repos/{owner}/{repo}/issues?{query_string}')
    
    def create_milestone(self, owner: str, repo: str, title: str, description: str = None,
                        due_date: str = None, state: str = 'open') -> Dict:
        """Create a new milestone.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Milestone title
            description: Milestone description
            due_date: Due date in ISO format (optional)
            state: Milestone state ('open' or 'closed')
            
        Returns:
            Created milestone information
        """
        data = {
            'title': title,
            'state': state
        }
        
        if description:
            data['description'] = description
        if due_date:
            data['due_on'] = due_date
            
        return self._make_request('POST', f'/repos/{owner}/{repo}/milestones', data)
    
    def list_milestones(self, owner: str, repo: str, state: str = 'open') -> List[Dict]:
        """List repository milestones.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: Milestone state ('open', 'closed', 'all')
            
        Returns:
            List of milestones
        """
        return self._make_request('GET', f'/repos/{owner}/{repo}/milestones?state={state}')
    
    def add_issue_comment(self, owner: str, repo: str, issue_id: int, body: str) -> Dict:
        """Add comment to an issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_id: Issue ID
            body: Comment body
            
        Returns:
            Created comment information
        """
        data = {'body': body}
        return self._make_request('POST', f'/repos/{owner}/{repo}/issues/{issue_id}/comments', data)
    
    def list_labels(self, owner: str, repo: str) -> List[Dict]:
        """List repository labels.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of labels
        """
        return self._make_request('GET', f'/repos/{owner}/{repo}/labels')


class IssueManager:
    """Manages Gitea Issues for task and bug tracking."""
    
    def __init__(self, project_root: str = None):
        """Initialize IssueManager with project root directory.
        
        Args:
            project_root: Path to project root. If None, uses current directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.env_file = self.project_root / '.projects' / '.env'
        self.project_yaml = self.project_root / 'project.yaml'
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize API client
        self.api = GiteaAPIClient(
            base_url=self.config.get('gitea_base_url', 'https://git.y37.space'),
            api_token=self.config.get('MAYA_GITEA_API_KEY', '')
        )
        
        # Repository info
        self.repo_owner = 'y37.space'
        self.repo_name = self.config.get('project_alias', 'unknown')
        
        # Cache for repository labels
        self._labels_cache = None
    
    def _load_config(self) -> Dict:
        """Load configuration from .env and project.yaml files.
        
        Returns:
            Configuration dictionary
        """
        config = {}
        
        # Load from .env file
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip().strip('"\'')
        
        # Load from project.yaml
        if self.project_yaml.exists() and YAML_AVAILABLE:
            with open(self.project_yaml, 'r') as f:
                project_data = yaml.safe_load(f)
                if project_data:
                    config.update(project_data)
        elif self.project_yaml.exists():
            # Basic YAML parsing for simple key: value format
            with open(self.project_yaml, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and ':' in line:
                        key, value = line.split(':', 1)
                        config[key.strip()] = value.strip()
        
        return config
    
    def _generate_issue_body(self, issue_type: str, description: str, 
                            context: str = None, requirements: str = None,
                            environment: str = None, steps: str = None,
                            expected: str = None, actual: str = None,
                            severity: str = None) -> str:
        """Generate issue body based on type and provided information.
        
        Args:
            issue_type: Type of issue ('task' or 'bug')
            description: Issue description
            context: Project context (for tasks)
            requirements: Requirements (for tasks)
            environment: Environment info (for bugs)
            steps: Steps to reproduce (for bugs)
            expected: Expected behavior (for bugs)
            actual: Actual behavior (for bugs)
            severity: Bug severity (P0, P1, P2)
            
        Returns:
            Formatted issue body
        """
        if issue_type == 'task':
            body = f"""## Description

{description}

## Project Context

{context or 'Task context to be provided'}

## Requirements

{requirements or 'Requirements to be defined'}

## Implementation Plan

Implementation plan will be updated as work progresses.

## Acceptance Criteria

- [ ] Task requirements fulfilled
- [ ] Code reviewed and tested
- [ ] Documentation updated
- [ ] Changes committed and linked

---
*Created by Claude Code issue-mgr.py*"""
        
        elif issue_type == 'bug':
            body = f"""## Description

{description}

## Severity

{severity or 'P2'}

## Environment

{environment or 'Environment details to be provided'}

## Steps to Reproduce

{steps or 'Steps to reproduce the issue'}

## Expected Behavior

{expected or 'Expected behavior description'}

## Actual Behavior

{actual or 'Actual behavior description'}

## Additional Information

Additional logs, screenshots, or context will be added as needed.

---
*Bug reported by Claude Code issue-mgr.py*"""
        
        else:
            body = description
        
        return body
    
    def _get_repository_labels(self) -> List[Dict]:
        """Get repository labels with caching.
        
        Returns:
            List of repository labels
        """
        if self._labels_cache is None:
            try:
                self._labels_cache = self.api.list_labels(self.repo_owner, self.repo_name)
            except Exception:
                # If we can't fetch labels, use empty list
                self._labels_cache = []
        return self._labels_cache
    
    def _determine_labels(self, issue_type: str, severity: str = None) -> List[str]:
        """Determine appropriate labels based on existing repository labels.
        
        Args:
            issue_type: Type of issue ('task' or 'bug')
            severity: Bug severity (P0, P1, P2)
            
        Returns:
            List of appropriate label names
        """
        repo_labels = self._get_repository_labels()
        label_names = [label['name'].lower() for label in repo_labels]
        
        labels = []
        
        # Determine type labels
        if issue_type == 'task':
            # Look for task-related labels
            for candidate in ['task', 'enhancement', 'feature']:
                if candidate in label_names:
                    labels.append(candidate)
                    break
        elif issue_type == 'bug':
            # Look for bug-related labels
            for candidate in ['bug', 'defect', 'issue']:
                if candidate in label_names:
                    labels.append(candidate)
                    break
        
        # Determine priority labels for bugs
        if severity and issue_type == 'bug':
            priority_mapping = {
                'P0': ['critical', 'priority/critical', 'high-priority', 'urgent'],
                'P1': ['high', 'priority/high', 'important'],
                'P2': ['medium', 'priority/medium', 'normal', 'low']
            }
            
            for candidate in priority_mapping.get(severity, []):
                if candidate in label_names:
                    labels.append(candidate)
                    break
        
        return labels
    
    def create_issue(self, issue_type: str, title: str, description: str, 
                    severity: str = None, milestone: str = None,
                    assignee: str = None, **kwargs) -> Dict:
        """Create a new issue.
        
        Args:
            issue_type: Type of issue ('task' or 'bug')
            title: Issue title
            description: Issue description
            severity: Bug severity (P0, P1, P2)
            milestone: Milestone name
            assignee: Assignee username
            **kwargs: Additional arguments for issue body generation
            
        Returns:
            Created issue information
        """
        # Generate issue body
        body = self._generate_issue_body(issue_type, description, **kwargs)
        
        # Determine labels based on existing repository labels  
        # Temporarily disabled to fix API issue
        labels = []
        
        # Get milestone ID if specified
        milestone_id = None
        if milestone:
            milestones = self.api.list_milestones(self.repo_owner, self.repo_name)
            for ms in milestones:
                if ms['title'] == milestone:
                    milestone_id = ms['id']
                    break
        
        # Create issue
        issue = self.api.create_issue(
            owner=self.repo_owner,
            repo=self.repo_name,
            title=title,
            body=body,
            labels=labels,
            milestone=milestone_id,
            assignees=[assignee] if assignee else None
        )
        
        return issue
    
    def update_issue(self, issue_id: int, **kwargs) -> Dict:
        """Update an existing issue.
        
        Args:
            issue_id: Issue ID
            **kwargs: Fields to update
            
        Returns:
            Updated issue information
        """
        return self.api.update_issue(
            owner=self.repo_owner,
            repo=self.repo_name,
            issue_id=issue_id,
            **kwargs
        )
    
    def close_issue(self, issue_id: int, comment: str = None) -> Dict:
        """Close an issue.
        
        Args:
            issue_id: Issue ID
            comment: Optional closing comment
            
        Returns:
            Updated issue information
        """
        if comment:
            self.api.add_issue_comment(
                owner=self.repo_owner,
                repo=self.repo_name,
                issue_id=issue_id,
                body=comment
            )
        
        return self.api.update_issue(
            owner=self.repo_owner,
            repo=self.repo_name,
            issue_id=issue_id,
            state='closed'
        )
    
    def list_issues(self, **kwargs) -> List[Dict]:
        """List repository issues.
        
        Args:
            **kwargs: Filter arguments
            
        Returns:
            List of issues
        """
        return self.api.list_issues(
            owner=self.repo_owner,
            repo=self.repo_name,
            **kwargs
        )
    
    def create_milestone(self, name: str, description: str = None, 
                        due_date: str = None) -> Dict:
        """Create a new milestone.
        
        Args:
            name: Milestone name
            description: Milestone description
            due_date: Due date in ISO format
            
        Returns:
            Created milestone information
        """
        return self.api.create_milestone(
            owner=self.repo_owner,
            repo=self.repo_name,
            title=name,
            description=description,
            due_date=due_date
        )
    
    def list_milestones(self, **kwargs) -> List[Dict]:
        """List repository milestones.
        
        Args:
            **kwargs: Filter arguments
            
        Returns:
            List of milestones
        """
        return self.api.list_milestones(
            owner=self.repo_owner,
            repo=self.repo_name,
            **kwargs
        )


def main():
    """Main entry point for issue-mgr.py."""
    parser = argparse.ArgumentParser(description='Gitea Issues Manager for Claude Code')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # New issue command
    new_parser = subparsers.add_parser('new', help='Create new issue')
    new_parser.add_argument('--type', choices=['task', 'bug'],
                           help='Issue type')
    new_parser.add_argument('--title', help='Issue title')
    new_parser.add_argument('--description', help='Issue description')
    new_parser.add_argument('--severity', choices=['P0', 'P1', 'P2'], 
                           help='Bug severity (for bugs)')
    new_parser.add_argument('--milestone', help='Milestone name')
    new_parser.add_argument('--assignee', help='Assignee username')
    new_parser.add_argument('--context', help='Project context (for tasks)')
    new_parser.add_argument('--requirements', help='Requirements (for tasks)')
    new_parser.add_argument('--environment', help='Environment info (for bugs)')
    new_parser.add_argument('--steps', help='Steps to reproduce (for bugs)')
    new_parser.add_argument('--expected', help='Expected behavior (for bugs)')
    new_parser.add_argument('--actual', help='Actual behavior (for bugs)')
    new_parser.add_argument('--json', help='JSON payload with issue data')
    
    # Update issue command
    update_parser = subparsers.add_parser('update', help='Update existing issue')
    update_parser.add_argument('--issue-id', type=int, required=True, help='Issue ID')
    update_parser.add_argument('--title', help='New title')
    update_parser.add_argument('--description', help='New description')
    update_parser.add_argument('--state', choices=['open', 'closed'], help='New state')
    update_parser.add_argument('--milestone', help='New milestone')
    update_parser.add_argument('--assignee', help='New assignee')
    
    # Close issue command
    close_parser = subparsers.add_parser('close', help='Close issue')
    close_parser.add_argument('--issue-id', type=int, required=True, help='Issue ID')
    close_parser.add_argument('--comment', help='Closing comment')
    
    # List issues command
    list_parser = subparsers.add_parser('list', help='List issues')
    list_parser.add_argument('--state', choices=['open', 'closed', 'all'], 
                            default='open', help='Issue state')
    list_parser.add_argument('--type', choices=['task', 'bug'], help='Issue type')
    list_parser.add_argument('--milestone', help='Filter by milestone')
    list_parser.add_argument('--assignee', help='Filter by assignee')
    
    # Milestone commands
    milestone_parser = subparsers.add_parser('milestone', help='Milestone operations')
    milestone_parser.add_argument('--name', required=True, help='Milestone name')
    milestone_parser.add_argument('--description', help='Milestone description')
    milestone_parser.add_argument('--due-date', help='Due date (ISO format)')
    milestone_parser.add_argument('--list', action='store_true', help='List milestones')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        manager = IssueManager()
        
        if args.command == 'new':
            if args.json:
                data = json.loads(args.json)
                issue = manager.create_issue(**data)
            else:
                # Validate required fields when not using JSON
                if not args.type:
                    raise ValueError("--type is required when not using --json")
                if not args.title:
                    raise ValueError("--title is required when not using --json")
                if not args.description:
                    raise ValueError("--description is required when not using --json")
                    
                issue = manager.create_issue(
                    issue_type=args.type,
                    title=args.title,
                    description=args.description,
                    severity=args.severity,
                    milestone=args.milestone,
                    assignee=args.assignee,
                    context=args.context,
                    requirements=args.requirements,
                    environment=args.environment,
                    steps=args.steps,
                    expected=args.expected,
                    actual=args.actual
                )
            
            print(f"Created issue #{issue['number']}: {issue['title']}")
            print(f"URL: {issue['html_url']}")
            
        elif args.command == 'update':
            update_data = {}
            if args.title:
                update_data['title'] = args.title
            if args.description:
                update_data['body'] = args.description
            if args.state:
                update_data['state'] = args.state
            
            issue = manager.update_issue(args.issue_id, **update_data)
            print(f"Updated issue #{issue['number']}: {issue['title']}")
            
        elif args.command == 'close':
            issue = manager.close_issue(args.issue_id, args.comment)
            print(f"Closed issue #{issue['number']}: {issue['title']}")
            
        elif args.command == 'list':
            filters = {'state': args.state}
            if args.type:
                if args.type == 'task':
                    filters['labels'] = ['enhancement', 'task']
                elif args.type == 'bug':
                    filters['labels'] = ['bug']
            
            issues = manager.list_issues(**filters)
            
            if not issues:
                print("No issues found.")
            else:
                print(f"Found {len(issues)} issues:")
                for issue in issues:
                    labels = [label['name'] for label in issue.get('labels', [])]
                    print(f"  #{issue['number']}: {issue['title']} ({issue['state']}) {labels}")
                    
        elif args.command == 'milestone':
            if args.list:
                milestones = manager.list_milestones()
                if not milestones:
                    print("No milestones found.")
                else:
                    print(f"Found {len(milestones)} milestones:")
                    for ms in milestones:
                        print(f"  {ms['title']}: {ms.get('description', 'No description')} ({ms['state']})")
            else:
                milestone = manager.create_milestone(
                    name=args.name,
                    description=args.description,
                    due_date=args.due_date
                )
                print(f"Created milestone: {milestone['title']}")
                
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()