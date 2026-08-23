#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
gen = root / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder"
config = (root / "app/src/main/res/xml/accessibility_service_config.xml").read_text()
accessibility = (gen / "FilterAccessibilityService.java").read_text()
capture = (gen / "FilterCaptureService.java").read_text()


def need(text, value, label):
    if value not in text:
        raise SystemExit(f"FAIL {label}: {value}")
    print(f"PASS {label}")


for value in (
    "typeViewScrolled",
    "typeWindowContentChanged",
    "typeViewTextChanged",
    "typeWindowStateChanged",
    "typeWindowsChanged",
):
    need(config, value, "event subscription")

need(accessibility, "configureTextSyncEvents();", "runtime subscription")
need(accessibility, "windowTextRecognitionEnabled || externalTextRecognitionActive", "cross route invalidation")
need(accessibility, "setExternalTextRecognitionActive", "external route state")
need(capture, "frameContentRevision", "capture revision")
need(capture, "isTextContentStable(frameContentRevision, 100L)", "stable text gate")
need(capture, "reason=content_revision_before_copy", "drop before copy")
need(capture, "reason=content_revision_before_present", "drop before present")
need(capture, "setExternalTextRecognitionActive(false)", "cleanup state")

show_start = accessibility.find("    public void showFrame(Bitmap frame) {")
show_end = accessibility.find("    private void showFrame(Bitmap frame, Rect bounds) {", show_start)
if show_start < 0 or show_end < 0:
    raise SystemExit("FAIL MediaProjection showFrame method")
show_body = accessibility[show_start:show_end]
need(show_body, "captureVisible = true;", "fresh MediaProjection frame restores overlay visibility")

filter_pos = capture.find("GameBoyFilter.apply(")
text_pos = capture.find("applyFontMinTextOverlay(", filter_pos)
if filter_pos < 0 or text_pos <= filter_pos:
    raise SystemExit("FAIL processing order")
print("PASS processing order")
print("TEXT SCROLL SYNC AUTOMATED GATE: PASS")
