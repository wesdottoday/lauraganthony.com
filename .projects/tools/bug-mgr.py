#!/usr/bin/env python3
"""
Bug Manager Tool for Claude Code Integration

This tool manages BUGS.md and BUG files, providing commands to create, update,
and resolve bugs following the project's _BUG-TEMPLATE.md schema.

Usage:
    python bug-mgr.py new --title "Bug Title" --description "Bug description" --severity P1
    python bug-mgr.py update --bug-id 001 --status "investigating"
    python bug-mgr.py resolve --bug-id 001
    
    Or with JSON:
    python bug-mgr.py new --json '{"title": "Bug Title", "description": "...", "severity": "P1"}'
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class BugManager:
    """Manages BUGS.md and BUG files following project schema."""
    
    def __init__(self, project_root: str = None):
        """Initialize BugManager with project root directory.
        
        Args:
            project_root: Path to project root. If None, uses current directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.bugs_file = self.project_root / "BUGS.md"
        self.bugs_dir = self.project_root / "BUGS"
        self.bug_template = self.bugs_dir / "_BUG-TEMPLATE.md"
        
        # Ensure directories exist
        self.bugs_dir.mkdir(exist_ok=True)
        
        # Valid severity levels
        self.valid_severities = ["P0", "P1", "P2"]
        
    def _get_next_bug_id(self) -> str:
        """Get the next sequential bug ID.
        
        Returns:
            String bug ID (e.g., "001", "002")
        """
        existing_bugs = []
        if self.bugs_dir.exists():
            for bug_file in self.bugs_dir.glob("BUG-*.md"):
                match = re.search(r'BUG-(\d+)\.md', bug_file.name)
                if match:
                    existing_bugs.append(int(match.group(1)))
        
        next_id = max(existing_bugs, default=0) + 1
        return f"{next_id:03d}"
    
    def _load_bug_template(self) -> str:
        """Load the BUG template content.
        
        Returns:
            Template content as string
            
        Raises:
            FileNotFoundError: If template doesn't exist
        """
        if not self.bug_template.exists():
            raise FileNotFoundError(f"Bug template not found: {self.bug_template}")
        
        return self.bug_template.read_text()
    
    def _create_bug_content(self, bug_id: str, title: str, description: str,
                           severity: str, background: str = "", environment: str = "",
                           steps: str = "", expected: str = "", actual: str = "",
                           logs: str = "", workaround: str = "", proposed_fix: str = "") -> str:
        """Create bug file content from template.
        
        Args:
            bug_id: Bug ID (e.g., "001")
            title: Bug title
            description: Bug description
            severity: Bug severity (P0, P1, P2)
            background: Background context
            environment: Environment details
            steps: Steps to reproduce
            expected: Expected behavior
            actual: Actual behavior
            logs: Logs and screenshots
            workaround: Temporary workaround
            proposed_fix: Proposed fix
            
        Returns:
            Formatted bug content
        """
        template = self._load_bug_template()
        
        # Replace template placeholders
        content = template.replace(
            "# BUG-nnn: Short bug summary",
            f"# BUG-{bug_id}: {title}"
        )
        
        # Replace description
        content = re.sub(
            r'<REPLACE>\nA brief introduction to the bug:.*?\n</REPLACE>',
            description,
            content,
            flags=re.DOTALL
        )
        
        # Replace severity
        severity_text = f"**{severity}** – "
        if severity == "P0":
            severity_text += "Critical: app crashes or core functionality is broken."
        elif severity == "P1":
            severity_text += "Major: significant issue that degrades functionality but doesn't fully block the app."
        elif severity == "P2":
            severity_text += "Minor: nuisance or cosmetic issue with low impact."
        
        content = re.sub(
            r'<REPLACE>\nSelect one severity.*?\n</REPLACE>',
            severity_text,
            content,
            flags=re.DOTALL
        )
        
        # Replace other sections
        replacements = [
            (r'<REPLACE>\nContext for this bug.*?\n</REPLACE>', background),
            (r'<REPLACE>\nList OS, browser.*?\n</REPLACE>', environment),
            (r'<REPLACE>\n1\. Go to.*?\n</REPLACE>', steps),
            (r'<REPLACE>\nDescribe exactly what should happen.*?\n</REPLACE>', expected),
            (r'<REPLACE>\nDescribe exactly what does happen.*?\n</REPLACE>', actual),
            (r'<REPLACE>\nPaste relevant log excerpts.*?\n</REPLACE>', logs),
            (r'<REPLACE>\nIf known, describe any workaround.*?\n</REPLACE>', workaround),
            (r'<REPLACE>\nIf you have suggestions.*?\n</REPLACE>', proposed_fix)
        ]
        
        for pattern, replacement in replacements:
            if replacement:
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        return content
    
    def _update_bugs_md(self, bug_id: str, title: str, severity: str, action: str = "add") -> None:
        """Update BUGS.md file with bug entry.
        
        Args:
            bug_id: Bug ID
            title: Bug title
            severity: Bug severity
            action: "add" or "resolve"
        """
        if not self.bugs_file.exists():
            # Create BUGS.md if it doesn't exist
            initial_content = """# BUGS

A list of bugs for this project. Utilize the following bug levels:

- [P0]: Breaking bug, something that causes the app not to function at all or cause further breaking behavior.
- [P1]: A bug that is serious, but isn't stopping the app from functioning.
- [P2]: A minor bug that is more annoying than anything

## BUG List

"""
            self.bugs_file.write_text(initial_content)
        
        content = self.bugs_file.read_text()
        
        if action == "add":
            # Add new bug entry
            bug_entry = f"- [ ] BUG-{bug_id}: [{severity}] {title}\n"
            
            if "## BUG List" in content:
                # Insert after BUG List header
                content = content.replace(
                    "## BUG List\n\n",
                    f"## BUG List\n\n{bug_entry}"
                )
            else:
                # Append to end
                content += f"\n{bug_entry}"
        
        elif action == "resolve":
            # Mark bug as resolved
            pattern = f"- \\[ \\] BUG-{bug_id}:"
            replacement = f"- [x] BUG-{bug_id}:"
            content = re.sub(pattern, replacement, content)
        
        self.bugs_file.write_text(content)
    
    def _load_bug_file(self, bug_id: str) -> Tuple[Path, str]:
        """Load existing bug file.
        
        Args:
            bug_id: Bug ID
            
        Returns:
            Tuple of (file_path, content)
            
        Raises:
            FileNotFoundError: If bug file doesn't exist
        """
        bug_file = self.bugs_dir / f"BUG-{bug_id}.md"
        if not bug_file.exists():
            raise FileNotFoundError(f"Bug file not found: {bug_file}")
        
        return bug_file, bug_file.read_text()
    
    def _check_bug_resolution(self, content: str) -> Tuple[bool, List[str]]:
        """Check if bug cleanup items are completed.
        
        Args:
            content: Bug file content
            
        Returns:
            Tuple of (is_resolved, missing_items)
        """
        # Find cleanup section
        cleanup_match = re.search(r'## Cleanup\n\n(.*?)(?=\n## |$)', content, re.DOTALL)
        if not cleanup_match:
            return False, ["No cleanup section found"]
        
        cleanup_content = cleanup_match.group(1)
        
        # Check for incomplete items
        incomplete_items = re.findall(r'- \[ \] (.+)', cleanup_content)
        
        # Check for commit link
        has_commit_link = "git.y37.space" in content and "https://" in content
        
        missing_items = []
        if incomplete_items:
            missing_items.extend(incomplete_items)
        if not has_commit_link:
            missing_items.append("Missing commit link in Final Comments")
        
        return len(missing_items) == 0, missing_items
    
    def new_bug(self, title: str, description: str, severity: str,
                background: str = "", environment: str = "", steps: str = "",
                expected: str = "", actual: str = "", logs: str = "",
                workaround: str = "", proposed_fix: str = "", json_data: Dict = None) -> str:
        """Create a new bug report.
        
        Args:
            title: Bug title
            description: Bug description
            severity: Bug severity (P0, P1, P2)
            background: Background context
            environment: Environment details
            steps: Steps to reproduce
            expected: Expected behavior
            actual: Actual behavior
            logs: Logs and screenshots
            workaround: Temporary workaround
            proposed_fix: Proposed fix
            json_data: Optional JSON data to override parameters
            
        Returns:
            Bug ID of created bug
        """
        # Override with JSON data if provided
        if json_data:
            title = json_data.get("title", title)
            description = json_data.get("description", description)
            severity = json_data.get("severity", severity)
            background = json_data.get("background", background)
            environment = json_data.get("environment", environment)
            steps = json_data.get("steps", steps)
            expected = json_data.get("expected", expected)
            actual = json_data.get("actual", actual)
            logs = json_data.get("logs", logs)
            workaround = json_data.get("workaround", workaround)
            proposed_fix = json_data.get("proposed_fix", proposed_fix)
        
        # Validate required fields
        if not title or not description:
            raise ValueError("Title and description are required")
        
        if severity not in self.valid_severities:
            raise ValueError(f"Severity must be one of: {', '.join(self.valid_severities)}")
        
        # Get next bug ID
        bug_id = self._get_next_bug_id()
        
        # Create bug content
        bug_content = self._create_bug_content(
            bug_id, title, description, severity, background, environment,
            steps, expected, actual, logs, workaround, proposed_fix
        )
        
        # Write bug file
        bug_file = self.bugs_dir / f"BUG-{bug_id}.md"
        bug_file.write_text(bug_content)
        
        # Update BUGS.md
        self._update_bugs_md(bug_id, title, severity, "add")
        
        return bug_id
    
    def update_bug(self, bug_id: str, background: str = None, environment: str = None,
                   steps: str = None, expected: str = None, actual: str = None,
                   logs: str = None, workaround: str = None, proposed_fix: str = None,
                   json_data: Dict = None) -> bool:
        """Update an existing bug report.
        
        Args:
            bug_id: Bug ID to update
            background: Updated background context
            environment: Updated environment details
            steps: Updated steps to reproduce
            expected: Updated expected behavior
            actual: Updated actual behavior
            logs: Updated logs and screenshots
            workaround: Updated temporary workaround
            proposed_fix: Updated proposed fix
            json_data: Optional JSON data to override parameters
            
        Returns:
            True if update successful
        """
        # Override with JSON data if provided
        if json_data:
            background = json_data.get("background", background)
            environment = json_data.get("environment", environment)
            steps = json_data.get("steps", steps)
            expected = json_data.get("expected", expected)
            actual = json_data.get("actual", actual)
            logs = json_data.get("logs", logs)
            workaround = json_data.get("workaround", workaround)
            proposed_fix = json_data.get("proposed_fix", proposed_fix)
        
        # Load existing bug
        bug_file, content = self._load_bug_file(bug_id)
        
        # Update sections
        updates = [
            ("Background", background),
            ("Environment", environment),
            ("Steps to Reproduce", steps),
            ("Expected Behavior", expected),
            ("Actual Behavior", actual),
            ("Logs & Screenshots", logs),
            ("Temporary Workaround", workaround),
            ("Proposed Fix", proposed_fix)
        ]
        
        for section, new_content in updates:
            if new_content:
                pattern = f'(## {section}\n\n).*?(?=\n## |$)'
                replacement = f'\\1{new_content}\n'
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Write updated content
        bug_file.write_text(content)
        
        return True
    
    def resolve_bug(self, bug_id: str) -> bool:
        """Mark a bug as resolved.
        
        Args:
            bug_id: Bug ID to resolve
            
        Returns:
            True if bug is fully resolved and ready to be marked done
            
        Raises:
            ValueError: If bug is not ready to be resolved
        """
        # Load bug file
        bug_file, content = self._load_bug_file(bug_id)
        
        # Check if bug is ready to be resolved
        is_resolved, missing_items = self._check_bug_resolution(content)
        
        if not is_resolved:
            raise ValueError(f"Bug not ready to resolve. Missing: {', '.join(missing_items)}")
        
        # Update BUGS.md to mark as resolved
        self._update_bugs_md(bug_id, "", "", "resolve")
        
        return True
    
    def list_bugs(self) -> List[Dict]:
        """List all bugs with their status.
        
        Returns:
            List of bug dictionaries with id, title, severity, and status
        """
        bugs = []
        
        # Read BUGS.md to get bug status
        bugs_content = ""
        if self.bugs_file.exists():
            bugs_content = self.bugs_file.read_text()
        
        # Find all bug files
        if self.bugs_dir.exists():
            for bug_file in sorted(self.bugs_dir.glob("BUG-*.md")):
                match = re.search(r'BUG-(\d+)\.md', bug_file.name)
                if match:
                    bug_id = match.group(1)
                    
                    # Get title and severity from file
                    content = bug_file.read_text()
                    title_match = re.search(r'# BUG-\d+: (.+)', content)
                    title = title_match.group(1) if title_match else "Unknown"
                    
                    severity_match = re.search(r'\*\*(P[0-2])\*\*', content)
                    severity = severity_match.group(1) if severity_match else "Unknown"
                    
                    # Check status in BUGS.md
                    status = "open"
                    if f"- [x] BUG-{bug_id}:" in bugs_content:
                        status = "resolved"
                    elif f"- [ ] BUG-{bug_id}:" in bugs_content:
                        status = "open"
                    
                    bugs.append({
                        "id": bug_id,
                        "title": title,
                        "severity": severity,
                        "status": status,
                        "file": str(bug_file)
                    })
        
        return bugs


