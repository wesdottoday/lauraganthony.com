#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Initialization Script

This script initializes a new project from the template, handling:
- Interactive project configuration
- Gitea repository creation
- Woodpecker CI integration
- Template file processing
- Git initialization with Maya's SSH keys

Usage:
    python init_project.py [--dry-run]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Optional


class ProjectInitializer:
    """Handles project initialization from template."""
    
    def __init__(self, dry_run: bool = False):
        """Initialize the project initializer.
        
        Args:
            dry_run: If True, show what would be done without making changes
        """
        self.dry_run = dry_run
        self.project_root = Path.cwd()
        self.projects_dir = self.project_root / ".projects"
        self.env_file = self.projects_dir / ".env"
        
        # Load environment variables
        self.env_vars = self._load_env()
        
        # API configuration
        self.gitea_api_key = self.env_vars.get("MAYA_GITEA_API_KEY")
        self.woodpecker_api_key = self.env_vars.get("MAYA_WOODPECKER_API_KEY")
        self.gitea_base_url = "https://git.y37.space"
        self.woodpecker_base_url = "https://ci.y37.space"
        
        if not self.gitea_api_key:
            self._show_permission_guidance("MAYA_GITEA_API_KEY")
            raise ValueError("MAYA_GITEA_API_KEY not found in .projects/.env")
        if not self.woodpecker_api_key:
            self._show_permission_guidance("MAYA_WOODPECKER_API_KEY")
            raise ValueError("MAYA_WOODPECKER_API_KEY not found in .projects/.env")
    
    def _load_env(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        if not self.env_file.exists():
            self._show_permission_guidance("ENV_FILE")
            raise FileNotFoundError(f".env file not found: {self.env_file}")
        
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
            raise ValueError(f"Could not load .env file: {e}")
        
        return env_vars
    
    def _convert_ssh_to_https_url(self, ssh_url: str) -> str:
        """Convert SSH git URL to HTTPS format for web links.
        
        Args:
            ssh_url: SSH format URL like git@git.y37.space:org/repo.git
            
        Returns:
            HTTPS format URL like https://git.y37.space/org/repo
        """
        if ssh_url.startswith('git@'):
            # Extract parts from git@host:org/repo.git format
            parts = ssh_url.replace('git@', '').replace('.git', '')
            if ':' in parts:
                host, path = parts.split(':', 1)
                return f"https://{host}/{path}"
        
        # If it's already HTTPS or doesn't match expected format, return as-is
        return ssh_url
    
    def _print_action(self, action: str, details: str = ""):
        """Print action with dry-run prefix if applicable."""
        prefix = "[DRY RUN] " if self.dry_run else ""
        print(f"{prefix}{action}")
        if details:
            print(f"  {details}")
    
    def _show_permission_guidance(self, missing_item: str) -> None:
        """Show targeted permission guidance based on missing item."""
        print("\n" + "=" * 60)
        print("🔧 PERMISSION SETUP REQUIRED")
        print("=" * 60)
        
        print("The project template system requires proper API tokens and SSH key configuration.")
        print("Use the automated permission coaching system for guided setup.")
        print()
        
        if missing_item == "ENV_FILE":
            print("📋 Missing .env configuration file")
            print("This file contains your API tokens and is required for automation.")
            
        elif missing_item == "MAYA_GITEA_API_KEY":
            print("🔑 Missing Gitea API token")
            print("Required for repository management, issues, and pull requests.")
            
        elif missing_item == "MAYA_WOODPECKER_API_KEY":
            print("🚁 Missing Woodpecker CI token")
            print("Required for automated build and deployment setup.")
        
        print()
        print("🚀 AUTOMATED SETUP (Recommended):")
        print("   python .projects/tools/permission-coach.py guide")
        print()
        print("🔍 VALIDATE EXISTING SETUP:")
        print("   python .projects/tools/permission-coach.py validate")
        print()
        print("🔧 TROUBLESHOOTING HELP:")
        print("   python .projects/tools/permission-coach.py troubleshoot")
        print()
        print("📋 VIEW EXAMPLES:")
        print("   python .projects/tools/permission-coach.py examples")
        print()
        
        # Offer to run the guided setup automatically
        try:
            response = input("Run automated setup now? (y/n): ").strip().lower()
            if response in ['y', 'yes', 'true', '1']:
                print("\n🚀 Starting automated permission setup...")
                import subprocess
                result = subprocess.run([
                    sys.executable, 
                    str(self.projects_dir / "tools" / "permission-coach.py"), 
                    "guide"
                ])
                if result.returncode == 0:
                    print("\n✅ Setup completed! Please re-run the initialization script.")
                else:
                    print("\n❌ Setup failed. Please check the errors above.")
                sys.exit(result.returncode)
        except KeyboardInterrupt:
            print("\n⛔ Setup cancelled by user.")
        
        print("=" * 60 + "\n")
    
    def _make_api_request(self, url: str, method: str = "GET", data: Optional[Dict] = None, 
                          headers: Optional[Dict] = None) -> Dict:
        """Make an API request.
        
        Args:
            url: Full URL for the request
            method: HTTP method
            data: JSON data for POST/PUT requests
            headers: Additional headers
            
        Returns:
            Response data as dictionary
        """
        if self.dry_run:
            self._print_action(f"API {method} request to {url}", str(data) if data else "")
            return {"dry_run": True}
        
        # Prepare headers
        request_headers = headers or {}
        if data:
            request_headers["Content-Type"] = "application/json"
        
        # Prepare data
        request_data = None
        if data:
            request_data = json.dumps(data).encode('utf-8')
        
        # Create request
        req = urllib.request.Request(url, data=request_data, headers=request_headers, method=method)
        
        try:
            with urllib.request.urlopen(req) as response:
                response_data = response.read().decode('utf-8')
                if response_data:
                    return json.loads(response_data)
                return {}
        except Exception as e:
            if hasattr(e, 'code') and hasattr(e, 'read'):
                try:
                    error_body = e.read().decode('utf-8')
                    error_data = json.loads(error_body)
                    error_msg = error_data.get('message', error_body)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    error_msg = str(e)
                raise ValueError(f"API request failed ({e.code}): {error_msg}")
            else:
                raise ValueError(f"API request failed: {e}")
    
    def collect_project_info(self) -> Dict[str, str]:
        """Collect project information interactively."""
        print("=� Project Initialization")
        print("=" * 50)
        
        project_info = {}
        
        # Required fields
        project_info['project_name'] = input("Project Name: ").strip()
        if not project_info['project_name']:
            raise ValueError("Project name is required")
        
        project_info['project_alias'] = input("Project Alias (for Claude): ").strip()
        if not project_info['project_alias']:
            project_info['project_alias'] = project_info['project_name'].lower().replace(' ', '-')
        
        project_info['description'] = input("Project Description: ").strip()
        if not project_info['description']:
            raise ValueError("Project description is required")
        
        # Ask if it's a coding project
        is_code = input("Is this a coding project? (y/n): ").strip().lower()
        project_info['code'] = 'True' if is_code in ['y', 'yes', 'true', '1'] else 'False'
        
        if project_info['code'] == 'True':
            # Additional fields for coding projects
            default_git_repo = f"git@git.y37.space:y37.space/{project_info['project_alias']}.git"
            git_repo = input(f"Git Repository SSH URL [{default_git_repo}]: ").strip()
            project_info['git_repo'] = git_repo or default_git_repo
            
            default_public_url = f"https://{project_info['project_alias']}.y37.space"
            public_url = input(f"Public App URL [{default_public_url}]: ").strip()
            project_info['public_app_url'] = public_url or default_public_url
            
            claude_enabled = input("Enable Claude Code integration? (y/n) [y]: ").strip().lower()
            project_info['claude_enabled'] = 'True' if claude_enabled in ['', 'y', 'yes', 'true', '1'] else 'False'
            
            default_auth_user = f"{project_info['project_alias']}-sa"
            auth_user = input(f"Authentik Service Account User [{default_auth_user}]: ").strip()
            project_info['authentik_user'] = auth_user or default_auth_user
            
            default_auth_group = f"{project_info['project_alias']}-users"
            auth_group = input(f"Authentik Group [{default_auth_group}]: ").strip()
            project_info['authentik_group'] = auth_group or default_auth_group
        else:
            # Set defaults for non-coding projects
            project_info['git_repo'] = '<GIT_REPO_URL>'
            project_info['public_app_url'] = '<PUBLIC_APP_URL>'
            project_info['claude_enabled'] = 'False'
            project_info['authentik_user'] = '<AUTHENTIK_USER>'
            project_info['authentik_group'] = '<AUTHENTIK_GROUP>'
        
        print("\n=� Project Configuration Summary:")
        print("-" * 30)
        for key, value in project_info.items():
            print(f"{key}: {value}")
        
        confirm = input("\nProceed with this configuration? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Initialization cancelled.")
            sys.exit(0)
        
        return project_info
    
    def update_project_yaml(self, project_info: Dict[str, str]) -> None:
        """Update project.yaml with collected information."""
        yaml_file = self.project_root / "project.yaml"
        
        self._print_action("Updating project.yaml", str(yaml_file))
        
        if self.dry_run:
            return
        
        # Always use template content to ensure placeholders are replaced
        content = f"""project_name: <PROJECT_NAME>
project_alias: <PROJECT_ALIAS>
description: <PROJECT_DESCRIPTION>
code: <PROJECT_CODE>                        # Does this project have a codebase or is it not a coding project? True/False

###################
# Coding Projects
###################
git_repo: <GIT_REPO_URL>                    # Gitea repository for the project, the SSH one `git@git.y37.space...`
public_app_url: <PUBLIC_APP_URL>            # URL that the project would be made available on
claude_enabled: <CLAUDE_ENABLED>            # Will Claude Code be used in this project? True/False
authentik_user: <AUTHENTIK_USER>            # User to be created and used as a service account, typically `project_name-sa`
authentik_group: <AUTHENTIK_GROUP>          # Group to be created and used for this application. authentik_user would be a member of this group. Can be one or many groups. (e.g. project_name-admin, project_name-users)
admin_users:
  - wk
  - maya
"""
        
        # Replace placeholders
        replacements = {
            '<PROJECT_NAME>': project_info['project_name'],
            '<PROJECT_ALIAS>': project_info['project_alias'],
            '<PROJECT_DESCRIPTION>': project_info['description'],
            '<PROJECT_CODE>': project_info['code'],
            '<GIT_REPO_URL>': project_info['git_repo'],
            '<PUBLIC_APP_URL>': project_info['public_app_url'],
            '<CLAUDE_ENABLED>': project_info['claude_enabled'],
            '<AUTHENTIK_USER>': project_info['authentik_user'],
            '<AUTHENTIK_GROUP>': project_info['authentik_group']
        }
        
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        
        # Write updated content
        with open(yaml_file, 'w') as f:
            f.write(content)
    
    def replace_template_placeholders(self, project_info: Dict[str, str]) -> None:
        """Replace XML placeholders in README.md, CLAUDE.md, and project.yaml."""
        files_to_update = [
            self.project_root / "README.md",
            self.project_root / "CLAUDE.md",
            self.project_root / "project.yaml",
            self.project_root / "DOCS" / "mkdocs.yml"
        ]
        
        for file_path in files_to_update:
            if not file_path.exists():
                self._print_action(f"Skipping {file_path.name} (not found)")
                continue
            
            self._print_action(f"Updating placeholders in {file_path.name}")
            
            if self.dry_run:
                continue
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Convert SSH URL to HTTPS for web links
            https_repo_url = self._convert_ssh_to_https_url(project_info['git_repo'])
            
            # Replace XML-style placeholders
            xml_replacements = {
                '<PROJECT_NAME>': project_info['project_name'],
                '<PROJECT_ALIAS>': project_info['project_alias'],
                '<PROJECT_DESCRIPTION>': project_info['description'],
                '<PROJECT_VERSION>': 'v2025-07-07-INIT-001',
                '<GIT_REPO_URL>': project_info['git_repo'],  # SSH format for git operations
                '<GIT_REPO_HTTPS_URL>': https_repo_url,      # HTTPS format for web links
                '<PUBLIC_APP_URL>': project_info['public_app_url']  # Public app URL
            }
            
            for placeholder, value in xml_replacements.items():
                content = content.replace(placeholder, value)
            
            with open(file_path, 'w') as f:
                f.write(content)
    
    def create_gitea_repository(self, project_info: Dict[str, str]) -> Optional[Dict]:
        """Create repository in Gitea."""
        if project_info['code'] != 'True':
            self._print_action("Skipping Gitea repository creation (not a coding project)")
            return None
        
        # Extract repo name from git_repo URL
        repo_name = project_info['project_alias']
        org_name = "y37.space"
        
        self._print_action(f"Creating Gitea repository: {org_name}/{repo_name}")
        
        # Check if repository already exists
        check_url = f"{self.gitea_base_url}/api/v1/repos/{org_name}/{repo_name}"
        headers = {"Authorization": f"token {self.gitea_api_key}"}
        
        try:
            existing_repo = self._make_api_request(check_url, headers=headers)
            if not self.dry_run and existing_repo and not existing_repo.get('dry_run'):
                print(f"  Repository {org_name}/{repo_name} already exists")
                return existing_repo
        except ValueError:
            # Repository doesn't exist, which is what we want
            pass
        
        # Create repository
        create_url = f"{self.gitea_base_url}/api/v1/orgs/{org_name}/repos"
        repo_data = {
            "name": repo_name,
            "description": project_info['description'],
            "private": False,
            "auto_init": False,
            "default_branch": "main"
        }
        
        result = self._make_api_request(create_url, "POST", repo_data, headers)
        
        # Add wk user as admin collaborator
        if result and not self.dry_run:
            self._add_collaborator(org_name, repo_name, "wk", "admin")
        
        return result
    
    def _add_collaborator(self, org: str, repo: str, username: str, permission: str = "admin") -> None:
        """Add a collaborator to the repository.
        
        Args:
            org: Organization name
            repo: Repository name  
            username: Username to add as collaborator
            permission: Permission level (admin, write, read)
        """
        self._print_action(f"Adding {username} as {permission} collaborator to {org}/{repo}")
        
        collab_url = f"{self.gitea_base_url}/api/v1/repos/{org}/{repo}/collaborators/{username}"
        headers = {"Authorization": f"token {self.gitea_api_key}"}
        collab_data = {"permission": permission}
        
        try:
            self._make_api_request(collab_url, "PUT", collab_data, headers)
            print(f"  Added {username} as {permission} collaborator")
        except ValueError as e:
            print(f"  Warning: Could not add {username} as collaborator: {e}")
    
    def enable_woodpecker_ci(self, project_info: Dict[str, str]) -> Optional[Dict]:
        """Enable repository in Woodpecker CI."""
        if project_info['code'] != 'True':
            self._print_action("Skipping Woodpecker CI setup (not a coding project)")
            return None
        
        repo_name = f"y37.space/{project_info['project_alias']}"
        
        self._print_action(f"Enabling Woodpecker CI for {repo_name}")
        
        # First, get the Gitea repository ID
        gitea_repo_url = f"{self.gitea_base_url}/api/v1/repos/y37.space/{project_info['project_alias']}"
        gitea_headers = {"Authorization": f"token {self.gitea_api_key}"}
        
        try:
            gitea_repo = self._make_api_request(gitea_repo_url, headers=gitea_headers)
            if self.dry_run or not gitea_repo.get('id'):
                forge_remote_id = "999"  # Dummy ID for dry run
            else:
                forge_remote_id = str(gitea_repo['id'])
                
            # Enable repository using correct API endpoint
            enable_url = f"{self.woodpecker_base_url}/api/repos?forge_remote_id={forge_remote_id}"
            headers = {"Authorization": f"Bearer {self.woodpecker_api_key}"}
            
            result = self._make_api_request(enable_url, "POST", None, headers)
            
            # Configure repository settings to ensure wk user has access
            if result and not self.dry_run:
                repo_id = result.get('id')
                if repo_id:
                    self._configure_repository_access(repo_id)
            
            return result
            
        except ValueError as e:
            print(f"  Warning: Could not enable Woodpecker CI: {e}")
            return None
    
    def _configure_repository_access(self, repo_id: int) -> None:
        """Configure repository access settings for both Maya and wk users."""
        self._print_action(f"Configuring repository access for repo {repo_id}")
        
        headers = {"Authorization": f"Bearer {self.woodpecker_api_key}"}
        
        # Step 1: Set repository visibility to 'internal' to ensure authenticated users can see it
        visibility_url = f"{self.woodpecker_base_url}/api/repos/{repo_id}"
        visibility_data = {
            "visibility": "internal"  # Allow all authenticated users to see this repository
        }
        
        try:
            self._make_api_request(visibility_url, "PATCH", visibility_data, headers)
            print(f"  Repository {repo_id} visibility set to internal")
        except ValueError as e:
            print(f"  Warning: Could not set repository visibility: {e}")
        
        # Step 2: Configure repository settings for optimal access
        settings_data = {
            "trusted": True,             # Enable trusted mode for full capabilities
            "timeout": 60               # 60 minute timeout for builds
        }
        
        try:
            self._make_api_request(visibility_url, "PATCH", settings_data, headers)
            print(f"  Repository {repo_id} configured with optimal access settings")
        except ValueError as e:
            print(f"  Warning: Could not configure repository settings: {e}")
        
        # Step 3: Verify user access for both Maya and wk
        self._verify_user_access(repo_id)
    
    def _verify_user_access(self, repo_id: int) -> None:
        """Verify that both Maya and wk users can access the repository."""
        self._print_action(f"Verifying user access for repository {repo_id}")
        
        headers = {"Authorization": f"Bearer {self.woodpecker_api_key}"}
        
        # Check repository permissions
        permissions_url = f"{self.woodpecker_base_url}/api/repos/{repo_id}/permissions"
        
        try:
            permissions = self._make_api_request(permissions_url, headers=headers)
            if not self.dry_run and permissions and not permissions.get('dry_run'):
                print(f"  Repository permissions: {permissions}")
            else:
                print(f"  Repository permissions check completed")
        except ValueError as e:
            print(f"  Warning: Could not check repository permissions: {e}")
        
        # List all user repositories to verify access
        user_repos_url = f"{self.woodpecker_base_url}/api/user/repos"
        
        try:
            user_repos = self._make_api_request(user_repos_url, headers=headers)
            if not self.dry_run and user_repos and not (isinstance(user_repos, dict) and user_repos.get('dry_run')):
                # Check if our repository is in the user's accessible repos
                repo_found = False
                # user_repos should be a list of repository objects
                if isinstance(user_repos, list):
                    for repo in user_repos:
                        if isinstance(repo, dict) and repo.get('id') == repo_id:
                            repo_found = True
                            print(f"  Repository {repo_id} is accessible to user")
                            break
                    
                    if not repo_found:
                        print(f"  Warning: Repository {repo_id} not found in user's accessible repositories")
                        print(f"  This may indicate a permissions issue")
                else:
                    print(f"  Unexpected response format for user repositories: {type(user_repos)}")
            else:
                print(f"  User repository access check completed")
        except ValueError as e:
            print(f"  Warning: Could not check user repository access: {e}")
    
    def get_woodpecker_badge_info(self, project_info: Dict[str, str]) -> Optional[tuple]:
        """Get Woodpecker CI badge information."""
        if project_info['code'] != 'True':
            return None
        
        repo_name = f"y37.space/{project_info['project_alias']}"
        
        # Get repository info to find the ID
        repos_url = f"{self.woodpecker_base_url}/api/user/repos"
        headers = {"Authorization": f"Bearer {self.woodpecker_api_key}"}
        
        if self.dry_run:
            # Return dummy badge info for dry run
            return (
                f"https://ci.y37.space/api/badges/999/status.svg",
                f"https://ci.y37.space/repos/999"
            )
        
        try:
            repos = self._make_api_request(repos_url, headers=headers)
            for repo in repos:
                if repo.get('full_name') == repo_name:
                    repo_id = repo.get('id')
                    badge_url = f"https://ci.y37.space/api/badges/{repo_id}/status.svg"
                    repo_url = f"https://ci.y37.space/repos/{repo_id}"
                    return (badge_url, repo_url)
        except ValueError as e:
            print(f"  Warning: Could not get badge info: {e}")
        
        return None
    
    def setup_issues_workflow(self, project_info: Dict[str, str]) -> None:
        """Setup Issues-based workflow configuration."""
        if project_info['code'] != 'True':
            self._print_action("Skipping Issues workflow setup (not a coding project)")
            return
        
        org_name = "y37.space"
        repo_name = project_info['project_alias']
        
        self._print_action("Setting up Issues-based workflow")
        
        # Create default milestone
        self._create_default_milestone(org_name, repo_name, project_info)
        
        # Setup repository labels
        self._setup_repository_labels(org_name, repo_name)
        
        # Configure repository settings for Issues
        self._configure_repository_issues(org_name, repo_name)
        
        # Update project.yaml with Issues URL
        issues_url = f"{self.gitea_base_url}/{org_name}/{repo_name}/issues"
        self._update_project_yaml_issues_url(project_info, issues_url)
    
    def _create_default_milestone(self, org: str, repo: str, project_info: Dict[str, str]) -> None:
        """Create default milestone for the project."""
        self._print_action("Creating default milestone")
        
        milestone_data = {
            "title": "v1.0",
            "description": f"Initial release of {project_info['project_name']}",
            "state": "open"
        }
        
        milestone_url = f"{self.gitea_base_url}/api/v1/repos/{org}/{repo}/milestones"
        headers = {"Authorization": f"token {self.gitea_api_key}"}
        
        try:
            self._make_api_request(milestone_url, "POST", milestone_data, headers)
            print(f"  Created milestone: v1.0")
        except ValueError as e:
            print(f"  Warning: Could not create milestone: {e}")
    
    def _setup_repository_labels(self, org: str, repo: str) -> None:
        """Setup standard labels for task/bug differentiation."""
        self._print_action("Setting up repository labels")
        
        standard_labels = [
            {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
            {"name": "enhancement", "color": "a2eeef", "description": "New feature or request"},
            {"name": "task", "color": "7057ff", "description": "General task or work item"},
            {"name": "priority/high", "color": "ff6b6b", "description": "High priority item"},
            {"name": "priority/medium", "color": "ffd93d", "description": "Medium priority item"},
            {"name": "priority/low", "color": "6bcf7f", "description": "Low priority item"}
        ]
        
        labels_url = f"{self.gitea_base_url}/api/v1/repos/{org}/{repo}/labels"
        headers = {"Authorization": f"token {self.gitea_api_key}"}
        
        for label in standard_labels:
            try:
                self._make_api_request(labels_url, "POST", label, headers)
                print(f"  Created label: {label['name']}")
            except ValueError as e:
                if "already exists" not in str(e).lower():
                    print(f"  Warning: Could not create label {label['name']}: {e}")
    
    def _configure_repository_issues(self, org: str, repo: str) -> None:
        """Configure repository settings for Issues workflow."""
        self._print_action("Configuring repository Issues settings")
        
        # Enable Issues, PRs, and Wiki
        repo_settings = {
            "has_issues": True,
            "has_pull_requests": True,
            "has_wiki": True,
            "allow_merge_commits": True,
            "allow_squash_merge": True,
            "allow_rebase_merge": True
        }
        
        repo_url = f"{self.gitea_base_url}/api/v1/repos/{org}/{repo}"
        headers = {"Authorization": f"token {self.gitea_api_key}"}
        
        try:
            self._make_api_request(repo_url, "PATCH", repo_settings, headers)
            print(f"  Configured repository Issues settings")
        except ValueError as e:
            print(f"  Warning: Could not configure repository settings: {e}")
    
    def _update_project_yaml_issues_url(self, project_info: Dict[str, str], issues_url: str) -> None:
        """Update project.yaml with Issues URL."""
        self._print_action(f"Adding Issues URL to project.yaml: {issues_url}")
        
        project_yaml_path = self.project_root / "project.yaml"
        
        if not project_yaml_path.exists():
            self._print_action("Warning: project.yaml not found, skipping Issues URL update")
            return
        
        if self.dry_run:
            return
        
        with open(project_yaml_path, 'r') as f:
            content = f.read()
        
        # Add Issues URL after CI URL if it exists, otherwise after public_app_url
        if 'ci_url:' in content:
            # Add after CI URL
            import re
            content = re.sub(
                r'(ci_url:.*\n)',
                f'\\1issues_url: {issues_url}            # Gitea Issues URL for task and bug tracking\n',
                content
            )
        elif 'issues_url:' not in content:
            # Add after public_app_url
            content = content.replace(
                'public_app_url:',
                f'public_app_url: {project_info["public_app_url"]}            # URL that the project would be made available on\nissues_url: {issues_url}            # Gitea Issues URL for task and bug tracking'
            )
        
        with open(project_yaml_path, 'w') as f:
            f.write(content)
    
    def update_project_yaml_ci_url(self, project_info: Dict[str, str], ci_url: str) -> None:
        """Update project.yaml file with CI URL."""
        self._print_action(f"Updating project.yaml with CI URL: {ci_url}")
        
        project_yaml_path = self.project_root / "project.yaml"
        
        if not project_yaml_path.exists():
            self._print_action("Warning: project.yaml not found, skipping CI URL update")
            return
        
        if self.dry_run:
            return
        
        with open(project_yaml_path, 'r') as f:
            content = f.read()
        
        # Replace or add CI URL line
        if 'ci_url:' in content:
            # Replace existing CI URL
            import re
            content = re.sub(r'ci_url:.*', f'ci_url: {ci_url}            # Woodpecker CI URL for monitoring builds', content)
        else:
            # Add CI URL after public_app_url
            content = content.replace(
                'public_app_url:', 
                f'public_app_url: {project_info["public_app_url"]}            # URL that the project would be made available on\nci_url: {ci_url}            # Woodpecker CI URL for monitoring builds'
            )
        
        with open(project_yaml_path, 'w') as f:
            f.write(content)

    def update_readme_with_badge(self, project_info: Dict[str, str]) -> None:
        """Update README.md with Woodpecker CI badge."""
        if project_info['code'] != 'True':
            self._print_action("Skipping badge update (not a coding project)")
            return
        
        readme_file = self.project_root / "README.md"
        if not readme_file.exists():
            self._print_action("Skipping badge update (README.md not found)")
            return
        
        badge_info = self.get_woodpecker_badge_info(project_info)
        if not badge_info:
            self._print_action("Skipping badge update (could not get badge info)")
            return
        
        badge_url, repo_url = badge_info
        
        self._print_action("Adding Woodpecker CI badge to README.md")
        
        if self.dry_run:
            return
        
        with open(readme_file, 'r') as f:
            content = f.read()
        
        # Create badge markdown
        badge_markdown = f"[![Build Status]({badge_url})]({repo_url})"
        
        # Find the main header and add badge after it
        # Look for patterns like "# ProjectName" followed by any <REPLACE> blocks
        header_pattern = rf"^# {re.escape(project_info['project_name'])}.*$"
        match = re.search(header_pattern, content, re.MULTILINE)
        
        if match:
            # Find the end of any <REPLACE> blocks after the header
            after_header = content[match.end():]
            replace_pattern = r'<REPLACE>.*?</REPLACE>'
            replace_match = re.search(replace_pattern, after_header, re.DOTALL)
            
            if replace_match:
                # Insert badge after the last <REPLACE> block
                insert_pos = match.end() + replace_match.end()
                content = content[:insert_pos] + f"\n\n{badge_markdown}" + content[insert_pos:]
            else:
                # Insert badge right after the header
                insert_pos = match.end()
                content = content[:insert_pos] + f"\n\n{badge_markdown}" + content[insert_pos:]
        else:
            # If no main header found, add at the beginning
            content = f"{badge_markdown}\n\n" + content
        
        with open(readme_file, 'w') as f:
            f.write(content)
    
    def copy_template_files(self, project_info: Dict[str, str]) -> None:
        """Copy template files to project root."""
        if project_info['code'] != 'True':
            self._print_action("Skipping template file copying (not a coding project)")
            return
        
        template_files = [
            (".woodpecker.yaml", ".woodpecker.yaml"),
            (".gitignore.example", ".gitignore"),
            ("README.md", "README.md"),  # Add README.md template
            ("mkdocs.yml", "DOCS/mkdocs.yml")  # Add MkDocs configuration
        ]
        
        for src_name, dst_name in template_files:
            src_path = self.projects_dir / "template-files" / src_name
            dst_path = self.project_root / dst_name
            
            if not src_path.exists():
                self._print_action(f"Warning: Template file not found: {src_path}")
                continue
            
            # For README.md, we want to replace the existing one
            if dst_name == "README.md" and dst_path.exists():
                self._print_action(f"Replacing existing {dst_name} with template")
            else:
                self._print_action(f"Copying {src_name} to {dst_name}")
            
            if not self.dry_run:
                # Create parent directory if it doesn't exist
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
    
    def copy_issue_templates(self, project_info: Dict[str, str]) -> None:
        """Copy Gitea issue templates to project root."""
        if project_info['code'] != 'True':
            self._print_action("Skipping issue template copying (not a coding project)")
            return
        
        self._print_action("Setting up Gitea issue templates")
        
        # Create .gitea/issue_template directory
        issue_template_dir = self.project_root / ".gitea" / "issue_template"
        if not self.dry_run:
            issue_template_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy issue template files
        template_source_dir = self.projects_dir.parent / ".gitea" / "issue_template"
        
        # Check if source and destination are the same (template project case)
        if template_source_dir.resolve() == issue_template_dir.resolve():
            self._print_action("Issue templates already exist in project root, skipping copy")
            return
        
        if template_source_dir.exists():
            for template_file in template_source_dir.glob("*.md"):
                src_path = template_file
                dst_path = issue_template_dir / template_file.name
                
                # Skip if source and destination are the same file
                if src_path.resolve() == dst_path.resolve():
                    self._print_action(f"Skipping {template_file.name} (already exists)")
                    continue
                
                self._print_action(f"Copying issue template: {template_file.name}")
                
                if not self.dry_run:
                    shutil.copy2(src_path, dst_path)
        else:
            self._print_action("Warning: Source issue templates not found, skipping")
    
    def setup_mkdocs(self, project_info: Dict[str, str]) -> None:
        """Setup MkDocs documentation system."""
        if project_info['code'] != 'True':
            self._print_action("Skipping MkDocs setup (not a coding project)")
            return
        
        self._print_action("Setting up MkDocs documentation system")
        
        # Create DOCS directory
        docs_dir = self.project_root / "DOCS"
        if not self.dry_run:
            docs_dir.mkdir(exist_ok=True)
        
        # Copy docs template files
        docs_template_dir = self.projects_dir / "template-files" / "docs"
        if docs_template_dir.exists():
            for template_file in docs_template_dir.rglob("*"):
                if template_file.is_file():
                    # Calculate relative path from template docs directory
                    relative_path = template_file.relative_to(docs_template_dir)
                    target_path = docs_dir / relative_path
                    
                    self._print_action(f"Copying docs template: {relative_path}")
                    
                    if not self.dry_run:
                        # Create parent directories if needed
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(template_file, target_path)
        
        # Create requirements-docs.txt for documentation dependencies
        requirements_docs = docs_dir / "requirements-docs.txt"
        if not requirements_docs.exists() and not self.dry_run:
            with open(requirements_docs, 'w') as f:
                f.write("""mkdocs>=1.4.0
mkdocs-material>=9.0.0
mkdocstrings[python]>=0.20.0
pymdown-extensions>=9.0.0
""")
            self._print_action("Created requirements-docs.txt")
    
    def cleanup_template_files(self) -> None:
        """Clean up template development files for new projects."""
        self._print_action("Cleaning up template development files")
        
        if self.dry_run:
            self._print_action("Would remove template TASK files, BUG files, and DOCS directory")
            self._print_action("Would reset TODO.md and BUGS.md to clean state")
            return
        
        # Remove all TASK files except template
        tasks_dir = self.project_root / "TASKS"
        if tasks_dir.exists():
            for task_file in tasks_dir.glob("TASK-*.md"):
                self._print_action(f"Removing template task file: {task_file.name}")
                task_file.unlink()
        
        # Remove all BUG files except template
        bugs_dir = self.project_root / "BUGS"
        if bugs_dir.exists():
            for bug_file in bugs_dir.glob("BUG-*.md"):
                self._print_action(f"Removing template bug file: {bug_file.name}")
                bug_file.unlink()
        
        # Remove DOCS directory (template project documentation)
        docs_dir = self.project_root / "DOCS"
        if docs_dir.exists():
            self._print_action("Removing template DOCS directory")
            shutil.rmtree(docs_dir)
        
        # Reset TODO.md to clean state
        todo_file = self.project_root / "TODO.md"
        if todo_file.exists():
            self._print_action("Resetting TODO.md to clean state")
            with open(todo_file, 'w') as f:
                f.write("# TODO\n\n")
        
        # Reset BUGS.md to clean state  
        bugs_index_file = self.project_root / "BUGS.md"
        if bugs_index_file.exists():
            self._print_action("Resetting BUGS.md to clean state")
            with open(bugs_index_file, 'w') as f:
                f.write("""# BUGS

## Severity Levels

- **P0**: Critical - System down, data loss, security vulnerability
- **P1**: High - Major feature broken, significant user impact  
- **P2**: Medium - Minor issues, cosmetic problems

## Active Bugs

No active bugs.

""")
    
    def setup_git_repository(self, project_info: Dict[str, str]) -> None:
        """Initialize git repository and push to remote."""
        if project_info['code'] != 'True':
            self._print_action("Skipping git setup (not a coding project)")
            return
        
        # Check if already a git repository
        if (self.project_root / ".git").exists():
            self._print_action("Git repository already exists")
            return
        
        ssh_key_path = self.projects_dir / "maya_id_ed25519"
        
        commands = [
            ["git", "init"],
            ["git", "config", "user.name", "maya"],
            ["git", "config", "user.email", "maya@y37.space"],
            ["git", "config", "core.sshCommand", f"ssh -i {ssh_key_path}"],
            ["git", "checkout", "-b", "main"],
            ["git", "add", "."],
            ["git", "commit", "-m", "Initial project setup\\n\\n> Generated with Project Template"],
            ["git", "remote", "add", "origin", project_info['git_repo']],
            ["git", "push", "-u", "origin", "main"]
        ]
        
        for cmd in commands:
            self._print_action(f"Running: {' '.join(cmd)}")
            
            if not self.dry_run:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    if result.stdout:
                        print(f"  {result.stdout.strip()}")
                except subprocess.CalledProcessError as e:
                    print(f"  Error: {e}")
                    if e.stderr:
                        print(f"  {e.stderr.strip()}")
                    if "git push" in " ".join(cmd):
                        print("  Note: Push failed - you may need to create the repository first")
                    else:
                        raise
    
    def run(self) -> None:
        """Run the complete project initialization process."""
        try:
            print("=' Project Template Initializer")
            print("=" * 50)
            
            if self.dry_run:
                print(">� DRY RUN MODE - No changes will be made")
                print()
            
            # Step 1: Collect project information
            project_info = self.collect_project_info()
            
            # Step 2: Clean up template development files
            self.cleanup_template_files()
            
            # Step 3: Update project.yaml
            self.update_project_yaml(project_info)
            
            # Step 4: Copy template files (including README.md stub)
            self.copy_template_files(project_info)
            
            # Step 4a: Copy Gitea issue templates
            self.copy_issue_templates(project_info)
            
            # Step 5: Setup MkDocs documentation system
            self.setup_mkdocs(project_info)
            
            # Step 6: Replace template placeholders
            self.replace_template_placeholders(project_info)
            
            # Step 7: Create Gitea repository
            self.create_gitea_repository(project_info)
            
            # Step 8: Setup git repository and push
            self.setup_git_repository(project_info)
            
            # Step 9: Enable Woodpecker CI (after repo exists in Gitea)
            woodpecker_result = self.enable_woodpecker_ci(project_info)
            
            # Step 9a: Update project.yaml with CI URL
            if woodpecker_result and woodpecker_result.get('id'):
                ci_url = f"{self.woodpecker_base_url}/repos/{woodpecker_result['id']}"
                self.update_project_yaml_ci_url(project_info, ci_url)
            
            # Step 9b: Setup Issues-based workflow
            self.setup_issues_workflow(project_info)
            
            # Step 10: Update README with CI badge
            self.update_readme_with_badge(project_info)
            
            print("\n Project initialization completed successfully!")
            
            if project_info['code'] == 'True':
                print(f"\n=� Next steps:")
                print(f"  - Repository: {self.gitea_base_url}/y37.space/{project_info['project_alias']}")
                print(f"  - CI/CD: {self.woodpecker_base_url}")
                print(f"  - Start developing in the main branch")
                print(f"  - Create tasks using: python .projects/tools/issue-mgr.py new --type task")
            
        except KeyboardInterrupt:
            print("\nL Initialization cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\nL Initialization failed: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize a new project from template",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Normal initialization
    python init_project.py
    
    # Dry run to see what would be done
    python init_project.py --dry-run
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    initializer = ProjectInitializer(dry_run=args.dry_run)
    initializer.run()


if __name__ == "__main__":
    main()