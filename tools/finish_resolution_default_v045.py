#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_resolution_default_v045.py <generated_src_root>")

path = Path(sys.argv[1]) / "com/sktpj/gbmoder/MainActivity.java"
text = path.read_text()
old = "    private int uiResolutionPosition = 0;\n"
new = "    private int uiResolutionPosition = 9;\n"
count = text.count(old)
if count != 1:
    raise SystemExit(f"30 percent live default: expected exactly one match, got {count}")
path.write_text(text.replace(old, new, 1))
print("v0.1.45 generated live state defaults to device ratio 30%")
