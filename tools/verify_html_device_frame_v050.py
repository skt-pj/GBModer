#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def require(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r} in {path}")
    print(f"PASS {label}")


def reject(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle in text:
        raise SystemExit(f"FAIL {label}: unexpected {needle!r} in {path}")
    print(f"PASS {label}")


require("version.properties", "VERSION_NAME=0.1.50", "version name")
require("version.properties", "VERSION_CODE=51", "version code")

renderer = "app/src/main/java/com/sktpj/gbmoder/ConsoleFrameRenderer.java"
require(renderer, "gameboy_glb_capture_device_modes_transparent_sheet_fixed_ordered_exports.html", "original HTML is named as frame source")
require(renderer, "Color.rgb(139, 149, 109)", "HTML body color #8b956d")
require(renderer, "Color.rgb(212, 215, 200)", "HTML device light color #d4d7c8")
require(renderer, "Color.rgb(181, 184, 170)", "HTML device dark color #b5b8aa")
require(renderer, "Color.rgb(75, 79, 64)", "HTML screen-frame color #4b4f40")
require(renderer, "Color.rgb(207, 213, 188)", "HTML screen-label color #cfd5bc")
require(renderer, "Color.rgb(111, 125, 86)", "HTML lcd-wrapper color #6f7d56")
require(renderer, "Color.rgb(155, 188, 15)", "HTML lcd-display color #9bbc0f")
require(renderer, "new LinearGradient(", "HTML device gradient approximation")
require(renderer, 'return "DOT MATRIX DISPLAY / 160 x 144 / 4 SHADES";', "GB HTML-style label")
require(renderer, 'return "DOT MATRIX DISPLAY / 160 x 144 / 15-BIT COLOR";', "GBC label")
require(renderer, 'return "DOT MATRIX DISPLAY / 240 x 160 / 15-BIT COLOR";', "GBA label")
require(renderer, 'return "DOT MATRIX DISPLAY / 256 x 192 / DS";', "DS label")
reject(renderer, "drawGbDetails", "invented handheld GB controls removed")
reject(renderer, "drawGbcDetails", "invented handheld GBC controls removed")
reject(renderer, "drawGbaDetails", "invented handheld GBA controls removed")
reject(renderer, "drawDsDetails", "invented handheld DS controls removed")
reject(renderer, "canvas.drawCircle", "invented handheld buttons and LED removed")

# The v0.1.49 integration point is retained: this validates that the restored HTML shell is
# used in both the GPU path and CPU fallback, not merely present as dead source code.
finalizer = "tools/finish_console_frame_v049.py"
require(finalizer, "GpuFilterRenderer.java", "GPU live path integration finalizer")
require(finalizer, "FilterAccessibilityService.java", "CPU fallback integration finalizer")
require(finalizer, "ConsoleFrameRenderer.draw(", "frame invocation generated in live paths")

build = "app/build.gradle"
require(build, "finish_console_frame_v049.py", "console frame finalizer tracked by Gradle")

generated_gpu = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/GpuFilterRenderer.java"
generated_cpu = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/FilterAccessibilityService.java"
require(generated_gpu, "ConsoleFrameRenderer.draw(", "GPU generated source uses restored HTML frame")
require(generated_cpu, "ConsoleFrameRenderer.draw(", "CPU generated source uses restored HTML frame")

print("ORIGINAL HTML DEVICE FRAME v0.1.50 AUTOMATED GATE: PASS")
