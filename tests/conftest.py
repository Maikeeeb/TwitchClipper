from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_root_str = str(ROOT)
# Ensure project root is first so "api" and "backend" resolve to repo packages.
# Alternatives: pip install -e . (editable) or set PYTHONPATH=. in pytest config.
sys.path.insert(0, _root_str)
