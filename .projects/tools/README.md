# Project Management Tools

This directory contains Python tools designed to integrate with Claude Code for automated project management following the project's established schemas and workflows.

## Tools Overview

### todo-mgr.py - Task Management Tool

Manages TODO.md and TASK files following the project's _TASK-TEMPLATE.md schema.

**Features:**
- Create new tasks with sequential numbering
- Update task implementation plans and context
- Mark tasks as complete (with validation)
- List all tasks with status

**Usage:**
```bash
# Create a new task
python todo-mgr.py new --title "Implement user authentication" --description "Add OAuth2 login functionality"

# Create task with full details
python todo-mgr.py new \
    --title "Database migration" \
    --description "Migrate from SQLite to PostgreSQL" \
    --context "Part of scalability improvements" \
    --requirements "Must maintain data integrity" \
    --plan "1. Backup data\n2. Create migration scripts\n3. Test thoroughly"

# Create task with JSON payload
python todo-mgr.py new --json '{
    "title": "Add API endpoints",
    "description": "Create REST API for user management",
    "context": "Mobile app integration requirement",
    "requirements": "Must follow OpenAPI 3.0 specification"
}'

# Update task implementation plan
python todo-mgr.py update --task-id 001 --plan "1. Research OAuth2 providers\n2. Implement Google OAuth\n3. Add user session management"

# Update multiple fields
python todo-mgr.py update --task-id 001 \
    --plan "Updated implementation steps" \
    --context "Additional project context" \
    --requirements "Updated requirements"

# Mark task as complete (validates all cleanup items are done)
python todo-mgr.py complete --task-id 001

# List all tasks
python todo-mgr.py list
```

### bug-mgr.py - Bug Tracking Tool

Manages BUGS.md and BUG files following the project's _BUG-TEMPLATE.md schema.

### woodpecker-access-fix.py - Woodpecker CI Access Management Tool

Diagnoses and fixes repository access issues in Woodpecker CI, specifically ensuring both Maya and wk users can see and access repositories.

**Features:**
- List all repositories accessible to the current user
- Check access permissions for specific repositories
- Diagnose visibility and permission issues
- Automatically fix common access problems
- Verify repository settings and configurations

**Usage:**
```bash
# List all accessible repositories
python woodpecker-access-fix.py --list-repos

# Check access to a specific repository
python woodpecker-access-fix.py --repo-name project-template

# Fix access issues for a repository
python woodpecker-access-fix.py --repo-name project-template --fix

# Run comprehensive diagnostic
python woodpecker-access-fix.py --repo-name project-template --diagnostic
```

### bug-mgr.py - Bug Tracking Tool (continued)

**Features:**
- Create new bug reports with severity levels (P0, P1, P2)
- Update bug details and investigation progress
- Mark bugs as resolved (with validation)
- List all bugs with status and severity

**Usage:**
```bash
# Create a new bug report
python bug-mgr.py new \
    --title "Memory leak in parser" \
    --description "Parser consumes excessive memory during large file processing" \
    --severity P1

# Create bug with full details
python bug-mgr.py new \
    --title "Login button misaligned" \
    --description "Login button appears off-center on mobile devices" \
    --severity P2 \
    --environment "iOS Safari 14.0, iPhone 12" \
    --steps "1. Open app on mobile\n2. Navigate to login page\n3. Observe button position"

# Create bug with JSON payload
python bug-mgr.py new --json '{
    "title": "Application crashes on startup",
    "description": "App crashes immediately when launched",
    "severity": "P0",
    "environment": "macOS 12.0, Python 3.9.7",
    "steps": "1. Run python main.py\n2. Application crashes with segfault"
}'

# Update bug with investigation details
python bug-mgr.py update --bug-id 001 \
    --steps "1. Load large CSV file\n2. Run parser\n3. Monitor memory usage with htop" \
    --actual "Memory usage grows to 8GB and doesn't decrease"

# Mark bug as resolved (validates all cleanup items are done)
python bug-mgr.py resolve --bug-id 001

# List all bugs
python bug-mgr.py list
```

## Command Reference

### woodpecker-access-fix.py Commands

#### `--list-repos` - List All Accessible Repositories
Lists all repositories that the current user (Maya) can access in Woodpecker CI.

#### `--repo-name` - Check Specific Repository Access
- `--repo-name` - Repository name to check (e.g., 'project-template' or 'y37.space/project-template')

