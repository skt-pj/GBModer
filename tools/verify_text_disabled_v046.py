#!/usr/bin/env python3
from pathlib import Path
import runpy

repo = Path(__file__).resolve().parents[1]
runpy.run_path(str(repo / "tools/verify_ui_restore_v046.py"), run_name="__main__")
