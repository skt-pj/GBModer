#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (repo / path).read_text()


def need(path: str, needle: str, label: str) -> None:
    text = read(path)
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r} in {path}")
    print(f"PASS {label}")


def reject(path: str, needle: str, label: str) -> None:
    text = read(path)
    if needle in text:
        raise SystemExit(f"FAIL {label}: unexpected {needle!r} in {path}")
    print(f"PASS {label}")


need("version.properties", "VERSION_NAME=0.1.49", "version name")
need("version.properties", "VERSION_CODE=50", "version code")
need("tools/prepare_all_sources_v020.py", "finish_console_frame_v049.py", "console-frame finalizer registered")
need("app/build.gradle", "finish_console_frame_v049.py", "console-frame finalizer tracked by Gradle")

# v0.1.47/48 changed the settings screen, which was the wrong target. They must not run.
reject("tools/prepare_billing_release_v041.py", "finish_mode_backdrop_v047.py", "v0.1.47 settings card removed from build")
reject("tools/prepare_billing_release_v041.py", "finish_mode_shell_v048.py", "v0.1.48 settings background removed from build")

ui = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt"
reject(ui, "ModeBackdrop(modePosition)", "no fake settings mode backdrop")
reject(ui, "modeShellColor", "no mode-colored settings page")
reject(ui, 'testTag("mode-shell-background")', "no settings shell test surface")
need(ui, "androidx.compose.material3.lightColorScheme(", "normal light app UI retained")
need(ui, "background = Color(0xFFE2E6D6)", "normal app background retained")

renderer = "app/src/main/java/com/sktpj/gbmoder/ConsoleFrameRenderer.java"
need(renderer, "final class ConsoleFrameRenderer", "console frame renderer source")
for mode in ("MODE_GB", "MODE_GBC", "MODE_GBA", "MODE_DS"):
    need(renderer, mode, f"console renderer {mode}")
for label in ('label = "GB"', 'label = "GBC"', 'label = "GBA"', 'label = "DS"'):
    need(renderer, label, f"console identity {label}")
need(renderer, "drawGbDetails", "GB hardware details")
need(renderer, "drawGbcDetails", "GBC hardware details")
need(renderer, "drawGbaDetails", "GBA hardware details")
need(renderer, "drawDsDetails", "DS hardware details")

# The v0.1.33 fixed-aspect/crop behavior remains; only the former black excess area changes.
gpu = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/GpuFilterRenderer.java"
need(gpu, "targetAspect", "fixed-aspect live GPU viewport retained")
need(gpu, "cropOffset", "live GPU center crop retained")
need(gpu, "ConsoleFrameRenderer.draw(", "live GPU uses console frame outside content")
reject(gpu, "canvas.drawColor(Color.BLACK);\n        canvas.save();", "live GPU flat black excess fill removed")

access = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/FilterAccessibilityService.java"
need(access, "private final FilterAccessibilityService service;", "CPU fallback tracks selected mode")
need(access, "service.windowFilterMode", "CPU fallback uses selected GB/GBC/GBA/DS mode")
need(access, "ConsoleFrameRenderer.draw(", "CPU fallback uses console frame outside content")
reject(access, "canvas.drawColor(Color.BLACK);\n            canvas.drawBitmap(\n                    current,", "CPU fallback flat black excess fill removed")

need("tools/finish_aspect_crop_v033.py", "getCenterCropBounds", "existing center crop logic retained")
need("tools/finish_2048_fit_v044.py", "contain", "2048TD contain-fit patch retained")
need("tools/finish_text_disabled_v046.py", "false", "text-recognition-off finalizer retained")

print("LIVE CONSOLE FRAME v0.1.49 AUTOMATED GATE: PASS")