#### `--fix` - Fix Repository Access Issues
- `--repo-name` - Repository name to fix (required)
- `--fix` - Apply automatic fixes to resolve access issues

#### `--diagnostic` - Run Comprehensive Diagnostic
- `--repo-name` - Repository name to diagnose (optional)
- `--diagnostic` - Run full diagnostic including authentication check

### todo-mgr.py Commands

#### `new` - Create New Task
- `--title` - Task title (required)
- `--description` - Task description (required)
- `--context` - Project context (optional)
- `--requirements` - Task requirements (optional)
- `--structure` - Directory structure (optional)
- `--plan` - Implementation plan (optional)
- `--json` - JSON payload with all fields (optional)

#### `update` - Update Existing Task
- `--task-id` - Task ID to update (required)
- `--plan` - Updated implementation plan (optional)
- `--context` - Updated project context (optional)
- `--requirements` - Updated requirements (optional)
- `--structure` - Updated directory structure (optional)
- `--json` - JSON payload with update fields (optional)

#### `complete` - Mark Task Complete
- `--task-id` - Task ID to complete (required)

#### `list` - List All Tasks
No additional arguments required.

### bug-mgr.py Commands

#### `new` - Create New Bug Report
- `--title` - Bug title (required)
- `--description` - Bug description (required)
- `--severity` - Bug severity: P0, P1, or P2 (required)
- `--background` - Background context (optional)
- `--environment` - Environment details (optional)
- `--steps` - Steps to reproduce (optional)
- `--expected` - Expected behavior (optional)
- `--actual` - Actual behavior (optional)
- `--logs` - Logs and screenshots (optional)
- `--workaround` - Temporary workaround (optional)
- `--proposed-fix` - Proposed fix (optional)
- `--json` - JSON payload with all fields (optional)

#### `update` - Update Existing Bug Report
- `--bug-id` - Bug ID to update (required)
- `--background` - Updated background context (optional)
- `--environment` - Updated environment details (optional)
- `--steps` - Updated steps to reproduce (optional)
- `--expected` - Updated expected behavior (optional)
- `--actual` - Updated actual behavior (optional)
- `--logs` - Updated logs and screenshots (optional)
- `--workaround` - Updated temporary workaround (optional)
- `--proposed-fix` - Updated proposed fix (optional)
- `--json` - JSON payload with update fields (optional)

#### `resolve` - Mark Bug Resolved
- `--bug-id` - Bug ID to resolve (required)

#### `list` - List All Bugs
No additional arguments required.

## Validation and Completion

### Task Completion Validation
Before marking a task as complete, the tool validates:
- [ ] All cleanup checklist items are marked as done
- [ ] A commit link is present in the Final Comments section
- [ ] The task file follows the proper schema

### Bug Resolution Validation
Before marking a bug as resolved, the tool validates:
- [ ] All cleanup checklist items are marked as done
- [ ] A commit link is present in the Final Comments section
- [ ] The bug file follows the proper schema

## Integration with Claude Code

These tools are designed to be called by Claude Code for automated project management:

1. **Task Creation**: Claude can create tasks based on user requests
2. **Progress Tracking**: Claude can update task progress and implementation plans
3. **Bug Reporting**: Claude can create bug reports when issues are discovered
4. **Status Management**: Claude can check completion status and validate readiness

## File Schema Compliance

Both tools strictly follow the project's template schemas:

- **TASK files**: Follow `TASKS/_TASK-TEMPLATE.md` structure
- **BUG files**: Follow `BUGS/_BUG-TEMPLATE.md` structure
- **TODO.md**: Maintained with consistent formatting
- **BUGS.md**: Maintained with consistent formatting and severity levels

## Error Handling

The tools include comprehensive error handling:
- Validation of required fields
- File existence checks
- Schema compliance verification
- Proper error messages for debugging

## Dependencies

Both tools are written in Python 3.6+ and use only standard library modules:
- `argparse` - Command-line argument parsing
- `json` - JSON data handling
- `os` - Operating system interface
- `re` - Regular expressions
- `sys` - System-specific parameters
- `pathlib` - Object-oriented filesystem paths
- `datetime` - Date and time handling
- `typing` - Type hints

No external dependencies are required, making the tools easy to deploy and maintain.