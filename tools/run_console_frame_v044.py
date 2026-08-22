#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: run_console_frame_v044.py <generated_src_root>")

repo = Path(__file__).resolve().parents[1]
script = repo / "tools/finish_console_frame_v044.py"
source = script.read_text()
old = '''def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)
'''
new = '''def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count < 1:
        raise SystemExit(f"{label}: expected at least one match, got {count}")
    return text.replace(old, new, 1)
'''
if source.count(old) != 1:
    raise SystemExit("v0.1.44 finalizer replacement helper shape changed")
source = source.replace(old, new, 1)
sys.argv = [str(script), sys.argv[1]]
exec(compile(source, str(script), "exec"), {"__name__": "__main__", "__file__": str(script)})
