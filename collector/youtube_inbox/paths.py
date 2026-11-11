from __future__ import annotations

import os
from pathlib import Path

try:
    import tzdata  # noqa: F401  # IANA zones on Windows
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT = REPO_ROOT / "vault"
LOCAL_TZ = os.environ.get("SIGNALS_TZ") or "America/Los_Angeles"


def vault_root() -> Path:
    env = os.environ.get("SIGNALS_VAULT")
    return Path(env).expanduser().resolve() if env else DEFAULT_VAULT.resolve()
