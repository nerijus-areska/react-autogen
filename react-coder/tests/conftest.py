"""
Shared pytest fixtures and configuration.
"""
import sys
from pathlib import Path

# Ensure app is importable when running tests (react-coder project root)
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
