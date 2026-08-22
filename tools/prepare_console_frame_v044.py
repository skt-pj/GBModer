#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: prepare_console_frame_v044.py <generated_src_root>")

root = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder"

converter_path = root / "MediaFileConverter.java"
text = converter_path.read_text()
pattern = re.compile(
    r"(?ms)^[ \t]*filtered\s*=\s*prepareFilteredBitmap\(\s*"
    r"sourceFrame\s*,\s*options\s*,\s*false\s*,\s*"
    r"targetWidth\s*,\s*targetHeight\s*\);\s*\n"
    r"[ \t]*byte\[\]\s+yuv\s*=\s*bitmapToYuv420\(filtered\s*,\s*colorFormat\);"
)
replacement = (
    "                    filtered = prepareFilteredBitmap(sourceFrame, options, false, targetWidth, targetHeight);\n"
    "                    byte[] yuv = bitmapToYuv420(filtered, colorFormat);"
)
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit(f"CPU video filter/YUV block normalization expected one match, got {count}")
converter_path.write_text(text)

# v0.1.22 added the text-redraw GPU guard. v0.1.44 temporarily normalizes the block
# so the frame finalizer can add the fixed-resolution guard; a post-finalizer restores
# the independent text-redraw guard immediately afterward.
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()
old_guard = '''        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && !windowTextRecognitionEnabled
                && !gpuWindowPathDisabled
                && !GameBoyFilter.MODE_GBC.equals(windowFilterMode);
'''
normalized_guard = '''        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && !gpuWindowPathDisabled
                && !GameBoyFilter.MODE_GBC.equals(windowFilterMode);
'''
if access.count(old_guard) != 1:
    raise SystemExit(f"live GPU text guard normalization expected one match, got {access.count(old_guard)}")
access_path.write_text(access.replace(old_guard, normalized_guard, 1))

print("v0.1.44 generated CPU video and live GPU guard normalized", flush=True)
