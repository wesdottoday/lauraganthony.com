#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CI Monitoring Tool for Woodpecker CI

This tool monitors Woodpecker CI builds, checks for failures, and can automatically
apply fixes for common build issues. Designed for Claude Code integration.

Usage:
    python ci-monitor.py --watch --commit-sha abc123    # Monitor specific commit
    python ci-monitor.py --latest                       # Check latest build
    python ci-monitor.py --status                       # Get current build status
    python ci-monitor.py --auto-fix                     # Auto-fix failed builds
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CIMonitor:
    """Monitors and manages Woodpecker CI builds with Issues integration."""
    
    def __init__(self):
        """Initialize the CI monitor."""
        self.project_root = Path.cwd()
        self.projects_dir = self.project_root / ".projects"
        self.tools_dir = self.projects_dir / "tools"
        self.env_file = self.projects_dir / ".env"
        self.project_yaml = self.project_root / "project.yaml"
        
        # Load environment and project configuration
        self.env_vars = self._load_env()
        self.project_config = self._load_project_config()
        
        # API configuration
        self.woodpecker_api_key = self.env_vars.get("MAYA_WOODPECKER_API_KEY")
        self.woodpecker_base_url = "https://ci.y37.space"
        
        # Issues integration
        self.issues_enabled = True
        self.issue_mgr_path = self.tools_dir / "issue-mgr.py"
        
        if not self.woodpecker_api_key:
            raise ValueError("MAYA_WOODPECKER_API_KEY not found in .projects/.env")
        
        if not self.issue_mgr_path.exists():
            print("⚠️  Warning: issue-mgr.py not found, Issues integration disabled")
            self.issues_enabled = False
    
    def _load_env(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        if not self.env_file.exists():
            return env_vars
        
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"\'')
                    env_vars[key] = value
        
        return env_vars
    
    def _load_project_config(self) -> Dict[str, str]:
        """Load project configuration from project.yaml."""
        config = {}
        if not self.project_yaml.exists():
            return config
        
        with open(self.project_yaml, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and ':' in line:
                    key, value = line.split(':', 1)
                    config[key.strip()] = value.strip()
        
        return config
    
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
    
    def get_repository_info(self) -> Optional[Dict]:
        """Get repository information from Woodpecker CI."""
        project_alias = self.project_config.get('project_alias')
        if not project_alias:
            print("No project_alias found in project.yaml")
            return None
        
        repo_name = f"y37.space/{project_alias}"
        
        # Get user repositories and find ours
        repos_url = f"{self.woodpecker_base_url}/api/user/repos"
        
        try:
            repos = self._make_api_request(repos_url)
            for repo in repos:
                if repo.get('full_name') == repo_name:
                    return repo
        except ValueError as e:
            print(f"Error getting repository info: {e}")
        
        return None
    
    def get_latest_build(self, repo_id: int) -> Optional[Dict]:
        """Get the latest build for a repository."""
        builds_url = f"{self.woodpecker_base_url}/api/repos/{repo_id}/builds"
        
        try:
            builds = self._make_api_request(builds_url)
            if builds:
                return builds[0]  # Latest build is first
        except ValueError as e:
            print(f"Error getting builds: {e}")
        
        return None
    
    def get_build_by_commit(self, repo_id: int, commit_sha: str) -> Optional[Dict]:
        """Get build for a specific commit."""
        builds_url = f"{self.woodpecker_base_url}/api/repos/{repo_id}/builds"
        
        try:
            builds = self._make_api_request(builds_url)
            for build in builds:
                if build.get('commit', {}).get('sha', '').startswith(commit_sha):
                    return build
        except ValueError as e:
            print(f"Error getting build for commit {commit_sha}: {e}")
        
        return None
    
    def get_build_logs(self, repo_id: int, build_number: int) -> Dict[str, str]:
        """Get logs for all steps in a build."""
        logs = {}
        
        # Get build details to find steps
        build_url = f"{self.woodpecker_base_url}/api/repos/{repo_id}/builds/{build_number}"
        
        try:
            build = self._make_api_request(build_url)
            workflows = build.get('workflows', [])
            
            for workflow in workflows:
                children = workflow.get('children', [])
                for step in children:
                    step_id = step.get('id')
                    step_name = step.get('name', 'unknown')
                    
                    if step_id:
                        log_url = f"{self.woodpecker_base_url}/api/repos/{repo_id}/builds/{build_number}/logs/{step_id}"
                        try:
                            log_response = self._make_api_request(log_url)
                            if isinstance(log_response, list):
                                log_text = '\\n'.join([entry.get('data', '') for entry in log_response])
                            else:
                                log_text = str(log_response)
                            logs[step_name] = log_text
                        except ValueError:
                            logs[step_name] = "Failed to retrieve logs"
            
        except ValueError as e:
            print(f"Error getting build logs: {e}")
        
        return logs
    
    def analyze_build_failure(self, logs: Dict[str, str]) -> List[Dict[str, str]]:
        """Analyze build logs to identify common failure patterns."""
        issues = []
        
        for step_name, log_content in logs.items():
            if not log_content:
                continue
            
            # Check for MkDocs issues
            if 'mkdocs' in step_name.lower() or 'docs' in step_name.lower():
                if "docs_dir should not be the parent directory" in log_content:
                    issues.append({
                        'step': step_name,
                        'type': 'mkdocs_directory_structure',
                        'description': 'MkDocs docs_dir configuration error',
                        'fix': 'Update docs_dir to use subdirectory instead of parent directory'
                    })
                
                if "URL isn't valid, it should include the http://" in log_content:
                    issues.append({
                        'step': step_name,
                        'type': 'mkdocs_url_format',
                        'description': 'MkDocs repo_url requires HTTP/HTTPS format',
                        'fix': 'Convert SSH URLs to HTTPS format in mkdocs.yml'
                    })
                
                if "Config value" in log_content and "isn't an existing directory" in log_content:
                    issues.append({
                        'step': step_name,
                        'type': 'mkdocs_missing_directory',
                        'description': 'MkDocs docs directory not found',
                        'fix': 'Create missing docs directory or fix docs_dir configuration'
                    })
            
            # Check for Python linting issues
            if 'lint' in step_name.lower():
                if "command not found: black" in log_content:
                    issues.append({
                        'step': step_name,
                        'type': 'missing_linting_tools',
                        'description': 'Python linting tools not installed',
                        'fix': 'Add linting tool installation to CI pipeline'
                    })
            
            # Check for test failures
            if 'test' in step_name.lower():
                if "No tests ran" in log_content or "no tests directory found" in log_content:
                    issues.append({
                        'step': step_name,
                        'type': 'missing_tests',
                        'description': 'No test directory or test files found',
                        'fix': 'Create tests directory or update test configuration'
                    })
            
            # Check for general Python errors
            if "ModuleNotFoundError" in log_content:
                module_match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", log_content)
                if module_match:
                    module_name = module_match.group(1)
                    issues.append({
                        'step': step_name,
                        'type': 'missing_dependency',
                        'description': f'Missing Python module: {module_name}',
                        'fix': f'Add {module_name} to requirements.txt or install in CI pipeline'
                    })
        
        return issues
    
    def auto_fix_issues(self, issues: List[Dict[str, str]]) -> bool:
        """Automatically fix common CI issues."""
        if not issues:
            print("No issues found to fix")
            return True
        
        fixed_any = False
        
        for issue in issues:
            issue_type = issue['type']
            print(f"\\nAttempting to fix: {issue['description']}")
            
            try:
                if issue_type == 'mkdocs_directory_structure':
                    fixed = self._fix_mkdocs_directory_structure()
                elif issue_type == 'mkdocs_url_format':
                    fixed = self._fix_mkdocs_url_format()
                elif issue_type == 'mkdocs_missing_directory':
                    fixed = self._fix_mkdocs_missing_directory()
                else:
                    print(f"  No automated fix available for {issue_type}")
                    fixed = False
                
                if fixed:
                    print(f"  ✓ Fixed: {issue['description']}")
                    fixed_any = True
                else:
                    print(f"  ✗ Could not fix: {issue['description']}")
                    
            except Exception as e:
                print(f"  ✗ Error fixing {issue['description']}: {e}")
        
        return fixed_any
    
    def _fix_mkdocs_directory_structure(self) -> bool:
        """Fix MkDocs directory structure issues."""
        docs_dir = self.project_root / "DOCS"
        if not docs_dir.exists():
            return False
        
        mkdocs_yml = docs_dir / "mkdocs.yml"
        if not mkdocs_yml.exists():
            return False
        
        # Read current config
        with open(mkdocs_yml, 'r') as f:
            content = f.read()
        
        # Fix docs_dir configuration
        if "docs_dir: ." in content:
            # Create docs subdirectory if it doesn't exist
            docs_subdir = docs_dir / "docs"
            if not docs_subdir.exists():
                docs_subdir.mkdir()
                
                # Move .md files to docs subdirectory
                for md_file in docs_dir.glob("*.md"):
                    md_file.rename(docs_subdir / md_file.name)
            
            # Update configuration
            content = content.replace("docs_dir: .", "docs_dir: docs")
            
            with open(mkdocs_yml, 'w') as f:
                f.write(content)
            
            return True
        
        return False
    
    def _fix_mkdocs_url_format(self) -> bool:
        """Fix MkDocs URL format issues."""
        docs_dir = self.project_root / "DOCS"
        if not docs_dir.exists():
            return False
        
        mkdocs_yml = docs_dir / "mkdocs.yml"
        if not mkdocs_yml.exists():
            return False
        
        # Read current config
        with open(mkdocs_yml, 'r') as f:
            content = f.read()
        
        # Convert SSH URLs to HTTPS
        ssh_pattern = r'git@([^:]+):([^/]+)/([^.]+)\.git'
        https_replacement = r'https://\\1/\\2/\\3'
        
        new_content = re.sub(ssh_pattern, https_replacement, content)
        
        if new_content != content:
            with open(mkdocs_yml, 'w') as f:
                f.write(new_content)
            return True
        
        return False
    
    def _fix_mkdocs_missing_directory(self) -> bool:
        """Fix missing MkDocs directory issues."""
        docs_dir = self.project_root / "DOCS"
        if not docs_dir.exists():
            return False
        
        mkdocs_yml = docs_dir / "mkdocs.yml"
        if not mkdocs_yml.exists():
            return False
        
        # Check if docs subdirectory exists
        docs_subdir = docs_dir / "docs"
        if not docs_subdir.exists():
            docs_subdir.mkdir()
            
            # Create basic index.md if no docs exist
            index_file = docs_subdir / "index.md"
            if not index_file.exists():
                with open(index_file, 'w') as f:
                    project_name = self.project_config.get('project_name', 'Project')
                    f.write(f"# {project_name}\\n\\nWelcome to the {project_name} documentation!\\n")
            
            return True
        
        return False
    
    def commit_and_push_fixes(self, commit_message: str) -> bool:
        """Commit and push fixes to repository."""
        try:
            # Stage changes
            subprocess.run(['git', 'add', '-A'], check=True, cwd=self.project_root)
            
            # Check if there are changes to commit
            result = subprocess.run(['git', 'diff', '--staged', '--quiet'], 
                                  cwd=self.project_root, capture_output=True)
            
            if result.returncode == 0:
                print("No changes to commit")
                return False
            
            # Commit changes
            subprocess.run(['git', 'commit', '-m', commit_message], 
                          check=True, cwd=self.project_root)
            
            # Push changes
            subprocess.run(['git', 'push'], check=True, cwd=self.project_root)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Git operation failed: {e}")
            return False
    
    def wait_for_build(self, repo_id: int, commit_sha: str, timeout: int = 300) -> Optional[Dict]:
        """Wait for a build to complete for a specific commit."""
        start_time = time.time()
        
        print(f"Waiting for build to start for commit {commit_sha[:8]}...")
        
        while time.time() - start_time < timeout:
            build = self.get_build_by_commit(repo_id, commit_sha)
            
            if build:
                status = build.get('status')
                print(f"Build status: {status}")
                
                if status in ['success', 'failure', 'error', 'killed']:
                    return build
                elif status in ['pending', 'running']:
                    print("Build in progress...")
                    time.sleep(10)
                else:
                    print(f"Unknown build status: {status}")
                    time.sleep(10)
            else:
                print("Build not found yet, waiting...")
                time.sleep(10)
        
        print(f"Timeout waiting for build to complete")
        return None
    
    def _create_ci_failure_issue(self, build_info: Dict, logs: Dict[str, str] = None) -> Optional[int]:
        """Create an Issue for CI build failure with detailed information.
        
        Args:
            build_info: Build information from Woodpecker API
            logs: Build logs by step name (optional)
            
        Returns:
            Issue ID if created successfully, None otherwise
        """
        if not self.issues_enabled:
            print("Issues integration disabled, skipping Issue creation")
            return None
        
        try:
            # Generate Issue title
            commit_sha = build_info.get('commit', {}).get('sha', 'unknown')[:8]
            build_number = build_info.get('number', 'unknown')
            title = f"CI Build #{build_number} failed for commit {commit_sha}"
            
            # Generate comprehensive Issue description
            commit_info = build_info.get('commit', {})
            description_parts = [
                "## Build Failure Report",
                "",
                f"**Status:** {build_info.get('status', 'unknown')}",
                f"**Build Number:** #{build_number}",
                f"**Commit SHA:** {commit_info.get('sha', 'unknown')}",
                f"**Branch:** {commit_info.get('branch', 'unknown')}",
                f"**Started:** {build_info.get('started', 'unknown')}",
                f"**Finished:** {build_info.get('finished', 'unknown')}",
                "",
                f"## Commit Details",
                f"**Message:** {commit_info.get('message', 'unknown')}",
                f"**Author:** {commit_info.get('author', 'unknown')}",
                "",
                f"## Build Steps Status"
            ]
            
            # Add step status information
            steps = build_info.get('steps', [])
            failed_steps = []
            
            for step in steps:
                step_name = step.get('name', 'unknown')
                step_status = step.get('state', 'unknown')
                step_exit_code = step.get('exit_code', 'unknown')
                
                if step_status == 'success':
                    icon = "✅"
                elif step_status == 'failure':
                    icon = "❌"
                    failed_steps.append(step_name)
                else:
                    icon = "⏸️"
                
                description_parts.append(f"- {icon} **{step_name}**: {step_status} (exit code: {step_exit_code})")
            
            # Add build logs summary if available
            if logs:
                description_parts.extend([
                    "",
                    "## Failed Steps Details"
                ])
                
                for step_name in failed_steps:
                    if step_name in logs and logs[step_name]:
                        log_content = logs[step_name]
                        # Truncate very long logs for the Issue description
                        if len(log_content) > 1000:
                            log_content = log_content[:1000] + "\n... (truncated)"
                        
                        description_parts.extend([
                            f"",
                            f"### {step_name} Output",
                            "```",
                            log_content.strip(),
                            "```"
                        ])
            
            description_parts.extend([
                "",
                "## Next Steps",
                "1. Review the build logs above for specific error details",
                "2. Identify the root cause of the failure",
                "3. Apply appropriate fixes",
                "4. Re-run the build to verify the fix",
                "",
                f"## Build URL",
                f"[View full build details]({self.woodpecker_base_url}/repos/{build_info.get('repo_id', 'unknown')}/build/{build_number})",
                "",
                "---",
                "*Auto-created by CI Monitor on build failure*"
            ])
            
            description = "\n".join(description_parts)
            
            # Determine severity based on failure type
            severity = "P1"  # Default to high priority for CI failures
            
            # Critical if security step failed
            if any('security' in step.get('name', '').lower() for step in steps if step.get('state') == 'failure'):
                severity = "P0"
            # Medium if only lint/docs failed
            elif all('lint' in step.get('name', '').lower() or 'docs' in step.get('name', '').lower() 
                     for step in steps if step.get('state') == 'failure'):
                severity = "P2"
            
            # Create the Issue
            cmd = [
                "python3", str(self.issue_mgr_path), "new",
                "--type", "bug",
                "--title", title,
                "--description", description,
                "--severity", severity,
                "--environment", f"Woodpecker CI Build #{build_number}",
                "--steps", "1. Commit changes to repository\n2. CI build triggers automatically\n3. Build fails with errors",
                "--expected", "Build should complete successfully with all steps passing",
                "--actual", f"Build failed with status: {build_info.get('status', 'unknown')}"
            ]
            
            # Execute Issue creation
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse Issue ID from output
            for line in result.stdout.strip().split('\n'):
                if line.startswith("Created issue #"):
                    issue_match = re.search(r'#(\d+)', line)
                    if issue_match:
                        issue_id = int(issue_match.group(1))
                        print(f"📋 Created Issue #{issue_id} for build failure: {title}")
                        return issue_id
            
            print("Issue created but couldn't parse Issue ID")
            return None
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating CI failure Issue: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return None
        except Exception as e:
            print(f"Unexpected error creating CI failure Issue: {e}")
            return None
    
    def _create_specific_bug_reports(self, build_info: Dict, logs: Dict[str, str]) -> List[int]:
        """Analyze build logs and create specific bug reports for identified issues.
        
        Args:
            build_info: Build information
            logs: Build logs by step name
            
        Returns:
            List of created Issue IDs
        """
        if not self.issues_enabled:
            return []
        
        # Analyze the logs for specific problems
        issues_found = self.analyze_build_failure(logs)
        created_issues = []
        
        for issue in issues_found:
            try:
                title = f"CI Issue: {issue['description']}"
                
                description_parts = [
                    "## Problem Description",
                    issue['description'],
                    "",
                    "## Build Context",
                    f"- **Build Step:** {issue['step']}",
                    f"- **Issue Type:** {issue['type']}",
                    f"- **Build Number:** #{build_info.get('number', 'unknown')}",
                    f"- **Commit:** {build_info.get('commit', {}).get('sha', 'unknown')[:8]}",
                    "",
                    "## Suggested Fix",
                    issue['fix'],
                    "",
                    "## Reproduction Steps",
                    f"1. Make a commit that triggers CI",
                    f"2. Wait for build to reach the '{issue['step']}' step",
                    f"3. Observe the failure pattern",
                    "",
                    "## Expected Behavior",
                    f"The '{issue['step']}' step should complete successfully",
                    "",
                    "## Actual Behavior",
                    f"The '{issue['step']}' step fails with: {issue['description']}",
                    "",
                    "---",
                    "*Auto-created by CI Monitor issue analysis*"
                ]
                
                description = "\n".join(description_parts)
                
                # Determine severity
                severity = "P2"  # Most CI configuration issues are medium
                if 'security' in issue['step'].lower():
                    severity = "P0"
                elif 'test' in issue['step'].lower() or 'build' in issue['step'].lower():
                    severity = "P1"
                
                # Create the specific bug Issue
                cmd = [
                    "python3", str(self.issue_mgr_path), "new",
                    "--type", "bug", 
                    "--title", title,
                    "--description", description,
                    "--severity", severity,
                    "--environment", f"Woodpecker CI - {issue['step']} step",
                    "--steps", f"1. Trigger CI build\n2. Wait for {issue['step']} step\n3. Observe specific failure",
                    "--expected", f"{issue['step']} step completes successfully",
                    "--actual", f"{issue['step']} step fails: {issue['description']}"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Parse Issue ID
                for line in result.stdout.strip().split('\n'):
                    if line.startswith("Created issue #"):
                        issue_match = re.search(r'#(\d+)', line)
                        if issue_match:
                            issue_id = int(issue_match.group(1))
                            created_issues.append(issue_id)
                            print(f"🐛 Created specific Bug #{issue_id}: {issue['description']}")
                            break
                
            except Exception as e:
                print(f"Error creating specific bug report for {issue['type']}: {e}")
        
        return created_issues
    
    def monitor_and_fix(self, commit_sha: Optional[str] = None, auto_fix: bool = True, 
                       create_issues: bool = True) -> bool:
        """Monitor CI build and auto-fix issues if requested."""
        print("=== CI Build Monitor ===")
        
        # Get repository info
        repo_info = self.get_repository_info()
        if not repo_info:
            print("Could not find repository in Woodpecker CI")
            return False
        
        repo_id = repo_info['id']
        repo_name = repo_info['full_name']
        print(f"Monitoring repository: {repo_name} (ID: {repo_id})")
        
        # Get build to monitor
        if commit_sha:
            build = self.wait_for_build(repo_id, commit_sha)
        else:
            build = self.get_latest_build(repo_id)
        
        if not build:
            print("No build found to monitor")
            return False
        
        build_number = build['number']
        build_status = build['status']
        commit_info = build.get('commit', {})
        build_commit = commit_info.get('sha', 'unknown')[:8]
        
        print(f"\\nBuild #{build_number} (commit: {build_commit})")
        print(f"Status: {build_status}")
        print(f"Message: {commit_info.get('message', 'No message')}")
        
        if build_status == 'success':
            print("\\n✓ Build successful - no action needed")
            return True
        
        if build_status in ['failure', 'error']:
            print(f"\\n✗ Build failed with status: {build_status}")
            
            # Get build logs
            print("Analyzing build logs...")
            logs = self.get_build_logs(repo_id, build_number)
            
            # Create Issues for the build failure if enabled
            if create_issues:
                print("\\n📋 Creating Issues for build failure...")
                
                # Add repo_id to build info for Issue creation
                build['repo_id'] = repo_id
                
                # Create main CI failure Issue
                main_issue_id = self._create_ci_failure_issue(build, logs)
                
                if logs:
                    # Analyze for specific issues and create targeted bug reports
                    specific_issues = self._create_specific_bug_reports(build, logs)
                    
                    if specific_issues:
                        print(f"📋 Created {len(specific_issues)} specific bug reports: {specific_issues}")
                
                if main_issue_id:
                    print(f"📋 Main CI failure tracked in Issue #{main_issue_id}")
            
            if logs:
                # Analyze for common issues
                issues = self.analyze_build_failure(logs)
                
                if issues:
                    print(f"\\nFound {len(issues)} issue(s):")
                    for i, issue in enumerate(issues, 1):
                        print(f"  {i}. {issue['description']} (Step: {issue['step']})")
                        print(f"     Fix: {issue['fix']}")
                    
                    if auto_fix:
                        print("\\nAttempting automatic fixes...")
                        fixed = self.auto_fix_issues(issues)
                        
                        if fixed:
                            commit_msg = f"Auto-fix CI build issues\\n\\nFixed issues found in build #{build_number}:\\n"
                            for issue in issues:
                                commit_msg += f"- {issue['description']}\\n"
                            commit_msg += "\\n🤖 Generated with [Claude Code](https://claude.ai/code)\\n\\nCo-Authored-By: Claude <noreply@anthropic.com>"
                            
                            success = self.commit_and_push_fixes(commit_msg)
                            if success:
                                print("\\n✓ Fixes committed and pushed")
                                print("New build should start automatically")
                                return True
                            else:
                                print("\\n✗ Failed to commit fixes")
                        else:
                            print("\\n✗ No fixes could be applied automatically")
                else:
                    print("\\nNo recognizable issues found in build logs")
                    print("Manual investigation may be required")
            else:
                print("Could not retrieve build logs")
            
            return False
        
        print(f"\\nBuild status '{build_status}' - monitoring not applicable")
        return True
    
    def get_ci_status(self) -> Dict:
        """Get current CI status for the project."""
        repo_info = self.get_repository_info()
        if not repo_info:
            return {'error': 'Repository not found'}
        
        latest_build = self.get_latest_build(repo_info['id'])
        if not latest_build:
            return {'error': 'No builds found'}
        
        return {
            'repository': repo_info['full_name'],
            'latest_build': {
                'number': latest_build['number'],
                'status': latest_build['status'],
                'commit': latest_build.get('commit', {}).get('sha', 'unknown')[:8],
                'message': latest_build.get('commit', {}).get('message', 'No message'),
                'url': f"{self.woodpecker_base_url}/repos/{repo_info['id']}/builds/{latest_build['number']}"
            }
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor and manage Woodpecker CI builds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Monitor latest build and auto-fix issues
    python ci-monitor.py --latest --auto-fix
    
    # Monitor specific commit build
    python ci-monitor.py --watch --commit-sha abc123 --auto-fix
    
    # Get current build status
    python ci-monitor.py --status
    
    # Monitor without auto-fixing
    python ci-monitor.py --latest
        """
    )
    
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Monitor the latest build"
    )
    
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch for build completion (use with --commit-sha)"
    )
    
    parser.add_argument(
        "--commit-sha",
        help="Specific commit SHA to monitor (first 7+ characters)"
    )
    
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Automatically fix common build issues"
    )
    
    parser.add_argument(
        "--create-issues",
        action="store_true",
        default=True,
        help="Create Issues for build failures (default: enabled)"
    )
    
    parser.add_argument(
        "--no-create-issues",
        action="store_true",
        help="Disable automatic Issue creation for build failures"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Get current CI status"
    )
    
    args = parser.parse_args()
    
    if not any([args.latest, args.watch, args.status]):
        parser.print_help()
        return
    
    try:
        monitor = CIMonitor()
        
        if args.status:
            status = monitor.get_ci_status()
            if 'error' in status:
                print(f"Error: {status['error']}")
            else:
                print(f"Repository: {status['repository']}")
                build = status['latest_build']
                print(f"Latest build: #{build['number']} - {build['status']}")
                print(f"Commit: {build['commit']} - {build['message']}")
                print(f"URL: {build['url']}")
        
        elif args.latest:
            create_issues = not args.no_create_issues
            monitor.monitor_and_fix(auto_fix=args.auto_fix, create_issues=create_issues)
        
        elif args.watch:
            if not args.commit_sha:
                print("Error: --commit-sha required with --watch")
                return
            create_issues = not args.no_create_issues
            monitor.monitor_and_fix(commit_sha=args.commit_sha, auto_fix=args.auto_fix, create_issues=create_issues)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()