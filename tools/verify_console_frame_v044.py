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


require("version.properties", "VERSION_NAME=0.1.46", "version name")
require("version.properties", "VERSION_CODE=47", "version code")
require("tools/prepare_all_sources_v020.py", "run_console_frame_v044.py", "console frame compatibility wrapper registered")
require("tools/run_console_frame_v044.py", "finish_console_frame_v044.py", "console frame finalizer executed by wrapper")
require("tools/prepare_all_sources_v020.py", "finish_overlay_aspect_v046.py", "v046 aspect correction registered after console frame")
require("app/build.gradle", "run_console_frame_v044.py", "console frame wrapper tracked by Gradle")
require("app/build.gradle", "finish_console_frame_v044.py", "console frame finalizer tracked by Gradle")
require("app/build.gradle", "finish_overlay_aspect_v046.py", "v046 aspect correction tracked by Gradle")

source = "app/src/main/java/com/sktpj/gbmoder/ConsoleFrameRenderer.java"
require(source, "static boolean isFixedResolution", "fixed-resolution selector")
require(source, "RESOLUTION_GB", "GB frame")
require(source, "RESOLUTION_GBC", "GBC frame")
require(source, "RESOLUTION_GBA", "GBA frame")
require(source, "RESOLUTION_DS", "DS frame")
require(source, "static Bitmap compose", "bitmap frame composition")
require(source, "static Rect fitCenterRect", "aspect-preserving fit helper retained")
require(source, "drawVerticalBody", "vertical handheld body")
require(source, "drawGbaBody", "GBA-style body")
require(source, "drawDsBody", "DS-style clamshell body")

reject(source, 'RESOLUTION_PHONE_20.equals(safe)', "phone ratio remains full-frame")
reject(source, 'RESOLUTION_NATIVE.equals(safe)', "native remains full-frame")

generated_renderer = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/ConsoleFrameRenderer.java"
require(generated_renderer, "class ConsoleFrameRenderer", "frame renderer copied into generated source")

generated_converter = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MediaFileConverter.java"
require(generated_converter, "ConsoleFrameRenderer.compose(converted, options.resolution)", "photo output gets frame")
require(generated_converter, "int encodedWidth = cpuConsoleFrame ? cpuFrameSpec.outputWidth : targetWidth", "CPU video encoder frame width")
require(generated_converter, "ConsoleFrameRenderer.compose(filtered, options.resolution)", "CPU video frame composition")

generated_access = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/FilterAccessibilityService.java"
require(generated_access, "!ConsoleFrameRenderer.isFixedResolution(windowFilterResolution)", "fixed live presets use framed CPU route")
require(generated_access, "ConsoleFrameRenderer.compose(sourceFrame, windowFilterResolution)", "accessibility live frame composition")
require(generated_access, "final Bitmap frame = preparedFrame", "accessibility framed bitmap is lambda-safe")
require(generated_access, "GameBoyFilter.getCenterCropBounds(\n                    windowFilterResolution,", "accessibility source center-crops to selected console display")
require(generated_access, "new Rect(crop[0], crop[1], crop[2], crop[3])", "accessibility crop is used before fixed-size downsample")
require(generated_access, "float frameAspect = current.getWidth() / (float) Math.max(1, current.getHeight());", "complete handheld bitmap keeps its aspect")
require(generated_access, "int left = (viewWidth - drawWidth) / 2;", "handheld frame is horizontally centered")
require(generated_access, "int top = (viewHeight - drawHeight) / 2;", "handheld frame is vertically centered")
require(generated_access, "new Rect(left, top, left + drawWidth, top + drawHeight)", "overlay does not stretch handheld frame to phone bounds")

generated_capture = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/FilterCaptureService.java"
require(generated_capture, "GameBoyFilter.getCenterCropBounds(resolution, sourceWidth, sourceHeight)", "MediaProjection fixed screen center crop retained")
require(generated_capture, "new Rect(crop[0], crop[1], crop[2], crop[3])", "MediaProjection uses crop before downsample")
require(generated_capture, "ConsoleFrameRenderer.compose(lowResolutionBitmap, resolution)", "MediaProjection live frame composition")

generated_video = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/VideoGpuConverter.java"
require(generated_video, "int outputWidth = consoleFrame ? frameSpec.outputWidth : targetWidth", "GPU framed encoder width")
require(generated_video, "createSurfaceEncoder(outputWidth, outputHeight, nominalFps)", "GPU Surface encoder uses framed canvas")
require(generated_video, 'console_frame=" + consoleFrame', "GPU frame diagnostic")
require(generated_video, "drawConsoleBody();", "GPU draws hardware body")
require(generated_video, "frameSpec.screenLeft", "GPU screen viewport uses frame geometry")
require(generated_video, "GLES20.GL_SCISSOR_TEST", "GPU body stays on Surface path")
require(generated_video, "outputHeight - frameSpec.screenTop - targetHeight", "GPU top-origin frame geometry mapped to GL viewport")
require(generated_video, "sourceFormat.setInteger(MediaFormat.KEY_ROTATION, 0)", "portrait rotation ownership preserved")
require(generated_video, "VideoGpuConverter.mapDisplayUvForRotation", "upright rotation mapper preserved")

test = "app/src/test/java/com/sktpj/gbmoder/ConsoleFrameRendererTest.java"
require(test, "onlyFixedResolutionsUseConsoleFrame", "fixed-only unit test")
require(test, "gbFrameKeepsExactScreenInsideBody", "GB frame geometry test")
require(test, "gbaFrameSupportsPortraitVideoScreen", "portrait GBA frame test")
require(test, "dsFrameCreatesClamshellSpace", "DS frame geometry test")

print("FIXED RESOLUTION HANDHELD FRAME v0.1.46 ASPECT GATE: PASS")
