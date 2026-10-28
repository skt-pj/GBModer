#!/usr/bin/env python3
"""Add a separately selectable live layout without changing GB/GBC/GBA/DS filters."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_live_layout_java_v057.py <generated_java_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"


def once(source: str, old: str, new: str, label: str) -> str:
    matches = source.count(old)
    if matches != 1:
        raise SystemExit(f"{label}: expected one match, found {matches}")
    return source.replace(old, new, 1)


main_path = root / "MainActivity.java"
main = main_path.read_text()
main = once(
    main,
    "                    int captureRoutePosition,\n                    boolean textRecognitionEnabled\n            ) {",
    "                    int captureRoutePosition,\n                    boolean textRecognitionEnabled,\n                    int layoutPosition\n            ) {",
    "Compose action layout parameter",
)
main = once(
    main,
    "                uiTextRecognitionEnabled = false;\n                beginStartFlow();",
    "                uiTextRecognitionEnabled = false;\n"
    "                LiveLayoutRenderer.setLayoutMode(layoutPosition);\n"
    "                beginStartFlow();",
    "set selected layout before capture begins",
)
main_path.write_text(main)

access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()
access = once(
    access,
    "ConsoleFrameRenderer.getContentRect(\n                    service.windowFilterMode,",
    "LiveLayoutRenderer.getContentRect(\n                    service.windowFilterMode,",
    "CPU content rectangle",
)
access = once(
    access,
    "ConsoleFrameRenderer.draw(\n                    canvas,\n                    service.windowFilterMode,",
    "LiveLayoutRenderer.draw(\n                    canvas,\n                    service.windowFilterMode,",
    "CPU console or SGB decoration",
)
access = once(
    access,
    "ConsoleFrameRenderer.getSourceRectForWidthFit(\n                    service.windowFilterMode,",
    "LiveLayoutRenderer.getSourceRectForWidthFit(\n                    service.windowFilterMode,",
    "CPU crop respects layout",
)
access_path.write_text(access)

gpu_path = root / "GpuFilterRenderer.java"
gpu = gpu_path.read_text()
gpu = once(
    gpu,
    "ConsoleFrameRenderer.getContentRect(\n                mode,",
    "LiveLayoutRenderer.getContentRect(\n                mode,",
    "GPU content rectangle",
)
gpu = once(
    gpu,
    "ConsoleFrameRenderer.getSourceCropForWidthFit(\n                mode,",
    "LiveLayoutRenderer.getSourceCropForWidthFit(\n                mode,",
    "GPU crop respects layout",
)
gpu = once(
    gpu,
    "ConsoleFrameRenderer.draw(\n                canvas,\n                mode,",
    "LiveLayoutRenderer.draw(\n                canvas,\n                mode,",
    "GPU console or SGB decoration",
)
gpu_path.write_text(gpu)
print("v0.1.57 fullscreen, chassis and Super Game Boy Java live layouts applied", flush=True)
