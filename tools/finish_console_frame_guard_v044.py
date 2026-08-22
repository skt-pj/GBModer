#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_console_frame_guard_v044.py <generated_src_root>")

path = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder/FilterAccessibilityService.java"
text = path.read_text()
old = '''        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && !gpuWindowPathDisabled
                && !ConsoleFrameRenderer.isFixedResolution(windowFilterResolution)
                && !GameBoyFilter.MODE_GBC.equals(windowFilterMode);
'''
new = '''        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && !windowTextRecognitionEnabled
                && !gpuWindowPathDisabled
                && !ConsoleFrameRenderer.isFixedResolution(windowFilterResolution)
                && !GameBoyFilter.MODE_GBC.equals(windowFilterMode);
'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"live GPU text guard restore expected one match, got {count}")
path.write_text(text.replace(old, new, 1))
print("v0.1.44 live GPU text-redraw guard restored", flush=True)
