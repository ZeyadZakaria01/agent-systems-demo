"""Test setup: the baseline's MiniLM model comes from the shared fastembed cache (no network)."""

import os

from demo.paths import SHARED_ROOT

os.environ.setdefault("FASTEMBED_CACHE_PATH", str(SHARED_ROOT / ".cache" / "fastembed"))
