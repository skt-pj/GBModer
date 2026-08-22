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
text = text.replace(old, new, 1)

# The prepared frame is posted to the main-handler lambda. Keep the lambda-captured
# variable final/effectively-final while still allowing console composition to replace
# the working bitmap before the post.
old_frame = '''            Bitmap frame = lowResolutionBitmap;
            if (ConsoleFrameRenderer.isFixedResolution(windowFilterResolution)) {
                Bitmap framed = ConsoleFrameRenderer.compose(frame, windowFilterResolution);
                if (framed != frame) {
                    frame.recycle();
                    frame = framed;
                }
            }
            lowResolutionBitmap = null;
'''
new_frame = '''            Bitmap sourceFrame = lowResolutionBitmap;
            Bitmap preparedFrame = sourceFrame;
            if (ConsoleFrameRenderer.isFixedResolution(windowFilterResolution)) {
                Bitmap framed = ConsoleFrameRenderer.compose(sourceFrame, windowFilterResolution);
                if (framed != sourceFrame) {
                    sourceFrame.recycle();
                    preparedFrame = framed;
                }
            }
            final Bitmap frame = preparedFrame;
            lowResolutionBitmap = null;
'''
frame_count = text.count(old_frame)
if frame_count != 1:
    raise SystemExit(f"live console lambda frame expected one match, got {frame_count}")
text = text.replace(old_frame, new_frame, 1)

path.write_text(text)
print("v0.1.44 live GPU text-redraw and lambda frame guards restored", flush=True)
