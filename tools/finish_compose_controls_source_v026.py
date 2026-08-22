#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_compose_controls_source_v026.py <generated_src_root>")

root = Path(sys.argv[1])
path = root / "com/sktpj/gbmoder/MainActivity.java"
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    '''            public void onStart(int modePosition, int resolutionPosition, int brightness, int contrast, boolean dither) {
                uiModePosition = modePosition;
                uiResolutionPosition = resolutionPosition;
                uiBrightness = brightness;
                uiContrast = contrast;
                uiDither = dither;
                beginStartFlow();
            }
''',
    '''            public void onStart(
                    int modePosition,
                    int resolutionPosition,
                    int brightness,
                    int contrast,
                    boolean dither,
                    int captureRoutePosition,
                    boolean textRecognitionEnabled
            ) {
                uiModePosition = modePosition;
                uiResolutionPosition = resolutionPosition;
                uiBrightness = brightness;
                uiContrast = contrast;
                uiDither = dither;
                uiCaptureRoutePosition = captureRoutePosition;
                uiTextRecognitionEnabled = textRecognitionEnabled;
                beginStartFlow();
            }
''',
    "compose start parameters",
)

start_marker = "        LinearLayout routeRoot = new LinearLayout(this);\n"
end_marker = "        routeControls.post(routeControls::requestApplyInsets);\n"
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit("compose-only root: route control wrapper markers not found")
end += len(end_marker)
text = text[:start] + "        setContentView(composeView);\n" + text[end:]

path.write_text(text)
print("v0.1.26 single-scroll Compose controls applied")
