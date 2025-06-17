# Coding Style Guide

This guide summarizes conventions for Python code in this repository.

## Supported Python Versions

- Python 3.10 and 3.11 are supported. New code should remain compatible with Python 3.10 while
  testing under Python 3.11 as well.

## Tooling

- **Formatter**: [Black](https://black.readthedocs.io/) with a line length of 120 characters. Formatting is run via the `darker` wrapper which only reformats changed lines and applies `isort` and `flynt` where appropriate.
- **Import sorting**: [isort](https://pycqa.github.io/isort/) using the "black" profile.
- **Linting**: [Ruff](https://docs.astral.sh/ruff/) is preferred over flake8 and is configured to enforce common flake8, pylint and pyupgrade rules.
- All tools run automatically via `pre-commit` hooks. Run `pre-commit run --files <file1> <file2>` before committing changes.

## Type Hinting

- Type hints are gradually being introduced. When adding new modules or functions, provide type annotations where practical using the standard `typing` module.
- Return and argument types should be explicit. Use `typing.Optional` for values that may be `None`.

## Naming Conventions

- Modules, functions and variables use `snake_case`.
- Classes use `CamelCase`.
- Constants are in `UPPER_SNAKE_CASE`.

## Commenting and Docstrings

- Use complete sentences in comments and docstrings.
- Module, class and function docstrings use triple double quotes with a short summary line followed by a blank line and further description when needed.
- Inline comments start with `# ` and should explain *why* something is done when it is not obvious.

## Import Style

- Imports are absolute and grouped in the following order with blank lines between groups:
  1. Standard library modules
  2. Third-party modules
  3. Local application modules
- Avoid wildcard imports.

## Data Structures

- `namedtuple` is used in a few places for lightweight data containers.
- `dataclasses` or `pydantic` models are currently not used but may be introduced when structured records are needed.

## Programming Style

- List and dictionary comprehensions are preferred for simple transformations. Use imperative loops for more complex logic to keep the code readable.
- Functional constructs like `map()` and `filter()` are rarely used.

Adhering to these guidelines ensures a consistent code base and helps automated tools catch issues early.
