# .projects Directory

This directory contains project meta-files, automation tools, and configuration used for project management and Claude Code integration.

## Directory Structure

```
.projects/
├── .env                    # Automation credentials and environment variables
├── init_project.py         # Project initialization script
├── maya_id_ed25519         # Private SSH key for git commits
├── maya_id_ed25519.pub     # Public SSH key for git commits
├── requirements.txt        # Python dependencies for project tools
├── tools/                  # Management tools for Claude Code integration
│   ├── todo-mgr.py         # Task management tool
│   ├── bug-mgr.py          # Bug tracking tool
│   ├── README.md           # Tools documentation
│   └── CLAUDE.md           # Claude-specific context for tools
├── TASKS/                  # Meta-project tasks
│   └── TASK-001.md         # Example task
├── TODO.md                 # Meta-project task index
├── README.md               # This file
└── CLAUDE.md               # Claude context for .projects directory
```

## Files Overview

### Core Files

- **`.env`** - Contains automation credentials and environment variables. Not checked into version control.
- **`init_project.py`** - Script to initialize new projects from this template.
- **`maya_id_ed25519`** & **`maya_id_ed25519.pub`** - SSH key pair for git commits as the `maya` user.
- **`requirements.txt`** - Python dependencies needed for project management tools.

### Management Tools

The `tools/` directory contains Python scripts that integrate with Claude Code to manage project tasks and bugs:

- **`todo-mgr.py`** - Manages TODO.md and TASK files
- **`bug-mgr.py`** - Manages BUGS.md and BUG files

These tools follow the project's template schemas and provide consistent interfaces for Claude to interact with the project management system.

### Meta-Project Management

- **`TASKS/`** - Contains tasks related to the project template itself (not the main project)
- **`TODO.md`** - Index of meta-project tasks

## Usage

### Setting Up a New Project

1. Run the initialization script:
   ```bash
   python init_project.py
   ```

2. Configure environment variables in `.env`:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. Install tool dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Using Management Tools

The tools in the `tools/` directory are designed to be used by Claude Code for automated project management. They can also be used manually:

```bash
# Create a new task
python tools/todo-mgr.py new --title "Implement feature X" --description "Add user authentication"

# Create a new bug report
python tools/bug-mgr.py new --title "Login fails" --description "Users cannot log in" --severity P1

# List all tasks
python tools/todo-mgr.py list

# List all bugs
python tools/bug-mgr.py list
```

See the individual tool documentation in `tools/README.md` for detailed usage instructions.

## Environment Variables

The `.env` file should contain the following variables:

```bash
# Git configuration
GIT_USER_NAME="maya"
GIT_USER_EMAIL="maya@example.com"

# Project configuration
PROJECT_NAME="Your Project Name"
PROJECT_ALIAS="project-alias"
PROJECT_DESCRIPTION="Brief project description"

# Automation credentials (if applicable)
GITEA_TOKEN="your-gitea-token"
AUTHENTIK_TOKEN="your-authentik-token"
```

## Security Notes

- The `.env` file is not checked into version control
- SSH keys should be properly secured and have appropriate permissions
- Automation tokens should be rotated regularly
- Never commit sensitive credentials to the repository

## Integration with Claude Code

This directory structure is designed to work seamlessly with Claude Code. The tools provide standardized interfaces for:

- Task creation and management
- Bug tracking and resolution
- Project documentation maintenance
- Automated workflows

Claude can use these tools to maintain project organization and ensure consistent documentation practices across all project activities.