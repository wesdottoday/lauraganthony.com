# Claude Context for .projects Directory

This directory contains project meta-files, automation tools, and configuration specifically designed for Claude Code integration and project management.

## Directory Purpose

The `.projects` directory serves as the operational center for:
- Project template management
- Automation tools for task/bug tracking
- SSH keys and credentials for git operations
- Environment configuration
- Claude Code integration utilities

## Key Files and Their Purpose

### Management Tools
- **`tools/issue-mgr.py`** - Issues management tool for Claude to create, update, and manage Gitea Issues (tasks and bugs)
- **`tools/pr-helper.py`** - Enhanced PR tool with automatic linking and assignee notifications
- **`tools/ci-monitor.py`** - CI build monitoring tool with automatic issue creation for failures
- **`tools/docs-validator.py`** - Documentation compliance validator for CI integration

### Configuration Files
- **`.env`** - Environment variables and credentials (not committed to git)
- **`requirements.txt`** - Python dependencies for management tools
- **`project.yaml`** - Structured project metadata for automation

### Git Configuration
- **`maya_id_ed25519`** - Private SSH key for git commits as maya user
- **`maya_id_ed25519.pub`** - Public SSH key for git commits

### Project Initialization
- **`init_project.py`** - Script to initialize new projects from this template

## Claude Usage Guidelines

### Issues-Based Task Management
When working with tasks, Claude should:
1. Use `python .projects/tools/issue-mgr.py new --type task` to create new task Issues
2. Use `python .projects/tools/issue-mgr.py update --issue-id ID` to update Issue details
3. Use `python .projects/tools/issue-mgr.py close --issue-id ID` to close completed Issues
4. Use `python .projects/tools/issue-mgr.py list --state open --type task` to view open tasks

### Issues-Based Bug Tracking
When encountering bugs, Claude should:
1. Use `python .projects/tools/issue-mgr.py new --type bug --severity P1` to create bug Issues
2. Use `python .projects/tools/issue-mgr.py update --issue-id ID` to add investigation details
3. Use `python .projects/tools/issue-mgr.py close --issue-id ID` to close resolved bugs
4. Use `python .projects/tools/issue-mgr.py list --state open --type bug` to view open bugs

### Pull Request Management
When completing Issues, Claude should:
1. Create feature branch: `git checkout -b feature/issue-ID-description`
2. Make commits and push changes
3. Use `python .projects/tools/pr-helper.py create --title "Fix #ID: Description"` to create PR with automatic linking
4. PRs automatically assign to @wk and link to Issues

### Tool Integration
The Issues-based tools are designed to:
- Create and manage Gitea Issues via API with automatic labeling
- Support milestone assignment for project coordination
- Automatically link PRs to Issues using #ID syntax
- Integrate with CI monitoring for automatic failure reporting
- Validate documentation compliance for task completions
- Provide automatic assignee notifications and review requests

## Important Notes

### Security
- Never commit the `.env` file to version control
- SSH keys should have appropriate permissions (600 for private key)
- Credentials should be rotated regularly

### Workflow Integration
- All task and bug management should go through issue-mgr.py
- Issues are managed in Gitea repository Issues system
- Use Issues-first approach: create Issues before implementing
- Follow branch naming: `feature/issue-ID-description`

### Issues Organization
- Tasks and bugs are tracked as Gitea Issues with appropriate labels
- Milestones coordinate major project phases
- Issue templates ensure consistent reporting
- Automatic linking between PRs and Issues via #ID syntax

## Error Handling

If tools fail:
1. Check Python environment and dependencies
2. Verify file permissions
3. Ensure templates exist and are properly formatted
4. Check for file system write permissions

## Dependencies

The tools require:
- Python 3.6+
- Standard library only (no external dependencies)
- Gitea API access with valid API token
- Git repository with proper remote configuration
- SSH keys configured for automated commits

## Integration Points

This directory integrates with:
- Gitea Issues system via API for task/bug tracking
- Gitea Pull Requests with automatic linking and notifications
- Woodpecker CI for build monitoring and failure reporting
- Documentation validation system for compliance enforcement
- Git repository for branch management and automated commits
- Claude Code workflow automation and Issues-first development