# Claude Context for .projects/tools Directory

This directory contains Python tools specifically designed for Claude Code integration with the project's task and bug management workflows.

## Tools Overview

### issue-mgr.py - Issues Management Tool
**Purpose**: Manage Gitea Issues for task and bug tracking via API
**Integration**: Creates, updates, and manages repository Issues with automatic labeling
**Features**: Milestone support, existing label detection, automatic linking

### pr-helper.py - Enhanced Pull Request Tool
**Purpose**: Create and manage PRs with automatic linking and notifications
**Features**: Auto-detects related Issues, assigns to @wk, adds review checklists
**Integration**: Works with Issues system for seamless workflow

### permission-coach.py - Permission Setup Tool
**Purpose**: Guide users through API token and permission setup
**Features**: Interactive guidance, validation, troubleshooting
**Commands**: guide, validate, troubleshoot, examples

### ci-monitor.py - CI Build Monitoring Tool
**Purpose**: Monitor Woodpecker CI builds and auto-fix common issues
**Features**: Real-time monitoring, automatic issue detection and resolution

### docs-validator.py - Documentation Compliance Validator ⭐ NEW
**Purpose**: Ensure documentation is updated with task completions while allowing intermediate commits
**Features**: Smart validation, task completion detection, CI integration
**Commands**: check-commit, validate-pattern, interactive

## Documentation Validation System

### Problem Solved
The docs-validator.py tool solves the challenge of ensuring documentation compliance without hindering development workflow:

- **Task Completion Enforcement**: Requires documentation updates only when tasks are actually completed
- **Intermediate Commit Flexibility**: Allows safety commits and in-progress commits without documentation
- **Smart Detection**: Automatically detects task completion vs. intermediate commits
- **CI Integration**: Validates documentation compliance in Woodpecker CI pipeline

### How It Works

#### 1. Commit Classification
The validator analyzes commits to determine their type:

```python
# Task completion patterns
completion_patterns = [
    r"Complete TASK-(\d+)",
    r"Finish TASK-(\d+)", 
    r"TASK-(\d+):.*complete",
    r"TASK-(\d+):.*finished"
]
```

#### 2. Documentation Requirement Analysis
Determines if code changes require documentation updates:

```python
# Files requiring documentation
doc_requiring_patterns = [
    r'\.py$',           # Python code changes
    r'requirements.*\.txt$',  # Dependency changes
    r'\.yaml$',         # Configuration changes
    r'project\.yaml$',  # Project configuration
]

# Exempt files (don't require docs)
doc_exempt_patterns = [
    r'^TASKS/',         # Task files
    r'^BUGS/',          # Bug files
    r'CLAUDE\.md$',     # Claude context files
    r'test.*\.py$',     # Test files
]
```

#### 3. Validation Logic
- **Task Completion + Code Changes = Documentation Required**
- **Intermediate Commits = Warnings Only** (non-blocking)
- **Documentation Files**: README.md, DOCS/docs/getting-started.md, DOCS/docs/api.md

### Usage Examples

#### CI Pipeline Integration
```yaml
# In .woodpecker.yaml
- name: docs-validation
  image: python:3.11-slim
  commands:
    - python .projects/tools/docs-validator.py check-commit --commit HEAD
```

#### Local Development
```bash
# Check current commit
python .projects/tools/docs-validator.py check-commit

# Check specific commit
python .projects/tools/docs-validator.py check-commit --commit abc123

# Validate recent task completion patterns
python .projects/tools/docs-validator.py validate-pattern

# Interactive mode
python .projects/tools/docs-validator.py interactive
```

#### Strict Mode (for specific branches)
```bash
# Fail on warnings as well as errors
python .projects/tools/docs-validator.py check-commit --strict
```

### Example Scenarios

#### ✅ Allowed: Intermediate Commit
```
Commit: "WIP: Add user authentication system"
Files: src/auth.py, tests/test_auth.py
Result: Warning only - docs should be updated before task completion
```

#### ❌ Blocked: Task Completion Without Docs
```
Commit: "Complete TASK-042: Add user authentication system"
Files: src/auth.py, tests/test_auth.py
Result: Error - documentation updates required for task completion
```

#### ✅ Allowed: Task Completion With Docs
```
Commit: "Complete TASK-042: Add user authentication system"
Files: src/auth.py, README.md, DOCS/docs/api.md
Result: Validation passed
```

#### ✅ Allowed: Non-Code Changes
```
Commit: "Complete TASK-043: Update task management process"
Files: TASKS/TASK-043.md, TODO.md
Result: No documentation required (exempt files only)
```

## Claude Usage Instructions

### When Using docs-validator.py
Claude should use this tool when:
- Working on tasks that involve code changes
- Completing tasks to ensure documentation compliance
- Investigating CI failures related to documentation
- Setting up new projects with documentation validation

### Before Task Completion
Always run validation before marking tasks complete:
```bash
# Check if current changes require documentation updates
python .projects/tools/docs-validator.py check-commit

# If validation fails, update required documentation files:
# - README.md (for user-facing changes)
# - DOCS/docs/getting-started.md (for setup/usage changes)
# - DOCS/docs/api.md (for API/tool changes)
```

### During Development
The validator allows intermediate commits without documentation:
```bash
# These commits are allowed without docs:
git commit -m "WIP: Implementing feature X"
git commit -m "Safety commit: partial implementation"
git commit -m "In progress: debugging issue"

# Only task completion commits require docs:
git commit -m "Complete TASK-123: Implement feature X"  # Requires docs
```

## Implementation Benefits

### 1. Developer Experience
- **No false positives**: Intermediate commits don't block CI
- **Clear feedback**: Specific guidance on what documentation is needed
- **Flexible workflow**: Supports various development styles

### 2. Documentation Quality
- **Comprehensive coverage**: Ensures all documentation types are updated
- **Consistent compliance**: Automated enforcement prevents oversight
- **Timely updates**: Documentation stays current with code changes

### 3. CI/CD Integration
- **Fast feedback**: Quick validation in CI pipeline
- **Selective enforcement**: Only blocks problematic commits
- **Pattern analysis**: Identifies trends in documentation compliance

### 4. Project Maintenance
- **Audit trail**: Track documentation compliance over time
- **Team coordination**: Ensures all contributors follow documentation standards
- **Quality gates**: Prevents merging incomplete work

## Configuration and Customization

### File Patterns
The validator can be customized by modifying the file pattern lists:

- **doc_requiring_patterns**: Add file types that require documentation
- **doc_exempt_patterns**: Add file types that don't require documentation
- **completion_patterns**: Add commit message patterns for task completion

### Documentation Files
Default required documentation files:
- `README.md` - User-facing documentation
- `DOCS/docs/getting-started.md` - Setup and usage guide
- `DOCS/docs/api.md` - API and tool documentation

### Validation Modes
- **Standard**: Errors on task completion without docs, warnings on intermediate commits
- **Strict**: Fails on warnings as well as errors (use for main branch)
- **Pattern**: Validates recent task completion history

This system ensures documentation compliance without hindering development velocity, making it an ideal solution for the project template system.