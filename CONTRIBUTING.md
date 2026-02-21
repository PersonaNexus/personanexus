# Contributing to PersonaNexus

Thank you for your interest in contributing to **PersonaNexus** — a Python framework for building AI agent personalities and identities using OCEAN (Big Five) and DISC psychological models.

PersonaNexus aims to make it easier for developers to create NPCs, assistive agents, and generative AI systems with consistent, realistic, and scientifically-grounded personality traits.

## 🎯 Project Overview

- **Language**: Python 3.10+
- **Testing**: pytest (410+ tests)
- **Code Style**: black, isort, flake8
- **License**: MIT

## 🛠️ Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/PersonaNexus.git
   cd PersonaNexus
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or `.\.venv\Scripts\activate` on Windows
   ```

3. **Install in editable mode with dev dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests to verify setup**
   ```bash
   pytest
   ```

   ✅ All 410+ tests should pass.

## 🧪 Testing Requirements

- Every PR **must include tests** for new functionality or bug fixes
- Use `pytest` to run the full test suite
- Ensure test coverage for core modules (`personanexus/core/`, `personanexus/models/`, `personanexus/psychology/`)
- You can run a specific test file: `pytest tests/unit/test_model.py`
- Or run with coverage: `pytest --cov=personanexus --cov-report=term-missing`

## 🎨 Code Style

We use automated formatting and lintingtools to keep code consistent:

- **Formatting**: [black](https://black.readthedocs.io/) (line length: 88)
- **Imports**: [isort](https://pycqa.github.io/isort/) (profile: `black`)
- **Linting**: [flake8](https://flake8.pycqa.org/) with our configured rules

Before committing, run:
```bash
black personanexus tests
isort personanexus tests
flake8 personanexus tests
```

Or let the pre-commit hooks (if installed) handle this automatically.

## 🚀 Contributing Workflow

1. **Fork** the repository
2. **Create a feature or fix branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**, adding tests where appropriate
4. **Run the test suite** and ensure all 410+ tests pass
5. **Format and lint** your code
6. **Commit** with a descriptive message (use [conventional commits](https://www.conventionalcommits.org/))
   ```bash
   git commit -m "feat: add DISC assertiveness model"
   ```
7. **Push** to your fork
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Open a Pull Request** on GitHub

## 🐛 Reporting Issues

Before reporting an issue, please:

- Search existing issues to avoid duplicates
- Include Python version, `personanexus` version, and OS
- Provide steps to reproduce
- Include logs or stack traces when relevant

We use issue templates:
- **Bug Report**: Describe expected vs actual behavior
- **Feature Request**: Explain the use case and potential implementation

## 📜 Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this code. Please report unacceptable behavior to maintainers.

## 📝 Documentation

- contributions that improve docs (docstrings, README, examples) are highly valued
- All public functions should have Google-style docstrings

## ✨ Recognition

All contributors will be listed in `CONTRIBUTORS.md` and recognized in release notes.

## 📄 License

By contributing, you agree that your contributions will be licensed under the **MIT License** (see `LICENSE` file).

---

🌟 Thanks for helping make PersonaNexus better for everyone!
