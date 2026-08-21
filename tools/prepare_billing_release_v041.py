#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: prepare_billing_release_v041.py <source_kotlin_root> <generated_kotlin_root>")

repo = Path(__file__).resolve().parents[1]
source_root = Path(sys.argv[1]).resolve()
generated_root = Path(sys.argv[2]).resolve()

subprocess.run(
    [sys.executable, str(repo / "tools/prepare_billing_kotlin_v035.py"), str(source_root), str(generated_root)],
    cwd=repo,
    check=True,
)
subprocess.run(
    [sys.executable, str(repo / "tools/finish_release_ui_v041.py"), str(generated_root)],
    cwd=repo,
    check=True,
)

print("billing/release Kotlin sources prepared through v0.1.41", flush=True)
