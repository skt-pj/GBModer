#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_2048_content_v043.py <generated_java_root>")

root = Path(sys.argv[1]).resolve()
path = root / "com/sktpj/gbmoder/FilterAccessibilityService.java"
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    "    private boolean windowFilterDither = true;\n",
    "    private boolean windowFilterDither = true;\n    private boolean allowOwnPackageWindow = false;\n",
    "embedded-content state",
)

replace_once(
    "        windowFilterMode = safeMode(mode);\n",
    "        allowOwnPackageWindow = false;\n        windowFilterMode = safeMode(mode);\n",
    "normal filter own-package reset",
)

replace_once(
    "    public void stopWindowFilter() {\n",
    '''    public void startEmbeddedContentFilter(
            String mode,
            String resolution,
            int brightness,
            int contrast,
            boolean dither
    ) {
        startWindowFilter(mode, resolution, brightness, contrast, dither, false);
        allowOwnPackageWindow = true;
        Log.i(TAG, "Embedded content filter enabled for own package");
    }

    public void stopWindowFilter() {
''',
    "embedded-content start method",
)

replace_once(
    '''    public void stopWindowFilter() {
        windowFilterRunning = false;
        screenshotInFlight = false;
''',
    '''    public void stopWindowFilter() {
        windowFilterRunning = false;
        allowOwnPackageWindow = false;
        screenshotInFlight = false;
''',
    "embedded-content stop reset",
)

method_start_marker = "    private TargetWindow resolveActiveApplicationWindow() {\n"
method_end_marker = "\n    public void prepareProbe() {\n"
method_start = text.find(method_start_marker)
method_end = text.find(method_end_marker, method_start)
if method_start < 0 or method_end < 0:
    raise SystemExit("resolveActiveApplicationWindow method boundaries not found")

method_text = text[method_start:method_end]
old_skip = '''                if (getPackageName().equals(packageName) || SYSTEM_UI_PACKAGE.equals(packageName)) {
                    continue;
                }
'''
new_skip = '''                if ((!allowOwnPackageWindow && getPackageName().equals(packageName))
                        || SYSTEM_UI_PACKAGE.equals(packageName)) {
                    continue;
                }
'''
count = method_text.count(old_skip)
if count != 2:
    raise SystemExit(
        f"resolveActiveApplicationWindow own-package gates: expected exactly two matches, got {count}"
    )
method_text = method_text.replace(old_skip, new_skip, 2)
text = text[:method_start] + method_text + text[method_end:]

path.write_text(text)
print("v0.1.43 embedded 2048TD filter route prepared", flush=True)
