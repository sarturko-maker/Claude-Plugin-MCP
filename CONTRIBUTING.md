# Contributing

Contributions are welcome for this proof of concept. Whether you are reporting a bug, suggesting a feature, or submitting code, your input helps improve the tool.

## Reporting Bugs

Open a [GitHub issue](https://github.com/sarturko-maker/Claude-Plugin-MCP/issues) with:

- A clear description of the bug
- Steps to reproduce
- Expected behavior vs. actual behavior
- Your environment (Python version, OS, Claude Desktop version)

## Suggesting Features

Open a [GitHub issue](https://github.com/sarturko-maker/Claude-Plugin-MCP/issues) with:

- A description of the feature
- The use case it addresses
- How it fits with the plugin's purpose (contract negotiation with tracked changes)

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your change
3. **Write tests** for new functionality
4. **Run the test suite** to confirm nothing is broken: `pytest`
5. **Submit a PR** with a clear description of what changed and why

## Code Standards

This project follows the conventions documented in [CLAUDE.md](CLAUDE.md):

- **Python 3.11+** with type hints on all functions
- **Pydantic** for data models
- **pytest** for testing
- Every file and function has a **docstring**
- No file longer than **200 lines** -- split into focused modules
- No function longer than **40 lines** -- extract named helpers
- Self-explanatory function names (prefer `extract_authors_from_markup()` over `process()`)
- No circular imports, no abbreviations, no single-letter variables outside trivial loops

## Testing

- All changes must pass the existing test suite: `pytest`
- New features must include tests
- Bug fixes should include a test that would have caught the bug
- Test names should describe the scenario they cover

## Security

Report security vulnerabilities through the responsible disclosure process described in [SECURITY.md](SECURITY.md). Do **not** report security issues via public GitHub issues.

## License

By contributing to this project, you agree that your contributions will be licensed under the [MIT License](LICENSE).
