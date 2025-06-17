"""Lightweight ms.version stub used for testing."""
import sys
from pathlib import Path

_packages: dict[str, str] = {}

def addpkg(name: str, version: str, meta: str | None = None) -> None:
    """Register a package version.

    Parameters
    ----------
    name : str
        Package name.
    version : str
        Package version.
    meta : str, optional
        Extra metadata ignored by this stub.
    """
    _packages[name] = version
    if name == "ms.dsdb":
        fake_path = Path(__file__).resolve().parents[2] / "tests" / "fakemodules" / "ms"
        if fake_path.exists():
            package = __import__("ms")
            package.__path__.append(str(fake_path))
