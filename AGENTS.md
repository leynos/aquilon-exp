# Developer Notes

## Documentation
- Markdown documents live under `docs/`
- DocBook-based manuals are in `doc/`

## Package management
- Use `uv pip install --system -e .` to install dependencies defined in
  `setup.py`
- Tool configurations live in `pyproject.toml`

## Testing
```
python tests/runtests.py --config=tests/unittest.conf --no-interactive
```
Some tests require additional environment modules; see `setup-dev-env.sh`.

## Linting and formatting
- Install [pre-commit](https://pre-commit.com/) and run `pre-commit run --files <files>`
- Hooks invoke `darker` (Black + isort) and `ruff` for lint checks
