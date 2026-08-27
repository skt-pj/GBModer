#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_console_frame_v049.py <generated_src_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# v0.1.33 introduced a black fill for the device area outside fixed-aspect content.
# Keep the exact same content viewport/crop, but paint that excess area as the selected
# handheld shell instead of a flat black rectangle.
gpu_path = root / "GpuFilterRenderer.java"
gpu = gpu_path.read_text()
gpu = replace_once(
    gpu,
    '''        canvas.drawColor(Color.BLACK);
        canvas.save();
''',
    '''        ConsoleFrameRenderer.draw(
                canvas,
                mode,
                safeViewWidth,
                safeViewHeight,
                left,
                top,
                drawWidth,
                drawHeight
        );
        canvas.save();
''',
    "GPU excess-area console frame",
)
gpu_path.write_text(gpu)


# prepare_gpu_source.py already gives FilterOverlayView a reference named `service`.
# Reuse it so the CPU fallback paints the same selected GB/GBC/GBA/DS shell.
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()
if "private final FilterAccessibilityService service;" not in access:
    raise SystemExit("CPU overlay service reference missing before v0.1.49 finalizer")
access = replace_once(
    access,
    '''            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    current,
                    null,
                    new Rect(left, top, left + drawWidth, top + drawHeight),
                    paint
            );
''',
    '''            ConsoleFrameRenderer.draw(
                    canvas,
                    service.windowFilterMode,
                    viewWidth,
                    viewHeight,
                    left,
                    top,
                    drawWidth,
                    drawHeight
            );
            canvas.drawBitmap(
                    current,
                    null,
                    new Rect(left, top, left + drawWidth, top + drawHeight),
                    paint
            );
''',
    "CPU excess-area console frame",
)
access_path.write_text(access)

print("v0.1.49 fixed-aspect live excess area uses GB/GBC/GBA/DS console frames", flush=True)
