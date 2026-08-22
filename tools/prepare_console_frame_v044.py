#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: prepare_console_frame_v044.py <generated_src_root>")

path = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder/MediaFileConverter.java"
text = path.read_text()

pattern = re.compile(
    r"filtered\s*=\s*prepareFilteredBitmap\(\s*"
    r"sourceFrame\s*,\s*options\s*,\s*false\s*,\s*"
    r"targetWidth\s*,\s*targetHeight\s*\);"
)
replacement = "filtered = prepareFilteredBitmap(sourceFrame, options, false, targetWidth, targetHeight);"
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit(f"CPU video filter-call normalization expected one match, got {count}")

path.write_text(text)
print("v0.1.44 generated CPU video filter call normalized", flush=True)
