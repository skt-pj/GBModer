#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_overlay_aspect_v046.py <generated_java_root>")

root = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder"
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()

old_draw = '''            Canvas canvas = new Canvas(lowResolutionBitmap);
            Paint downsamplePaint = new Paint();
            downsamplePaint.setFilterBitmap(false);
            downsamplePaint.setAntiAlias(false);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    source,
                    new Rect(0, 0, source.getWidth(), source.getHeight()),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
'''
new_draw = '''            Canvas canvas = new Canvas(lowResolutionBitmap);
            Paint downsamplePaint = new Paint();
            downsamplePaint.setFilterBitmap(false);
            downsamplePaint.setAntiAlias(false);
            int[] crop = GameBoyFilter.getCenterCropBounds(
                    windowFilterResolution,
                    source.getWidth(),
                    source.getHeight()
            );
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    source,
                    new Rect(crop[0], crop[1], crop[2], crop[3]),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
'''
count = access.count(old_draw)
if count != 1:
    raise SystemExit(f"accessibility fixed-aspect source crop expected exactly one match, got {count}")
access = access.replace(old_draw, new_draw, 1)

# v0.1.33 already fit-centers the resulting bitmap into the Android window. Keep
# that behavior as a required invariant: after v0.1.44 adds the handheld body,
# the complete GB/GBC/GBA/DS frame must not be stretched to the phone aspect.
required_overlay_tokens = (
    "float frameAspect = current.getWidth() / (float) Math.max(1, current.getHeight());",
    "int left = (viewWidth - drawWidth) / 2;",
    "int top = (viewHeight - drawHeight) / 2;",
    "new Rect(left, top, left + drawWidth, top + drawHeight)",
)
for token in required_overlay_tokens:
    if token not in access:
        raise SystemExit(f"aspect-preserving accessibility overlay invariant missing: {token}")

access_path.write_text(access)

# MediaProjection already center-crops fixed presets in v0.1.33. Verify it stays
# aligned with the accessibility route rather than introducing a second policy.
capture = (root / "FilterCaptureService.java").read_text()
for token in (
    "GameBoyFilter.getCenterCropBounds(resolution, sourceWidth, sourceHeight)",
    "new Rect(crop[0], crop[1], crop[2], crop[3])",
    "ConsoleFrameRenderer.compose(lowResolutionBitmap, resolution)",
):
    if token not in capture:
        raise SystemExit(f"MediaProjection fixed-aspect invariant missing: {token}")

print("v0.1.46 fixed console screens crop correctly and handheld overlays keep aspect", flush=True)
