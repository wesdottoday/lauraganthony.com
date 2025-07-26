#!/usr/bin/env python3
"""
Documentation Validation Tool for CI Pipeline

This tool validates that documentation is updated when tasks are completed,
while allowing intermediate commits during development.

Usage:
    python docs-validator.py --check-commit <commit-sha>
    python docs-validator.py --validate-task-completion
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DocsValidator:
    """Validates documentation compliance in CI pipeline."""
    
    def __init__(self, project_root: str = None):
        """Initialize documentation validator.
        
        Args:
            project_root: Path to project root. If None, uses current directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.docs_dir = self.project_root / "DOCS"
        self.readme_file = self.project_root / "README.md"
        
    def _get_commit_message(self, commit_sha: str = "HEAD") -> str:
        """Get commit message for specified commit.
        
        Args:
            commit_sha: Commit SHA to check (default: HEAD)
            
        Returns:
            Commit message
        """
        try:
            result = subprocess.run(
                ["git", "show", "-s", "--format=%B", commit_sha],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""
    
    def _get_changed_files(self, commit_sha: str = "HEAD") -> List[str]:
        """Get list of files changed in specified commit.
        
        Args:
            commit_sha: Commit SHA to check (default: HEAD)
            
        Returns:
            List of changed file paths
        """
        try:
            result = subprocess.run(
                ["git", "show", "--name-only", "--format=", commit_sha],
                capture_output=True,
                text=True,
                check=True
            )
            return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        except subprocess.CalledProcessError:
            return []
    
    def _is_task_completion_commit(self, commit_message: str) -> Tuple[bool, Optional[str]]:
        """Check if commit represents task completion.
        
        Args:
            commit_message: Commit message to analyze
            
        Returns:
            Tuple of (is_completion, task_id)
        """
        # Look for patterns indicating task completion
        completion_patterns = [
            r"Complete TASK-(\d+)",
            r"Finish TASK-(\d+)",
            r"TASK-(\d+):.*complete",
            r"TASK-(\d+):.*finished"
        ]
        
        for pattern in completion_patterns:
            match = re.search(pattern, commit_message, re.IGNORECASE)
            if match:
                return True, match.group(1)
        
        return False, None
    
    def _requires_documentation_update(self, changed_files: List[str]) -> bool:
        """Check if changed files require documentation updates.
        
        Args:
            changed_files: List of changed file paths
            
        Returns:
            True if documentation updates are required
        """
        # Files that require documentation updates
        doc_requiring_patterns = [
            r'\.py$',           # Python code changes
            r'requirements.*\.txt$',  # Dependency changes
            r'\.yaml$',         # Configuration changes
            r'\.yml$',          # Configuration changes
            r'\.json$',         # Configuration changes
            r'project\.yaml$',  # Project configuration
        ]
        
        # Files that don't require documentation updates
        doc_exempt_patterns = [
            r'^\.git',          # Git internals
            r'^TASKS/',         # Task files
            r'^BUGS/',          # Bug files  
            r'TODO\.md$',       # Task index
            r'BUGS\.md$',       # Bug index
            r'CLAUDE\.md$',     # Claude context files
            r'test.*\.py$',     # Test files
            r'.*_test\.py$',    # Test files
        ]
        
        for file_path in changed_files:
            # Skip exempt files
            if any(re.search(pattern, file_path) for pattern in doc_exempt_patterns):
                continue
                
            # Check if file requires documentation
            if any(re.search(pattern, file_path) for pattern in doc_requiring_patterns):
                return True
        
        return False
    
    def _check_documentation_updated(self, changed_files: List[str]) -> Tuple[bool, List[str]]:
        """Check if documentation files were updated.
        
        Args:
            changed_files: List of changed file paths
            
        Returns:
            Tuple of (docs_updated, missing_docs)
        """
        doc_files = [
            "README.md",
            "DOCS/docs/getting-started.md",
            "DOCS/docs/api.md",
        ]
        
        updated_docs = []
        missing_docs = []
        
        for doc_file in doc_files:
            if doc_file in changed_files:
                updated_docs.append(doc_file)
            else:
                missing_docs.append(doc_file)
        
        # At least one documentation file should be updated
        docs_updated = len(updated_docs) > 0
        
        return docs_updated, missing_docs
    
    def validate_commit(self, commit_sha: str = "HEAD") -> Dict:
        """Validate documentation compliance for a specific commit.
        
        Args:
            commit_sha: Commit SHA to validate
            
        Returns:
            Validation result dictionary
        """
        commit_message = self._get_commit_message(commit_sha)
        changed_files = self._get_changed_files(commit_sha)
        
        is_task_completion, task_id = self._is_task_completion_commit(commit_message)
        requires_docs = self._requires_documentation_update(changed_files)
        docs_updated, missing_docs = self._check_documentation_updated(changed_files)
        
        result = {
            "commit_sha": commit_sha,
            "commit_message": commit_message[:100] + "..." if len(commit_message) > 100 else commit_message,
            "is_task_completion": is_task_completion,
            "task_id": task_id,
            "requires_documentation": requires_docs,
            "documentation_updated": docs_updated,
            "changed_files": changed_files,
            "missing_docs": missing_docs,
            "validation_passed": True,
            "warnings": [],
            "errors": []
        }
        
        # Validation logic
        if is_task_completion:
            if requires_docs and not docs_updated:
                result["validation_passed"] = False
                result["errors"].append(
                    f"Task completion commit (TASK-{task_id}) with code changes "
                    f"requires documentation updates. Missing: {', '.join(missing_docs)}"
                )
        else:
            # For non-completion commits, only warn about documentation
            if requires_docs and not docs_updated:
                result["warnings"].append(
                    "Code changes detected but no documentation updates. "
                    "Ensure documentation is updated before task completion."
                )
        
        return result
    
    def validate_task_completion_pattern(self) -> Dict:
        """Validate that recent task completions included documentation updates.
        
        Returns:
            Validation result dictionary
        """
        try:
            # Get last 10 commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-10", "--format=%H %s"],
                capture_output=True,
                text=True,
                check=True
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(' ', 1)
                    if len(parts) == 2:
                        commits.append((parts[0], parts[1]))
            
            task_completion_issues = []
            
            for commit_sha, commit_msg in commits:
                validation = self.validate_commit(commit_sha)
                if validation["is_task_completion"] and not validation["validation_passed"]:
                    task_completion_issues.append(validation)
            
            return {
                "validation_passed": len(task_completion_issues) == 0,
                "issues": task_completion_issues,
                "total_commits_checked": len(commits)
            }
            
        except subprocess.CalledProcessError as e:
            return {
                "validation_passed": False,
                "error": f"Git command failed: {e}",
                "issues": [],
                "total_commits_checked": 0
            }


def main():
    """Main entry point for documentation validator."""
    parser = argparse.ArgumentParser(description="Validate documentation compliance")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Check specific commit
    check_parser = subparsers.add_parser('check-commit', help='Check specific commit')
    check_parser.add_argument('--commit', default='HEAD', help='Commit SHA to check')
    check_parser.add_argument('--strict', action='store_true', 
                             help='Fail on warnings as well as errors')
    
    # Validate task completion pattern
    validate_parser = subparsers.add_parser('validate-pattern', 
                                           help='Validate task completion pattern')
    
    # Interactive mode
    interactive_parser = subparsers.add_parser('interactive', 
                                              help='Interactive validation mode')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    validator = DocsValidator()
    
    try:
        if args.command == 'check-commit':
            result = validator.validate_commit(args.commit)
            
            print(f"🔍 Validating commit: {result['commit_sha'][:8]}")
            print(f"📝 Message: {result['commit_message']}")
            print(f"📋 Task completion: {'Yes' if result['is_task_completion'] else 'No'}")
            if result['task_id']:
                print(f"🎯 Task ID: TASK-{result['task_id']}")
            print(f"📖 Requires docs: {'Yes' if result['requires_documentation'] else 'No'}")
            print(f"✏️  Docs updated: {'Yes' if result['documentation_updated'] else 'No'}")
            
            if result['warnings']:
                print(f"\n⚠️  Warnings:")
                for warning in result['warnings']:
                    print(f"   - {warning}")
            
            if result['errors']:
                print(f"\n❌ Errors:")
                for error in result['errors']:
                    print(f"   - {error}")
            
            if result['validation_passed'] and not (args.strict and result['warnings']):
                print(f"\n✅ Validation passed")
                return 0
            else:
                print(f"\n❌ Validation failed")
                return 1
                
        elif args.command == 'validate-pattern':
            result = validator.validate_task_completion_pattern()
            
            print(f"🔍 Validating task completion patterns...")
            print(f"📊 Commits checked: {result['total_commits_checked']}")
            
            if result['issues']:
                print(f"\n❌ Found {len(result['issues'])} task completion issues:")
                for issue in result['issues']:
                    print(f"   - TASK-{issue['task_id']}: {issue['errors'][0]}")
                return 1
            else:
                print(f"\n✅ All recent task completions include proper documentation")
                return 0
                
        elif args.command == 'interactive':
            print("🔍 Interactive Documentation Validation")
            print("=" * 50)
            
            # Check current commit
            current = validator.validate_commit()
            print(f"\nCurrent commit validation:")
            print(f"  Status: {'✅ Pass' if current['validation_passed'] else '❌ Fail'}")
            print(f"  Task completion: {'Yes' if current['is_task_completion'] else 'No'}")
            
            # Check pattern
            pattern = validator.validate_task_completion_pattern()
            print(f"\nRecent pattern validation:")
            print(f"  Status: {'✅ Pass' if pattern['validation_passed'] else '❌ Fail'}")
            print(f"  Issues found: {len(pattern['issues'])}")
            
            return 0 if current['validation_passed'] and pattern['validation_passed'] else 1
            
    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())