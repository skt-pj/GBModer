#!/usr/bin/env python3
from pathlib import Path
import runpy

repo = Path(__file__).resolve().parents[1]
runpy.run_path(str(repo / "tools/verify_2048_fit_v044.py"), run_name="__main__")
