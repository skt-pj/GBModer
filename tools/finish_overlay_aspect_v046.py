#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_overlay_aspect_v046.py <generated_java_root>")

root = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()

access = replace_once(
    access,
    '''    public void showFrame(Bitmap frame) {
        runOnMain(() -> {
            ensureOverlay();
            updateOverlayBoundsIfNeeded();
            overlayView.setFrame(frame);
            updateOverlayVisibility();
        });
    }
''',
    '''    public void showFrame(Bitmap frame) {
        showFrame(frame, false);
    }

    public void showFrame(Bitmap frame, boolean preserveAspect) {
        runOnMain(() -> {
            ensureOverlay();
            updateOverlayBoundsIfNeeded();
            overlayView.setFrame(frame, preserveAspect);
            updateOverlayVisibility();
        });
    }
''',
    "public overlay aspect overload",
)

access = replace_once(
    access,
    '''            captureVisible = true;
            overlayView.setFrame(frame);
            updateSystemUiVisibility();
''',
    '''            captureVisible = true;
            overlayView.setFrame(
                    frame,
                    ConsoleFrameRenderer.isFixedResolution(windowFilterResolution)
            );
            updateSystemUiVisibility();
''',
    "accessibility fixed-frame aspect",
)

access = replace_once(
    access,
    '''        private Bitmap frame;
        private boolean probeMode = false;
''',
    '''        private Bitmap frame;
        private boolean probeMode = false;
        private boolean preserveFrameAspect = false;
''',
    "overlay aspect state",
)

access = replace_once(
    access,
    '''        void showProbe() {
            probeMode = true;
            Bitmap oldFrame = frame;
''',
    '''        void showProbe() {
            probeMode = true;
            preserveFrameAspect = false;
            Bitmap oldFrame = frame;
''',
    "probe aspect reset",
)

access = replace_once(
    access,
    '''        void setFrame(Bitmap newFrame) {
            probeMode = false;
            Bitmap oldFrame = frame;
            frame = newFrame;
            if (oldFrame != null && oldFrame != newFrame && !oldFrame.isRecycled()) {
                oldFrame.recycle();
            }
            invalidate();
        }
''',
    '''        void setFrame(Bitmap newFrame) {
            setFrame(newFrame, false);
        }

        void setFrame(Bitmap newFrame, boolean preserveAspect) {
            probeMode = false;
            preserveFrameAspect = preserveAspect;
            Bitmap oldFrame = frame;
            frame = newFrame;
            if (oldFrame != null && oldFrame != newFrame && !oldFrame.isRecycled()) {
                oldFrame.recycle();
            }
            invalidate();
        }
''',
    "overlay setFrame aspect overload",
)

access = replace_once(
    access,
    '''            canvas.drawBitmap(
                    current,
                    null,
                    new Rect(0, 0, getWidth(), getHeight()),
                    paint
            );
''',
    '''            Rect destination = preserveFrameAspect
                    ? ConsoleFrameRenderer.fitCenterRect(
                            current.getWidth(),
                            current.getHeight(),
                            getWidth(),
                            getHeight()
                    )
                    : new Rect(0, 0, getWidth(), getHeight());
            canvas.drawBitmap(
                    current,
                    null,
                    destination,
                    paint
            );
''',
    "fit-center handheld frame",
)

access = replace_once(
    access,
    '''        void release() {
            Bitmap current = frame;
            frame = null;
''',
    '''        void release() {
            Bitmap current = frame;
            frame = null;
            preserveFrameAspect = false;
''',
    "overlay aspect release reset",
)

access_path.write_text(access)

capture_path = root / "FilterCaptureService.java"
capture = capture_path.read_text()
capture = replace_once(
    capture,
    "                    service.showFrame(frameForOverlay);\n",
    "                    service.showFrame(\n"
    "                            frameForOverlay,\n"
    "                            ConsoleFrameRenderer.isFixedResolution(resolution)\n"
    "                    );\n",
    "MediaProjection fixed-frame aspect",
)
capture_path.write_text(capture)

print("v0.1.46 handheld overlays preserve console aspect", flush=True)
