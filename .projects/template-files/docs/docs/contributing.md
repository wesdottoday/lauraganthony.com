# Contributing

Thank you for your interest in contributing to <PROJECT_NAME>! This guide will help you get started.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct:

- Be respectful and inclusive
- Use welcoming and inclusive language
- Be collaborative
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.8 or higher
- Git
- A GitHub/Gitea account
- Basic knowledge of the project's technology stack

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone <GIT_REPO_URL>
   cd <PROJECT_ALIAS>
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Install the package in development mode**:
   ```bash
   pip install -e .
   ```

5. **Run tests to ensure everything works**:
   ```bash
   pytest
   ```

## Development Workflow

### Task-First Methodology

This project follows a strict task-first methodology:

1. **Create a task** before starting work:
   ```bash
   python .projects/tools/todo-mgr.py new \
       --title "Your task title" \
       --description "Detailed description of the work"
   ```

2. **Update your implementation plan**:
   ```bash
   python .projects/tools/todo-mgr.py update --task-id XXX --plan "Your implementation steps"
   ```

3. **Work on the implementation** following your plan

4. **Mark the task complete** when all cleanup items are done:
   ```bash
   python .projects/tools/todo-mgr.py complete --task-id XXX
   ```

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards

3. **Write tests** for new functionality

4. **Run the test suite**:
   ```bash
   pytest
   flake8
   black --check .
   mypy .
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add your descriptive commit message"
   ```

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a pull request**

## Coding Standards

### Python Code Style

We follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html):

- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use [flake8](https://flake8.pycqa.org/) for linting
- Use [mypy](https://mypy.readthedocs.io/) for type checking

### Documentation

- All public functions must have docstrings
- Use Google-style docstrings
- Update documentation when adding new features
- Include examples in docstrings where helpful

### Testing

- Write tests for all new functionality
- Maintain or improve test coverage
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern

## Types of Contributions

### Bug Reports

When reporting bugs:

1. **Use the bug tracking tool**:
   ```bash
   python .projects/tools/bug-mgr.py new \
       --title "Bug title" \
       --description "Detailed description" \
       --severity P1
   ```

2. **Include**:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Error messages or logs

### Feature Requests

When requesting features:

1. **Create a task** describing the feature
2. **Explain the use case** and why it's needed
3. **Propose an implementation** if you have ideas
4. **Discuss with maintainers** before starting work

### Documentation Improvements

Documentation contributions are always welcome:

- Fix typos or grammar errors
- Improve clarity or add examples
- Add missing documentation
- Update outdated information

### Code Contributions

Code contributions should:

- Solve a real problem or add valuable functionality
- Follow the coding standards
- Include appropriate tests
- Update documentation as needed
- Be discussed with maintainers for larger changes

## Pull Request Process

1. **Ensure your PR**:
   - Has a clear title and description
   - References related tasks or bugs
   - Includes tests for new functionality
   - Updates documentation if needed
   - Passes all CI checks

2. **PR Review Process**:
   - Maintainers will review your PR
   - Address any feedback or requested changes
   - Once approved, your PR will be merged

3. **After Merge**:
   - Your changes will be included in the next release
   - Update or close related tasks/bugs

## Development Guidelines

### Commit Messages

Use clear, descriptive commit messages:

```
Add user authentication system

- Implement OAuth2 integration
- Add user session management
- Update API endpoints for authentication
- Add comprehensive tests

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Branch Naming

Use descriptive branch names:

- `feature/add-user-auth`
- `bugfix/fix-memory-leak`
- `docs/update-api-reference`

### Testing

Run the full test suite before submitting:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=<PROJECT_ALIAS>

# Run linting
flake8 .
black --check .
isort --check-only .
mypy .
```

## Getting Help

If you need help:

1. Check existing documentation
2. Search [existing issues](<GIT_REPO_HTTPS_URL>/issues)
3. Ask in discussions or create a new issue
4. Contact maintainers directly

## Recognition

Contributors will be:

- Listed in the project's contributors
- Mentioned in release notes for significant contributions
- Invited to become maintainers for consistent valuable contributions

Thank you for contributing to <PROJECT_NAME>!