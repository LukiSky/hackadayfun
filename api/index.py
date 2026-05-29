from __future__ import annotations

import sys
from pathlib import Path

# Add backend to import path for serverless runtime.
BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from main import create_app

app = create_app()
