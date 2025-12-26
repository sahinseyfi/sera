#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app as merged_app  # noqa: E402

app = merged_app.app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=merged_app.SIMULATION_MODE)
