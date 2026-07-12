# Contributing to DevForge

Thanks for your interest in contributing! Here's how to get started.

## Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/REPO-NAME.git`
3. Create a branch: `git checkout -b my-feature`
4. Make your changes
5. Push: `git push origin my-feature`
6. Open a Pull Request

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Guidelines

- Write tests for new features
- Run existing tests before submitting: `pytest`
- Follow PEP 8 style conventions
- Keep PRs focused — one feature or fix per PR
- Write clear commit messages

## Reporting Issues

- Use GitHub Issues
- Include steps to reproduce
- Include expected vs actual behavior
- Include Python version and OS

## Code of Conduct

Be respectful, constructive, and inclusive. We're all here to build good tools.