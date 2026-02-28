# Contributing to PersonaNexus

Thank you for your interest in contributing to **PersonaNexus** — a Python framework for building AI agent personalities and identities using OCEAN (Big Five), DISC, and Jungian 16-type psychological models.

PersonaNexus aims to make it easier for developers to create NPCs, assistive agents, and generative AI systems with consistent, realistic, and scientifically-grounded personality traits.

## Project Overview

- **Language**: Python 3.11+
- **Package Manager**: [uv](https://docs.astral.sh/uv/)
- **Testing**: pytest (870+ tests)
- **Code Style**: [ruff](https://docs.astral.sh/ruff/) (lint + format)
- **License**: MIT

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/PersonaNexus.git
   cd PersonaNexus
   ```

2. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**
   ```bash
   uv sync --dev
   ```

4. **Run tests to verify setup**
   ```bash
   uv run pytest
   ```

   All tests should pass.

## Testing Requirements

- Every PR **must include tests** for new functionality or bug fixes
- Use `uv run pytest` to run the full test suite
- Run a specific test file: `uv run pytest tests/test_personality.py`
- Run with coverage: `uv run pytest --cov=personanexus --cov-report=term-missing`
- Validate example YAML files: `uv run personanexus validate examples/identities/*.yaml`

## Code Style

We use **ruff** for both linting and formatting:

```bash
# Check for lint issues
uv run ruff check src/ tests/

# Auto-fix lint issues
uv run ruff check --fix src/ tests/

# Check formatting
uv run ruff format --check src/ tests/

# Apply formatting
uv run ruff format src/ tests/
```

## Contributing Workflow

1. **Fork** the repository
2. **Create a feature or fix branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**, adding tests where appropriate
4. **Run the test suite** and ensure all tests pass
5. **Lint and format** your code with ruff
6. **Commit** with a descriptive message
   ```bash
   git commit -m "feat: add Jungian role recommendations"
   ```
7. **Push** to your fork
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Open a Pull Request** on GitHub

## Reporting Issues

Before reporting an issue, please:

- Search existing issues to avoid duplicates
- Include Python version, `personanexus` version, and OS
- Provide steps to reproduce
- Include logs or stack traces when relevant

We use issue templates:
- **Bug Report**: Describe expected vs actual behavior
- **Feature Request**: Explain the use case and potential implementation

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this code. Please report unacceptable behavior to maintainers.

## Documentation

- Contributions that improve docs (docstrings, README, examples) are highly valued
- All public functions should have Google-style docstrings

## Recognition

All contributors will be listed in `CONTRIBUTORS.md` and recognized in release notes.

## License

By contributing, you agree that your contributions will be licensed under the **MIT License** (see `LICENSE` file).

---

Thanks for helping make PersonaNexus better for everyone!
