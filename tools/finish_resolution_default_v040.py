#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_resolution_default_v040.py <generated_src_root>")

path = Path(sys.argv[1]) / "com/sktpj/gbmoder/MainActivity.java"
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    "    private int uiResolutionPosition = 7;\n",
    "    private int uiResolutionPosition = 0;\n",
    "generated GB default resolution",
)

replace_once(
    "        return GameBoyFilter.RESOLUTION_PHONE_20;\n",
    "        return GameBoyFilter.RESOLUTION_GB;\n",
    "generated invalid-position fallback",
)

path.write_text(text)
print("v0.1.40 generated live state defaults to GB resolution")
