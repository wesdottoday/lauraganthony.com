#!/usr/bin/env python3
"""
Migration Tool for Converting File-based Tasks/Bugs to Gitea Issues

This tool migrates existing TASK-*.md and BUG-*.md files to Gitea Issues,
preserving all important metadata and context.

Usage:
    python migration-tool.py migrate-tasks
    python migration-tool.py migrate-bugs
    python migration-tool.py migrate-all --dry-run
    python migration-tool.py cleanup
"""

import argparse
import json
import os
import re
import shutil
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class TaskBugMigrator:
    """Migrates file-based tasks and bugs to Gitea Issues."""
    
    def __init__(self, project_root: str = None, dry_run: bool = False):
        """Initialize migrator.
        
        Args:
            project_root: Path to project root. If None, uses current directory.
            dry_run: If True, show what would be done without making changes.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.dry_run = dry_run
        self.tasks_dir = self.project_root / "TASKS"
        self.bugs_dir = self.project_root / "BUGS"
        self.tools_dir = self.project_root / ".projects" / "tools"
        
        # Migration results tracking
        self.migration_results = {
            "tasks": {"migrated": [], "skipped": [], "errors": []},
            "bugs": {"migrated": [], "skipped": [], "errors": []}
        }
    
    def _parse_task_file(self, file_path: Path) -> Dict:
        """Parse a TASK-*.md file and extract metadata.
        
        Args:
            file_path: Path to task file
            
        Returns:
            Dictionary with task metadata
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Task file not found: {file_path}")
        
        content = file_path.read_text(encoding='utf-8')
        
        # Extract task number and title from first line
        first_line = content.split('\n')[0]
        task_match = re.match(r'^# TASK-(\d+): (.+)$', first_line)
        if not task_match:
            raise ValueError(f"Invalid task format in {file_path}")
        
        task_id = task_match.group(1)
        title = task_match.group(2)
        
        # Extract main description (after title, before ## sections)
        description_match = re.search(r'^# TASK-\d+: .+\n\n(.+?)\n\n## ', content, re.DOTALL)
        description = description_match.group(1).strip() if description_match else ""
        
        # Extract sections
        sections = self._extract_sections(content)
        
        # Determine completion status from cleanup section
        is_completed = self._is_task_completed(sections.get("Cleanup", ""))
        
        # Extract commit link if present
        commit_link = self._extract_commit_link(sections.get("Final Comments", ""))
        
        return {
            "task_id": task_id,
            "title": title,
            "description": description,
            "sections": sections,
            "is_completed": is_completed,
            "commit_link": commit_link,
            "file_path": str(file_path)
        }
    
    def _parse_bug_file(self, file_path: Path) -> Dict:
        """Parse a BUG-*.md file and extract metadata.
        
        Args:
            file_path: Path to bug file
            
        Returns:
            Dictionary with bug metadata
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Bug file not found: {file_path}")
        
        content = file_path.read_text(encoding='utf-8')
        
        # Extract bug number and title from first line
        first_line = content.split('\n')[0]
        bug_match = re.match(r'^# BUG-(\d+): (.+)$', first_line)
        if not bug_match:
            raise ValueError(f"Invalid bug format in {file_path}")
        
        bug_id = bug_match.group(1)
        title = bug_match.group(2)
        
        # Extract main description (after title, before ## sections)
        description_match = re.search(r'^# BUG-\d+: .+\n\n(.+?)\n\n## ', content, re.DOTALL)
        description = description_match.group(1).strip() if description_match else ""
        
        # Extract sections
        sections = self._extract_sections(content)
        
        # Extract severity
        severity = self._extract_severity(sections.get("Severity", ""))
        
        # Determine resolution status from cleanup section  
        is_resolved = self._is_bug_resolved(sections.get("Cleanup", ""))
        
        # Extract commit link if present
        commit_link = self._extract_commit_link(sections.get("Final Comments", ""))
        
        return {
            "bug_id": bug_id,
            "title": title,
            "description": description,
            "severity": severity,
            "sections": sections,
            "is_resolved": is_resolved,
            "commit_link": commit_link,
            "file_path": str(file_path)
        }
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract markdown sections from content.
        
        Args:
            content: File content
            
        Returns:
            Dictionary mapping section names to content
        """
        sections = {}
        
        # Split content by ## headers
        parts = re.split(r'\n## ', content)
        
        for part in parts[1:]:  # Skip the first part (before first ##)
            lines = part.split('\n')
            section_name = lines[0]
            section_content = '\n'.join(lines[1:]).strip()
            sections[section_name] = section_content
        
        return sections
    
    def _extract_severity(self, severity_section: str) -> str:
        """Extract severity from bug severity section.
        
        Args:
            severity_section: Content of severity section
            
        Returns:
            Severity level (P0, P1, P2)
        """
        # Look for bold severity indicators
        severity_match = re.search(r'\*\*(P[012])\*\*', severity_section)
        if severity_match:
            return severity_match.group(1)
        
        # Look for plain text indicators
        for severity in ['P0', 'P1', 'P2']:
            if severity in severity_section:
                return severity
        
        return 'P2'  # Default to P2 if not found
    
    def _is_task_completed(self, cleanup_section: str) -> bool:
        """Check if task is completed based on cleanup section.
        
        Args:
            cleanup_section: Content of cleanup section
            
        Returns:
            True if task appears to be completed
        """
        # Look for completed checkboxes
        completed_items = len(re.findall(r'- \[x\]', cleanup_section))
        total_items = len(re.findall(r'- \[[x ]\]', cleanup_section))
        
        # Consider completed if most items are checked off
        return completed_items > 0 and completed_items >= total_items * 0.8
    
    def _is_bug_resolved(self, cleanup_section: str) -> bool:
        """Check if bug is resolved based on cleanup section.
        
        Args:
            cleanup_section: Content of cleanup section
            
        Returns:
            True if bug appears to be resolved
        """
        # Same logic as task completion
        return self._is_task_completed(cleanup_section)
    
    def _extract_commit_link(self, final_comments: str) -> Optional[str]:
        """Extract commit link from final comments section.
        
        Args:
            final_comments: Content of final comments section
            
        Returns:
            Commit link URL if found
        """
        # Look for commit links
        link_match = re.search(r'https://git\.y37\.space/[^)\s]+/commit/[a-f0-9]+', final_comments)
        return link_match.group(0) if link_match else None
    
    def _generate_issue_description(self, item_type: str, data: Dict) -> str:
        """Generate Issue description from task/bug data.
        
        Args:
            item_type: 'task' or 'bug'
            data: Parsed task/bug data
            
        Returns:
            Formatted Issue description
        """
        description_parts = [data["description"]]
        
        if item_type == "task":
            # Add task-specific sections
            if "Project Context" in data["sections"]:
                description_parts.append(f"## Project Context\n\n{data['sections']['Project Context']}")
            
            if "Task Requirements" in data["sections"]:
                description_parts.append(f"## Requirements\n\n{data['sections']['Task Requirements']}")
            
            if "Implementation Plan" in data["sections"]:
                description_parts.append(f"## Implementation Plan\n\n{data['sections']['Implementation Plan']}")
        
        elif item_type == "bug":
            # Add bug-specific sections
            if "Environment" in data["sections"]:
                description_parts.append(f"## Environment\n\n{data['sections']['Environment']}")
            
            if "Steps to Reproduce" in data["sections"]:
                description_parts.append(f"## Steps to Reproduce\n\n{data['sections']['Steps to Reproduce']}")
            
            if "Expected Behavior" in data["sections"]:
                description_parts.append(f"## Expected Behavior\n\n{data['sections']['Expected Behavior']}")
            
            if "Actual Behavior" in data["sections"]:
                description_parts.append(f"## Actual Behavior\n\n{data['sections']['Actual Behavior']}")
        
        # Add commit link if present
        if data.get("commit_link"):
            description_parts.append(f"## Related Commit\n\n{data['commit_link']}")
        
        # Add migration metadata
        description_parts.append(f"---\n*Migrated from {data['file_path']} on {datetime.now().strftime('%Y-%m-%d')}*")
        
        return "\n\n".join(description_parts)
    
    def _create_gitea_issue(self, issue_type: str, title: str, description: str, 
                          severity: str = None, state: str = "open") -> Optional[Dict]:
        """Create a Gitea Issue using issue-mgr.py.
        
        Args:
            issue_type: 'task' or 'bug'
            title: Issue title
            description: Issue description
            severity: Bug severity (for bugs)
            state: Issue state ('open' or 'closed')
            
        Returns:
            Issue creation result or None if dry run
        """
        if self.dry_run:
            print(f"[DRY RUN] Would create {issue_type} Issue: {title}")
            return {"number": "XXX", "html_url": "https://example.com/issue/XXX"}
        
        # Prepare issue-mgr.py command
        cmd = [
            "python3", str(self.tools_dir / "issue-mgr.py"), "new",
            "--type", issue_type,
            "--title", title,
            "--description", description
        ]
        
        if severity and issue_type == "bug":
            cmd.extend(["--severity", severity])
        
        try:
            # Create the Issue
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse the output to get Issue URL and number
            output_lines = result.stdout.strip().split('\n')
            issue_info = {}
            
            for line in output_lines:
                if line.startswith("Created issue #"):
                    number_match = re.search(r'#(\d+)', line)
                    if number_match:
                        issue_info["number"] = number_match.group(1)
                elif line.startswith("URL: "):
                    issue_info["html_url"] = line.replace("URL: ", "")
            
            # Close the Issue if it was completed/resolved
            if state == "closed" and "number" in issue_info:
                close_cmd = [
                    "python3", str(self.tools_dir / "issue-mgr.py"), "close",
                    "--issue-id", issue_info["number"],
                    "--comment", f"Migrated as completed from file-based system"
                ]
                subprocess.run(close_cmd, capture_output=True, text=True, check=True)
            
            return issue_info
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating Issue: {e}")
            print(f"Command output: {e.stdout}")
            print(f"Command error: {e.stderr}")
            return None
    
    def migrate_tasks(self) -> Dict:
        """Migrate all tasks to Gitea Issues.
        
        Returns:
            Migration results
        """
        print("🔄 Migrating tasks to Gitea Issues...")
        
        if not self.tasks_dir.exists():
            print(f"❌ Tasks directory not found: {self.tasks_dir}")
            return self.migration_results
        
        # Find all task files
        task_files = sorted(self.tasks_dir.glob("TASK-*.md"))
        
        if not task_files:
            print("ℹ️  No task files found to migrate")
            return self.migration_results
        
        print(f"📋 Found {len(task_files)} task files to migrate")
        
        for task_file in task_files:
            try:
                print(f"\n📝 Processing {task_file.name}...")
                
                # Parse task file
                task_data = self._parse_task_file(task_file)
                
                # Generate Issue description
                description = self._generate_issue_description("task", task_data)
                
                # Determine Issue state
                state = "closed" if task_data["is_completed"] else "open"
                
                # Create Gitea Issue
                issue_result = self._create_gitea_issue(
                    issue_type="task",
                    title=task_data["title"],
                    description=description,
                    state=state
                )
                
                if issue_result:
                    migration_info = {
                        "file": task_file.name,
                        "task_id": task_data["task_id"],
                        "issue_number": issue_result["number"],
                        "issue_url": issue_result["html_url"],
                        "state": state
                    }
                    self.migration_results["tasks"]["migrated"].append(migration_info)
                    print(f"✅ Created Issue #{issue_result['number']}: {task_data['title']}")
                else:
                    self.migration_results["tasks"]["errors"].append({
                        "file": task_file.name,
                        "error": "Failed to create Issue"
                    })
                    print(f"❌ Failed to create Issue for {task_file.name}")
                
            except Exception as e:
                error_info = {"file": task_file.name, "error": str(e)}
                self.migration_results["tasks"]["errors"].append(error_info)
                print(f"❌ Error processing {task_file.name}: {e}")
        
        return self.migration_results
    
    def migrate_bugs(self) -> Dict:
        """Migrate all bugs to Gitea Issues.
        
        Returns:
            Migration results
        """
        print("🔄 Migrating bugs to Gitea Issues...")
        
        if not self.bugs_dir.exists():
            print(f"❌ Bugs directory not found: {self.bugs_dir}")
            return self.migration_results
        
        # Find all bug files (excluding template)
        bug_files = [f for f in sorted(self.bugs_dir.glob("BUG-*.md")) 
                    if not f.name.startswith("_")]
        
        if not bug_files:
            print("ℹ️  No bug files found to migrate")
            return self.migration_results
        
        print(f"🐛 Found {len(bug_files)} bug files to migrate")
        
        for bug_file in bug_files:
            try:
                print(f"\n🐛 Processing {bug_file.name}...")
                
                # Parse bug file
                bug_data = self._parse_bug_file(bug_file)
                
                # Generate Issue description
                description = self._generate_issue_description("bug", bug_data)
                
                # Determine Issue state
                state = "closed" if bug_data["is_resolved"] else "open"
                
                # Create Gitea Issue
                issue_result = self._create_gitea_issue(
                    issue_type="bug",
                    title=bug_data["title"],
                    description=description,
                    severity=bug_data["severity"],
                    state=state
                )
                
                if issue_result:
                    migration_info = {
                        "file": bug_file.name,
                        "bug_id": bug_data["bug_id"],
                        "issue_number": issue_result["number"],
                        "issue_url": issue_result["html_url"],
                        "severity": bug_data["severity"],
                        "state": state
                    }
                    self.migration_results["bugs"]["migrated"].append(migration_info)
                    print(f"✅ Created Issue #{issue_result['number']}: {bug_data['title']}")
                else:
                    self.migration_results["bugs"]["errors"].append({
                        "file": bug_file.name,
                        "error": "Failed to create Issue"
                    })
                    print(f"❌ Failed to create Issue for {bug_file.name}")
                
            except Exception as e:
                error_info = {"file": bug_file.name, "error": str(e)}
                self.migration_results["bugs"]["errors"].append(error_info)
                print(f"❌ Error processing {bug_file.name}: {e}")
        
        return self.migration_results
    
    def generate_migration_report(self) -> str:
        """Generate a comprehensive migration report.
        
        Returns:
            Formatted migration report
        """
        report_lines = ["# Migration Report", ""]
        
        # Task migration summary
        tasks = self.migration_results["tasks"]
        report_lines.extend([
            "## Tasks Migration",
            f"- **Migrated**: {len(tasks['migrated'])} tasks",
            f"- **Skipped**: {len(tasks['skipped'])} tasks", 
            f"- **Errors**: {len(tasks['errors'])} tasks",
            ""
        ])
        
        if tasks["migrated"]:
            report_lines.append("### Migrated Tasks")
            for task in tasks["migrated"]:
                report_lines.append(f"- {task['file']} → Issue #{task['issue_number']} ({task['state']})")
            report_lines.append("")
        
        # Bug migration summary
        bugs = self.migration_results["bugs"]
        report_lines.extend([
            "## Bugs Migration",
            f"- **Migrated**: {len(bugs['migrated'])} bugs",
            f"- **Skipped**: {len(bugs['skipped'])} bugs",
            f"- **Errors**: {len(bugs['errors'])} bugs",
            ""
        ])
        
        if bugs["migrated"]:
            report_lines.append("### Migrated Bugs")
            for bug in bugs["migrated"]:
                report_lines.append(f"- {bug['file']} → Issue #{bug['issue_number']} ({bug['severity']}, {bug['state']})")
            report_lines.append("")
        
        # Errors
        all_errors = tasks["errors"] + bugs["errors"]
        if all_errors:
            report_lines.append("## Errors")
            for error in all_errors:
                report_lines.append(f"- {error['file']}: {error['error']}")
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def cleanup_old_files(self) -> None:
        """Archive or remove old task and bug files after migration.
        
        This creates an archive directory and moves old files there.
        """
        if self.dry_run:
            print("[DRY RUN] Would archive old files to .migration_archive/")
            return
        
        archive_dir = self.project_root / ".migration_archive"
        archive_dir.mkdir(exist_ok=True)
        
        # Create timestamped subdirectory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_archive = archive_dir / f"migration_{timestamp}"
        timestamped_archive.mkdir(exist_ok=True)
        
        # Archive TASKS directory
        if self.tasks_dir.exists():
            shutil.copytree(self.tasks_dir, timestamped_archive / "TASKS")
            print(f"📁 Archived TASKS directory to {timestamped_archive / 'TASKS'}")
        
        # Archive BUGS directory
        if self.bugs_dir.exists():
            shutil.copytree(self.bugs_dir, timestamped_archive / "BUGS")
            print(f"📁 Archived BUGS directory to {timestamped_archive / 'BUGS'}")
        
        # Archive index files
        for index_file in ["TODO.md", "BUGS.md"]:
            index_path = self.project_root / index_file
            if index_path.exists():
                shutil.copy2(index_path, timestamped_archive / index_file)
                print(f"📄 Archived {index_file} to {timestamped_archive / index_file}")


