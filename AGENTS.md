# Developer Notes

## Documentation
- Markdown documents live under `docs/`
- DocBook-based manuals are in `doc/`

## Package management
- Use `uv pip install --system -e .` to install dependencies defined in
  `setup.py`
- Tool configurations live in `pyproject.toml`

## Protocol buffer modules
Aquilon's Python bindings for protocol messages live in the
[`aquilon-protocols`](https://github.com/quattor/aquilon-protocols) repository.
Install them by cloning the repo and compiling the `.proto` files:

```bash
git clone https://github.com/quattor/aquilon-protocols.git
cd aquilon-protocols
mkdir -p artifactory_build
protoc -I protofiles --python_out=artifactory_build protofiles/*.proto
uv pip install --system -e .
```
The generated modules like `aqdnetworks_pb2.py` will then be importable by the
test suite.

## Testing
```
python tests/runtests.py --config=tests/unittest.conf --no-interactive
```
Some tests require additional environment modules; see `setup-dev-env.sh`.

## Linting and formatting
- Install [pre-commit](https://pre-commit.com/) and run `pre-commit run --files <files>`
- Hooks invoke `darker` (Black + isort) and `ruff` for lint checks
