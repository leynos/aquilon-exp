# Test Coverage

Aquilon's test suite can generate code coverage reports using the standard `coverage.py` library.

Run the tests with coverage enabled:

```bash
python tests/runtests.py --config=tests/unittest.conf --no-interactive --coverage
```

Ensure the machine's fully qualified hostname resolves locally before running
the command:

```bash
grep -q $(hostname) /etc/hosts || \
    echo "127.0.0.1 $(hostname).local" >> /etc/hosts
```

The HTML and XML reports will be written under `logs/coverage` by default.
