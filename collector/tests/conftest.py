from __future__ import annotations

import sys
from pathlib import Path

# Lets the tests run from a plain checkout too (collector/ on sys.path),
# not only after `pip install -e collector/`.
COLLECTOR = Path(__file__).resolve().parent.parent
if str(COLLECTOR) not in sys.path:
    sys.path.insert(0, str(COLLECTOR))
