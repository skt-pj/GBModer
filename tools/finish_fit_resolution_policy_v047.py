#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_fit_resolution_policy_v047.py <generated_java_root>")

root = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


filter_path = root / "GameBoyFilter.java"
text = filter_path.read_text()
text = replace_once(
    text,
    '''    public static boolean isFitResolution(String resolution) {
        return RESOLUTION_GB_FIT.equals(resolution)
                || RESOLUTION_GBC_FIT.equals(resolution)
                || RESOLUTION_GBA_FIT.equals(resolution)
                || RESOLUTION_DS_FIT.equals(resolution);
    }

''',
    '''    public static boolean isFitResolution(String resolution) {
        return RESOLUTION_GB_FIT.equals(resolution)
                || RESOLUTION_GBC_FIT.equals(resolution)
                || RESOLUTION_GBA_FIT.equals(resolution)
                || RESOLUTION_DS_FIT.equals(resolution);
    }

    public static String safeResolutionPolicy(String requestedResolution) {
        if (isFitResolution(requestedResolution)) {
            return requestedResolution;
        }
        return safeResolution(requestedResolution);
    }

''',
    "fit resolution policy helper",
)
filter_path.write_text(text)

converter_path = root / "MediaFileConverter.java"
text = converter_path.read_text()
text = replace_once(
    text,
    "            this.resolution = GameBoyFilter.safeResolution(resolution);\n",
    "            this.resolution = GameBoyFilter.safeResolutionPolicy(resolution);\n",
    "conversion options retain fit policy",
)
converter_path.write_text(text)

capture_path = root / "FilterCaptureService.java"
text = capture_path.read_text()
text = replace_once(
    text,
    "        resolution = GameBoyFilter.safeResolution(intent.getStringExtra(EXTRA_RESOLUTION));\n",
    "        resolution = GameBoyFilter.safeResolutionPolicy(intent.getStringExtra(EXTRA_RESOLUTION));\n",
    "MediaProjection retains fit policy",
)
capture_path.write_text(text)

access_path = root / "FilterAccessibilityService.java"
text = access_path.read_text()
text = replace_once(
    text,
    "        windowFilterResolution = GameBoyFilter.safeResolution(resolution);\n",
    "        windowFilterResolution = GameBoyFilter.safeResolutionPolicy(resolution);\n",
    "accessibility live route retains fit policy",
)
access_path.write_text(text)

print("v0.1.47 fit resolution policy survives conversion and both live capture routes", flush=True)
