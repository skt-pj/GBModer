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


# CPU fallback uses the same console backdrop and selected live mode. The filtered
# bitmap is still drawn last, so the frame never covers game/application content.
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()
access = replace_once(
    access,
    '''    private static final class FilterOverlayView extends View {
        private final Paint paint = new Paint();
''',
    '''    private static final class FilterOverlayView extends View {
        private final FilterAccessibilityService service;
        private final Paint paint = new Paint();
''',
    "CPU overlay service reference",
)
access = replace_once(
    access,
    '''        FilterOverlayView(FilterAccessibilityService context) {
            super(context);
            paint.setFilterBitmap(false);
''',
    '''        FilterOverlayView(FilterAccessibilityService context) {
            super(context);
            service = context;
            paint.setFilterBitmap(false);
''',
    "CPU overlay selected mode source",
)
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
