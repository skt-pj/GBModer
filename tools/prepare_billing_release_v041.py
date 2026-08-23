#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: prepare_billing_release_v041.py <source_kotlin_root> <generated_kotlin_root>")

repo = Path(__file__).resolve().parents[1]
source_root = Path(sys.argv[1]).resolve()
generated_root = Path(sys.argv[2]).resolve()

for command in (
    [sys.executable, str(repo / "tools/prepare_billing_kotlin_v035.py"), str(source_root), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_release_ui_v041.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_release_polish_v041.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_debug_live_bypass_v042.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_2048_menu_v043.py"), str(generated_root)],
):
    subprocess.run(command, cwd=repo, check=True)

print("billing/release Kotlin sources prepared through v0.1.43", flush=True)
