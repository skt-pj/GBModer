#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
prepare = (root / "tools/prepare_all_sources_v020.py").read_text()
generated = root / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder"
filter_text = (generated / "GameBoyFilter.java").read_text()
converter = (generated / "MediaFileConverter.java").read_text()
gpu_video = (generated / "VideoGpuConverter.java").read_text()
gpu_live = (generated / "GpuFilterRenderer.java").read_text()
capture = (generated / "FilterCaptureService.java").read_text()
access = (generated / "FilterAccessibilityService.java").read_text()
diagnostics = (generated / "VideoPipelineDiagnostics.java").read_text()
tests = (root / "app/src/test/java/com/sktpj/gbmoder/GameBoyFilterResolutionTest.java").read_text()


def need(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r}")
    print(f"PASS {label}")


need(prepare, "finish_aspect_crop_v033.py", "aspect crop finisher registered")

# Shared geometry and unchanged fixed output sizes.
need(filter_text, "getCenterCropBounds", "shared center crop helper")
need(filter_text, "getCenterCropWorkingWidth", "crop-aware target-first working width")
need(filter_text, "getCenterCropWorkingHeight", "crop-aware target-first working height")
need(filter_text, "return 240;", "GBA fixed width retained")
need(filter_text, "return 256;", "DS fixed width retained")
need(filter_text, "return 160;", "GB/GBC fixed width retained")
need(filter_text, "return 144;", "GB/GBC fixed height retained")

# File conversion routes.
need(converter, "GameBoyFilter.getCenterCropBounds", "photo and CPU fallback center crop")
need(converter, "new Rect(crop[0], crop[1], crop[2], crop[3])", "bitmap crop source rect")
need(converter, "workingWidth", "CPU target-first decode keeps source aspect")
need(converter, "workingHeight", "CPU target-first decode height keeps source aspect")

# GPU video route crops display-oriented texture coordinates rather than stretching.
need(gpu_video, "displaySourceWidth", "GPU video display-oriented source dimensions")
need(gpu_video, "GameBoyFilter.getCenterCropBounds", "GPU video center crop")
need(gpu_video, "cropLeft", "GPU video crop left")
need(gpu_video, "cropRight", "GPU video crop right")
need(gpu_video, "textureCoordinates(\n                    rotation,", "GPU video crop coordinates sent to shader")
need(gpu_video, '" center_crop=true"', "GPU video crop logged")
if "textureCoordinates(rotation)" in gpu_video:
    raise SystemExit("FAIL GPU video still maps the whole source directly to fixed output")
print("PASS GPU video whole-source stretch removed")

# Live GPU/CPU routes keep target display aspect, blacking the excess device area.
need(gpu_live, '"uniform float2 cropOffset;', "live GPU crop offset")
need(gpu_live, '"uniform float2 cropSize;', "live GPU crop size")
need(gpu_live, "targetAspect", "live GPU target aspect")
need(gpu_live, "canvas.drawColor(Color.BLACK)", "live GPU excess area fill")
need(access, "frameAspect", "live CPU fallback frame aspect")
need(access, "canvas.drawColor(Color.BLACK)", "live CPU fallback excess area fill")
need(capture, "GameBoyFilter.getCenterCropBounds(resolution, sourceWidth, sourceHeight)", "MediaProjection crop before downsample")

# Diagnostics benchmark the same crop-aware path.
need(diagnostics, "GameBoyFilter.getCenterCropWorkingWidth", "diagnostics crop-aware target-first width")
need(diagnostics, "GameBoyFilter.getCenterCropBounds", "diagnostics center crop resize")

# Geometry regression examples: landscape, portrait, and phone/native no-crop.
need(tests, "fixedPresetsCenterCropWideSourcesInsteadOfStretching", "wide source crop unit test")
need(tests, "fixedPresetsCenterCropTallSourcesInsteadOfStretching", "tall source crop unit test")
need(tests, "phoneAndNativeResolutionKeepWholeSourceAspect", "phone/native no-crop unit test")
need(tests, "targetFirstDecodeKeepsSourceAspectUntilCrop", "target-first working-size unit test")

print("FIXED PRESET ASPECT PRESERVATION v0.1.33 FEATURE GATE: PASS")
