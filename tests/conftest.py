import sys
from pathlib import Path


def pytest_configure():
    """Ensure project root is on sys.path for src.* imports."""
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