def main():
    """Main entry point for migration tool."""
    parser = argparse.ArgumentParser(description="Migrate tasks and bugs to Gitea Issues")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Migrate tasks command
    migrate_tasks_parser = subparsers.add_parser('migrate-tasks', help='Migrate tasks to Issues')
    migrate_tasks_parser.add_argument('--dry-run', action='store_true', 
                                     help='Show what would be done without making changes')
    
    # Migrate bugs command
    migrate_bugs_parser = subparsers.add_parser('migrate-bugs', help='Migrate bugs to Issues')
    migrate_bugs_parser.add_argument('--dry-run', action='store_true',
                                    help='Show what would be done without making changes')
    
    # Migrate all command
    migrate_all_parser = subparsers.add_parser('migrate-all', help='Migrate both tasks and bugs')
    migrate_all_parser.add_argument('--dry-run', action='store_true',
                                   help='Show what would be done without making changes')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Archive old files after migration')
    cleanup_parser.add_argument('--dry-run', action='store_true',
                               help='Show what would be done without making changes')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Show migration report')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    migrator = TaskBugMigrator(dry_run=getattr(args, 'dry_run', False))
    
    try:
        if args.command == 'migrate-tasks':
            migrator.migrate_tasks()
            
        elif args.command == 'migrate-bugs':
            migrator.migrate_bugs()
            
        elif args.command == 'migrate-all':
            migrator.migrate_tasks()
            migrator.migrate_bugs()
            
        elif args.command == 'cleanup':
            migrator.cleanup_old_files()
            
        elif args.command == 'report':
            report = migrator.generate_migration_report()
            print(report)
            return 0
        
        # Print migration report
        if args.command in ['migrate-tasks', 'migrate-bugs', 'migrate-all']:
            print("\n" + "="*50)
            print(migrator.generate_migration_report())
        
        return 0
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())