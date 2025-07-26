#!/usr/bin/env python3
"""
Todo Manager Tool for Claude Code Integration

This tool manages TODO.md and TASK files, providing commands to create, update,
and complete tasks following the project's TASK-TEMPLATE.md schema.

Usage:
    python todo-mgr.py new --title "Task Title" --description "Task description"
    python todo-mgr.py update --task-id 001 --plan "Updated implementation plan"
    python todo-mgr.py complete --task-id 001
    
    Or with JSON:
    python todo-mgr.py new --json '{"title": "Task Title", "description": "..."}'
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class TodoManager:
    """Manages TODO.md and TASK files following project schema."""
    
    def __init__(self, project_root: str = None):
        """Initialize TodoManager with project root directory.
        
        Args:
            project_root: Path to project root. If None, uses current directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.todo_file = self.project_root / "TODO.md"
        self.tasks_dir = self.project_root / "TASKS"
        self.task_template = self.tasks_dir / "_TASK-TEMPLATE.md"
        
        # Ensure directories exist
        self.tasks_dir.mkdir(exist_ok=True)
        
    def _get_next_task_id(self) -> str:
        """Get the next sequential task ID.
        
        Returns:
            String task ID (e.g., "001", "002")
        """
        existing_tasks = []
        if self.tasks_dir.exists():
            for task_file in self.tasks_dir.glob("TASK-*.md"):
                match = re.search(r'TASK-(\d+)\.md', task_file.name)
                if match:
                    existing_tasks.append(int(match.group(1)))
        
        next_id = max(existing_tasks, default=0) + 1
        return f"{next_id:03d}"
    
    def _load_task_template(self) -> str:
        """Load the TASK template content.
        
        Returns:
            Template content as string
            
        Raises:
            FileNotFoundError: If template doesn't exist
        """
        if not self.task_template.exists():
            raise FileNotFoundError(f"Task template not found: {self.task_template}")
        
        return self.task_template.read_text()
    
    def _create_task_content(self, task_id: str, title: str, description: str, 
                           context: str = "", requirements: str = "", 
                           structure: str = "", plan: str = "") -> str:
        """Create task file content from template.
        
        Args:
            task_id: Task ID (e.g., "001")
            title: Task title
            description: Task description
            context: Project context
            requirements: Task requirements
            structure: Directory structure
            plan: Implementation plan
            
        Returns:
            Formatted task content
        """
        template = self._load_task_template()
        
        # Replace template placeholders
        content = template.replace(
            "# TASK-nnn: Short task summary",
            f"# TASK-{task_id}: {title}"
        )
        
        # Replace description
        content = re.sub(
            r'<REPLACE>\s*\nConcise introduction:.*?\n</REPLACE>',
            description,
            content,
            flags=re.DOTALL
        )
        
        # Replace project context
        if context:
            content = re.sub(
                r'<REPLACE>\s*\nBrief overview of the project.*?\n</REPLACE>',
                context,
                content,
                flags=re.DOTALL
            )
        
        # Replace requirements
        if requirements:
            content = re.sub(
                r'<REPLACE>\s*\nDetailed requirements:.*?\n</REPLACE>',
                requirements,
                content,
                flags=re.DOTALL
            )
        
        # Replace directory structure
        if structure:
            content = re.sub(
                r'<REPLACE>\s*\nA pared-down `tree` view.*?\n</REPLACE>',
                f"```\n{structure}\n```",
                content,
                flags=re.DOTALL
            )
        
        # Replace implementation plan
        if plan:
            content = re.sub(
                r'<REPLACE>\s*\nStep-by-step plan for completing.*?\n</REPLACE>',
                plan,
                content,
                flags=re.DOTALL
            )
        
        return content
    
    def _update_todo_md(self, task_id: str, title: str, action: str = "add") -> None:
        """Update TODO.md file with task entry.
        
        Args:
            task_id: Task ID
            title: Task title
            action: "add" or "complete"
        """
        if not self.todo_file.exists():
            # Create TODO.md if it doesn't exist
            self.todo_file.write_text("# TODO\n\n## Task List\n\n")
        
        content = self.todo_file.read_text()
        
        if action == "add":
            # Add new task entry
            task_entry = f"- [ ] TASK-{task_id}: {title}\n"
            
            if "## Task List" in content:
                # Insert after Task List header
                content = content.replace(
                    "## Task List\n\n",
                    f"## Task List\n\n{task_entry}"
                )
            else:
                # Append to end
                content += f"\n{task_entry}"
        
        elif action == "complete":
            # Mark task as complete
            pattern = f"- \\[ \\] TASK-{task_id}:"
            replacement = f"- [x] TASK-{task_id}:"
            content = re.sub(pattern, replacement, content)
        
        self.todo_file.write_text(content)
    
    def _load_task_file(self, task_id: str) -> Tuple[Path, str]:
        """Load existing task file.
        
        Args:
            task_id: Task ID
            
        Returns:
            Tuple of (file_path, content)
            
        Raises:
            FileNotFoundError: If task file doesn't exist
        """
        task_file = self.tasks_dir / f"TASK-{task_id}.md"
        if not task_file.exists():
            raise FileNotFoundError(f"Task file not found: {task_file}")
        
        return task_file, task_file.read_text()
    
    def _check_task_completion(self, content: str) -> Tuple[bool, List[str]]:
        """Check if task cleanup items are completed.
        
        Args:
            content: Task file content
            
        Returns:
            Tuple of (is_complete, missing_items)
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
    
    def new_task(self, title: str, description: str, context: str = "", 
                 requirements: str = "", structure: str = "", plan: str = "",
                 json_data: Dict = None) -> str:
        """Create a new task.
        
        Args:
            title: Task title
            description: Task description
            context: Project context
            requirements: Task requirements
            structure: Directory structure
            plan: Implementation plan
            json_data: Optional JSON data to override parameters
            
        Returns:
            Task ID of created task
        """
        # Override with JSON data if provided
        if json_data:
            title = json_data.get("title", title)
            description = json_data.get("description", description)
            context = json_data.get("context", context)
            requirements = json_data.get("requirements", requirements)
            structure = json_data.get("structure", structure)
            plan = json_data.get("plan", plan)
        
        # Validate required fields
        if not title or not description:
            raise ValueError("Title and description are required")
        
        # Get next task ID
        task_id = self._get_next_task_id()
        
        # Create task content
        task_content = self._create_task_content(
            task_id, title, description, context, requirements, structure, plan
        )
        
        # Write task file
        task_file = self.tasks_dir / f"TASK-{task_id}.md"
        task_file.write_text(task_content)
        
        # Update TODO.md
        self._update_todo_md(task_id, title, "add")
        
        return task_id
    
    def update_task(self, task_id: str, plan: str = None, context: str = None,
                    requirements: str = None, structure: str = None,
                    json_data: Dict = None) -> bool:
        """Update an existing task.
        
        Args:
            task_id: Task ID to update
            plan: Updated implementation plan
            context: Updated project context
            requirements: Updated requirements
            structure: Updated directory structure
            json_data: Optional JSON data to override parameters
            
        Returns:
            True if update successful
        """
        # Override with JSON data if provided
        if json_data:
            plan = json_data.get("plan", plan)
            context = json_data.get("context", context)
            requirements = json_data.get("requirements", requirements)
            structure = json_data.get("structure", structure)
        
        # Load existing task
        task_file, content = self._load_task_file(task_id)
        
        # Update implementation plan
        if plan:
            def replace_plan(match):
                return match.group(1) + plan + '\n'
            
            content = re.sub(
                r'(## Implementation Plan\n\n).*?(?=\n## |$)',
                replace_plan,
                content,
                flags=re.DOTALL
            )
        
        # Update project context
        if context:
            def replace_context(match):
                return match.group(1) + context + '\n'
            
            content = re.sub(
                r'(## Project Context\n\n).*?(?=\n## |$)',
                replace_context,
                content,
                flags=re.DOTALL
            )
        
        # Update requirements
        if requirements:
            def replace_requirements(match):
                return match.group(1) + requirements + '\n'
            
            content = re.sub(
                r'(## Task Requirements\n\n).*?(?=\n## |$)',
                replace_requirements,
                content,
                flags=re.DOTALL
            )
        
        # Update directory structure
        if structure:
            def replace_structure(match):
                return match.group(1) + f'```\n{structure}\n```\n'
            
            content = re.sub(
                r'(## Relevant Directory Structure\n\n).*?(?=\n## |$)',
                replace_structure,
                content,
                flags=re.DOTALL
            )
        
        # Write updated content
        task_file.write_text(content)
        
        return True
    
    def complete_task(self, task_id: str) -> bool:
        """Mark a task as complete.
        
        Args:
            task_id: Task ID to complete
            
        Returns:
            True if task is fully complete and ready to be marked done
            
        Raises:
            ValueError: If task is not ready to be completed
        """
        # Load task file
        task_file, content = self._load_task_file(task_id)
        
        # Check if task is ready to be completed
        is_complete, missing_items = self._check_task_completion(content)
        
        if not is_complete:
            raise ValueError(f"Task not ready to complete. Missing: {', '.join(missing_items)}")
        
        # Update TODO.md to mark as complete
        self._update_todo_md(task_id, "", "complete")
        
        return True
    
    def list_tasks(self) -> List[Dict]:
        """List all tasks with their status.
        
        Returns:
            List of task dictionaries with id, title, and status
        """
        tasks = []
        
        # Read TODO.md to get task status
        todo_content = ""
        if self.todo_file.exists():
            todo_content = self.todo_file.read_text()
        
        # Find all task files
        if self.tasks_dir.exists():
            for task_file in sorted(self.tasks_dir.glob("TASK-*.md")):
                match = re.search(r'TASK-(\d+)\.md', task_file.name)
                if match:
                    task_id = match.group(1)
                    
                    # Get title from file
                    content = task_file.read_text()
                    title_match = re.search(r'# TASK-\d+: (.+)', content)
                    title = title_match.group(1) if title_match else "Unknown"
                    
                    # Check status in TODO.md
                    status = "pending"
                    if f"- [x] TASK-{task_id}:" in todo_content:
                        status = "complete"
                    elif f"- [ ] TASK-{task_id}:" in todo_content:
                        status = "pending"
                    
                    tasks.append({
                        "id": task_id,
                        "title": title,
                        "status": status,
                        "file": str(task_file)
                    })
        
        return tasks


def main():
    """Main entry point for the todo manager tool."""
    parser = argparse.ArgumentParser(
        description="Manage TODO.md and TASK files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create new task
    python todo-mgr.py new --title "Add user authentication" --description "Implement OAuth2 login"
    
    # Create task with JSON
    python todo-mgr.py new --json '{"title": "Fix bug", "description": "Memory leak in parser"}'
    
    # Update task implementation plan
    python todo-mgr.py update --task-id 001 --plan "1. Create auth module\\n2. Add OAuth2 provider"
    
    # Complete task
    python todo-mgr.py complete --task-id 001
    
    # List all tasks
    python todo-mgr.py list
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # New task command
    new_parser = subparsers.add_parser("new", help="Create a new task")
    new_parser.add_argument("--title", help="Task title")
    new_parser.add_argument("--description", help="Task description")
    new_parser.add_argument("--context", help="Project context", default="")
    new_parser.add_argument("--requirements", help="Task requirements", default="")
    new_parser.add_argument("--structure", help="Directory structure", default="")
    new_parser.add_argument("--plan", help="Implementation plan", default="")
    new_parser.add_argument("--json", help="JSON data for task creation")
    
    # Update task command
    update_parser = subparsers.add_parser("update", help="Update an existing task")
    update_parser.add_argument("--task-id", required=True, help="Task ID to update")
    update_parser.add_argument("--plan", help="Updated implementation plan")
    update_parser.add_argument("--context", help="Updated project context")
    update_parser.add_argument("--requirements", help="Updated requirements")
    update_parser.add_argument("--structure", help="Updated directory structure")
    update_parser.add_argument("--json", help="JSON data for task update")
    
    # Complete task command
    complete_parser = subparsers.add_parser("complete", help="Mark a task as complete")
    complete_parser.add_argument("--task-id", required=True, help="Task ID to complete")
    
    # List tasks command
    list_parser = subparsers.add_parser("list", help="List all tasks")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    manager = TodoManager()
    
    try:
        if args.command == "new":
            # Parse JSON if provided
            json_data = None
            if args.json:
                json_data = json.loads(args.json)
            
            task_id = manager.new_task(
                title=args.title or "",
                description=args.description or "",
                context=args.context,
                requirements=args.requirements,
                structure=args.structure,
                plan=args.plan,
                json_data=json_data
            )
            print(f"Created task TASK-{task_id}")
        
        elif args.command == "update":
            # Parse JSON if provided
            json_data = None
            if args.json:
                json_data = json.loads(args.json)
            
            success = manager.update_task(
                task_id=args.task_id,
                plan=args.plan,
                context=args.context,
                requirements=args.requirements,
                structure=args.structure,
                json_data=json_data
            )
            if success:
                print(f"Updated task TASK-{args.task_id}")
        
        elif args.command == "complete":
            success = manager.complete_task(args.task_id)
            if success:
                print(f"Completed task TASK-{args.task_id}")
        
        elif args.command == "list":
            tasks = manager.list_tasks()
            if tasks:
                print("Tasks:")
                for task in tasks:
                    status_icon = "✓" if task["status"] == "complete" else "○"
                    print(f"  {status_icon} TASK-{task['id']}: {task['title']}")
            else:
                print("No tasks found")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()