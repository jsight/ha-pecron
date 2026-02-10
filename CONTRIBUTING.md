# Contributing to Pecron Home Assistant Integration

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/ha-pecron.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## Development Setup

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linters
ruff check .
mypy custom_components/
```

## Code Standards

- Follow PEP 8
- Use type hints
- Add docstrings to functions
- Keep functions focused and testable
- Write tests for new features

## Commit Messages

Use clear, descriptive commit messages:
- `feat: add support for new device type`
- `fix: resolve API connection timeout issue`
- `docs: update installation instructions`
- `test: add tests for sensor platform`

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass: `pytest`
4. Ensure linters pass: `ruff check . && mypy custom_components/`
5. Provide clear description of changes in the PR

## Reporting Bugs

- Use GitHub Issues
- Include Home Assistant version
- Include integration version
- Provide relevant logs
- Describe reproduction steps

## Feature Requests

- Use GitHub Issues with `[Feature Request]` prefix
- Explain the use case
- Be clear about the expected behavior

## Questions?

Open a GitHub discussion or issue. We're here to help!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
