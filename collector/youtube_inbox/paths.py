from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import tzdata  # noqa: F401  # IANA zones on Windows
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT = REPO_ROOT / "vault"


def vault_root() -> Path:
    env = os.environ.get("SIGNALS_VAULT")
    return Path(env).expanduser().resolve() if env else DEFAULT_VAULT.resolve()


def to_local(moment: datetime | None = None) -> datetime:
    """Convert to the local time zone: SIGNALS_TZ (IANA name) if set, else the system zone."""
    current = moment or datetime.now(timezone.utc)
    name = (os.environ.get("SIGNALS_TZ") or "").strip()
    return current.astimezone(ZoneInfo(name)) if name else current.astimezone()