def main():
    """Main entry point for the bug manager tool."""
    parser = argparse.ArgumentParser(
        description="Manage BUGS.md and BUG files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create new bug
    python bug-mgr.py new --title "Memory leak in parser" --description "Parser consumes excessive memory" --severity P1
    
    # Create bug with JSON
    python bug-mgr.py new --json '{"title": "UI bug", "description": "Button misaligned", "severity": "P2"}'
    
    # Update bug with steps to reproduce
    python bug-mgr.py update --bug-id 001 --steps "1. Open app\\n2. Click parse\\n3. Watch memory usage"
    
    # Resolve bug
    python bug-mgr.py resolve --bug-id 001
    
    # List all bugs
    python bug-mgr.py list
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # New bug command
    new_parser = subparsers.add_parser("new", help="Create a new bug report")
    new_parser.add_argument("--title", help="Bug title")
    new_parser.add_argument("--description", help="Bug description")
    new_parser.add_argument("--severity", choices=["P0", "P1", "P2"], help="Bug severity")
    new_parser.add_argument("--background", help="Background context", default="")
    new_parser.add_argument("--environment", help="Environment details", default="")
    new_parser.add_argument("--steps", help="Steps to reproduce", default="")
    new_parser.add_argument("--expected", help="Expected behavior", default="")
    new_parser.add_argument("--actual", help="Actual behavior", default="")
    new_parser.add_argument("--logs", help="Logs and screenshots", default="")
    new_parser.add_argument("--workaround", help="Temporary workaround", default="")
    new_parser.add_argument("--proposed-fix", help="Proposed fix", default="")
    new_parser.add_argument("--json", help="JSON data for bug creation")
    
    # Update bug command
    update_parser = subparsers.add_parser("update", help="Update an existing bug report")
    update_parser.add_argument("--bug-id", required=True, help="Bug ID to update")
    update_parser.add_argument("--background", help="Updated background context")
    update_parser.add_argument("--environment", help="Updated environment details")
    update_parser.add_argument("--steps", help="Updated steps to reproduce")
    update_parser.add_argument("--expected", help="Updated expected behavior")
    update_parser.add_argument("--actual", help="Updated actual behavior")
    update_parser.add_argument("--logs", help="Updated logs and screenshots")
    update_parser.add_argument("--workaround", help="Updated temporary workaround")
    update_parser.add_argument("--proposed-fix", help="Updated proposed fix")
    update_parser.add_argument("--json", help="JSON data for bug update")
    
    # Resolve bug command
    resolve_parser = subparsers.add_parser("resolve", help="Mark a bug as resolved")
    resolve_parser.add_argument("--bug-id", required=True, help="Bug ID to resolve")
    
    # List bugs command
    list_parser = subparsers.add_parser("list", help="List all bugs")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    manager = BugManager()
    
    try:
        if args.command == "new":
            # Parse JSON if provided
            json_data = None
            if args.json:
                json_data = json.loads(args.json)
            
            bug_id = manager.new_bug(
                title=args.title or "",
                description=args.description or "",
                severity=args.severity or "P2",
                background=args.background,
                environment=args.environment,
                steps=args.steps,
                expected=args.expected,
                actual=args.actual,
                logs=args.logs,
                workaround=args.workaround,
                proposed_fix=args.proposed_fix,
                json_data=json_data
            )
            print(f"Created bug BUG-{bug_id}")
        
        elif args.command == "update":
            # Parse JSON if provided
            json_data = None
            if args.json:
                json_data = json.loads(args.json)
            
            success = manager.update_bug(
                bug_id=args.bug_id,
                background=args.background,
                environment=args.environment,
                steps=args.steps,
                expected=args.expected,
                actual=args.actual,
                logs=args.logs,
                workaround=args.workaround,
                proposed_fix=args.proposed_fix,
                json_data=json_data
            )
            if success:
                print(f"Updated bug BUG-{args.bug_id}")
        
        elif args.command == "resolve":
            success = manager.resolve_bug(args.bug_id)
            if success:
                print(f"Resolved bug BUG-{args.bug_id}")
        
        elif args.command == "list":
            bugs = manager.list_bugs()
            if bugs:
                print("Bugs:")
                for bug in bugs:
                    status_icon = "✓" if bug["status"] == "resolved" else "○"
                    print(f"  {status_icon} BUG-{bug['id']}: [{bug['severity']}] {bug['title']}")
            else:
                print("No bugs found")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()