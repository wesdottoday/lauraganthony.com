#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Woodpecker CI Access Management Tool

This script helps diagnose and fix repository access issues in Woodpecker CI,
specifically ensuring both Maya and wk users can see and access repositories.

Usage:
    python woodpecker-access-fix.py --repo-name <repo-name> [--fix]
    python woodpecker-access-fix.py --list-repos
    python woodpecker-access-fix.py --check-user <username>
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional


class WoodpeckerAccessManager:
    """Manages Woodpecker CI repository access and permissions."""
    
    def __init__(self):
        """Initialize the access manager."""
        self.project_root = Path.cwd()
        self.projects_dir = self.project_root / ".projects"
        self.env_file = self.projects_dir / ".env"
        
        # Load environment variables
        self.env_vars = self._load_env()
        
        # API configuration
        self.woodpecker_api_key = self.env_vars.get("MAYA_WOODPECKER_API_KEY")
        self.woodpecker_base_url = "https://ci.y37.space"
        
        if not self.woodpecker_api_key:
            raise ValueError("MAYA_WOODPECKER_API_KEY not found in .projects/.env")
    
    def _load_env(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        if not self.env_file.exists():
            raise FileNotFoundError(f".env file not found: {self.env_file}")
        
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"\'')
                    env_vars[key] = value
        
        return env_vars
    
    def _make_api_request(self, url: str, method: str = "GET", data: Optional[Dict] = None) -> Dict:
        """Make an API request to Woodpecker CI."""
        headers = {"Authorization": f"Bearer {self.woodpecker_api_key}"}
        
        if data:
            headers["Content-Type"] = "application/json"
        
        request_data = None
        if data:
            request_data = json.dumps(data).encode('utf-8')
        
        req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
        
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
    
    def list_repositories(self) -> List[Dict]:
        """List all repositories accessible to the current user."""
        print("=== Listing All Accessible Repositories ===")
        
        url = f"{self.woodpecker_base_url}/api/user/repos"
        
        try:
            repos = self._make_api_request(url)
            
            if not repos:
                print("No repositories found or API returned empty response")
                return []
            
            print(f"Found {len(repos)} repositories:")
            print()
            
            for repo in repos:
                print(f"Repository: {repo.get('full_name', 'N/A')}")
                print(f"  ID: {repo.get('id', 'N/A')}")
                print(f"  Visibility: {repo.get('visibility', 'N/A')}")
                print(f"  Active: {repo.get('active', 'N/A')}")
                print(f"  URL: {repo.get('link_url', 'N/A')}")
                print()
            
            return repos
            
        except ValueError as e:
            print(f"Error listing repositories: {e}")
            return []
    
    def check_repository_access(self, repo_name: str) -> Optional[Dict]:
        """Check access to a specific repository."""
        print(f"=== Checking Repository Access: {repo_name} ===")
        
        # First, get all repositories and find the one we're looking for
        repos = self.list_repositories()
        
        target_repo = None
        for repo in repos:
            if repo.get('full_name') == repo_name or repo.get('name') == repo_name:
                target_repo = repo
                break
        
        if not target_repo:
            print(f"Repository '{repo_name}' not found in accessible repositories")
            print("This indicates a permissions issue.")
            return None
        
        repo_id = target_repo.get('id')
        print(f"Repository found with ID: {repo_id}")
        
        # Check repository permissions
        permissions_url = f"{self.woodpecker_base_url}/api/repos/{repo_id}/permissions"
        
        try:
            permissions = self._make_api_request(permissions_url)
            print(f"Repository permissions:")
            for key, value in permissions.items():
                print(f"  {key}: {value}")
            
        except ValueError as e:
            print(f"Error checking permissions: {e}")
        
        # Get detailed repository info
        repo_url = f"{self.woodpecker_base_url}/api/repos/{repo_id}"
        
        try:
            repo_details = self._make_api_request(repo_url)
            print(f"Repository details:")
            important_fields = ['visibility', 'active', 'trusted', 'allow_pr', 'allow_deploy']
            for field in important_fields:
                if field in repo_details:
                    print(f"  {field}: {repo_details[field]}")
            
        except ValueError as e:
            print(f"Error getting repository details: {e}")
        
        return target_repo
    
    def fix_repository_access(self, repo_name: str) -> bool:
        """Fix repository access issues."""
        print(f"=== Fixing Repository Access: {repo_name} ===")
        
        # Get repository info
        target_repo = self.check_repository_access(repo_name)
        if not target_repo:
            print("Cannot fix access - repository not found")
            return False
        
        repo_id = target_repo.get('id')
        
        # Apply fixes
        fixes_applied = []
        
        # Fix 1: Set visibility to internal
        print("\\nApplying Fix 1: Setting repository visibility to 'internal'...")
        visibility_url = f"{self.woodpecker_base_url}/api/repos/{repo_id}"
        visibility_data = {"visibility": "internal"}
        
        try:
            self._make_api_request(visibility_url, "PATCH", visibility_data)
            print("✓ Repository visibility set to internal")
            fixes_applied.append("visibility")
        except ValueError as e:
            print(f"✗ Failed to set visibility: {e}")
        
        # Fix 2: Configure repository settings
        print("\\nApplying Fix 2: Configuring repository settings...")
        settings_data = {
            "trusted": True,
            "allow_pr": True,
            "allow_deploy": True,
            "timeout": 60
        }
        
        try:
            self._make_api_request(visibility_url, "PATCH", settings_data)
            print("✓ Repository settings configured")
            fixes_applied.append("settings")
        except ValueError as e:
            print(f"✗ Failed to configure settings: {e}")
        
        # Verify fixes
        print("\\nVerifying fixes...")
        updated_repo = self.check_repository_access(repo_name)
        
        if fixes_applied:
            print(f"\\n✓ Applied {len(fixes_applied)} fixes: {', '.join(fixes_applied)}")
            print("\\nNext steps:")
            print("1. Ask wk to log out and log back into Woodpecker CI")
            print("2. Ask wk to refresh the repositories list")
            print("3. Check if the repository now appears in wk's dashboard")
            return True
        else:
            print("\\n✗ No fixes could be applied")
            return False
    
    def check_user_authentication(self) -> bool:
        """Check if the current user is properly authenticated."""
        print("=== Checking User Authentication ===")
        
        url = f"{self.woodpecker_base_url}/api/user"
        
        try:
            user_info = self._make_api_request(url)
            
            print(f"Authenticated user: {user_info.get('login', 'N/A')}")
            print(f"User ID: {user_info.get('id', 'N/A')}")
            print(f"Email: {user_info.get('email', 'N/A')}")
            print(f"Admin: {user_info.get('admin', 'N/A')}")
            
            return True
            
        except ValueError as e:
            print(f"Authentication failed: {e}")
            return False
    
    def run_diagnostic(self, repo_name: str) -> None:
        """Run a comprehensive diagnostic."""
        print("=== Woodpecker CI Access Diagnostic ===")
        print()
        
        # Check authentication
        if not self.check_user_authentication():
            print("\\n❌ Authentication failed - cannot proceed")
            return
        
        print("\\n" + "="*50)
        
        # List all repositories
        repos = self.list_repositories()
        
        print("\\n" + "="*50)
        
        # Check specific repository
        if repo_name:
            repo = self.check_repository_access(repo_name)
            
            if not repo:
                print(f"\\n❌ Repository '{repo_name}' is not accessible")
                print("\\nPossible causes:")
                print("1. Repository doesn't exist in Woodpecker CI")
                print("2. Repository visibility is set to 'private'")
                print("3. User doesn't have access permissions")
                print("4. Repository was not properly enabled in Woodpecker CI")
            else:
                print(f"\\n✓ Repository '{repo_name}' is accessible")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Woodpecker CI Access Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List all accessible repositories
    python woodpecker-access-fix.py --list-repos
    
    # Check access to a specific repository
    python woodpecker-access-fix.py --repo-name project-template
    
    # Fix access issues for a repository
    python woodpecker-access-fix.py --repo-name project-template --fix
    
    # Run full diagnostic
    python woodpecker-access-fix.py --repo-name project-template --diagnostic
        """
    )
    
    parser.add_argument(
        "--repo-name",
        help="Name of the repository to check (e.g., 'project-template' or 'y37.space/project-template')"
    )
    
    parser.add_argument(
        "--list-repos",
        action="store_true",
        help="List all accessible repositories"
    )
    
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix repository access issues"
    )
    
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Run comprehensive diagnostic"
    )
    
    args = parser.parse_args()
    
    try:
        manager = WoodpeckerAccessManager()
        
        if args.list_repos:
            manager.list_repositories()
        elif args.diagnostic:
            manager.run_diagnostic(args.repo_name)
        elif args.fix and args.repo_name:
            manager.fix_repository_access(args.repo_name)
        elif args.repo_name:
            manager.check_repository_access(args.repo_name)
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()