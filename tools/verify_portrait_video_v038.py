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


require("version.properties", "VERSION_NAME=0.1.40", "version name")
require("version.properties", "VERSION_CODE=41", "version code")
require("tools/prepare_all_sources_v020.py", "finish_portrait_video_v038.py", "portrait finalizer registered")
require("app/build.gradle", "finish_portrait_video_v038.py", "portrait finalizer tracked by Gradle")

generated_filter = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/GameBoyFilter.java"
require(generated_filter, "getVideoTargetWidth", "portrait-aware video target width")
require(generated_filter, "getVideoTargetHeight", "portrait-aware video target height")
require(generated_filter, "isFixedAspectResolution(resolution) && height > width", "fixed preset swaps only for portrait")
require(generated_filter, "getCenterCropBoundsForTarget", "target-oriented crop helper")
require(generated_filter, "resolution, width, height, targetWidth, targetHeight", "target-first decode uses oriented crop")

generated_gpu = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/VideoGpuConverter.java"
require(generated_gpu, "GameBoyFilter.getVideoTargetWidth", "GPU portrait output width")
require(generated_gpu, "GameBoyFilter.getVideoTargetHeight", "GPU portrait output height")
require(generated_gpu, "sourceFormat.setInteger(MediaFormat.KEY_ROTATION, 0)", "decoder automatic Surface rotation disabled")
require(generated_gpu, "getCenterCropBoundsForTarget", "GPU crop follows oriented output")
require(generated_gpu, 'decoder_rotation=0', "GPU rotation ownership diagnostic")
require(generated_gpu, 'portrait_output=', "GPU portrait output diagnostic")
require(generated_gpu, 'display=', "GPU display dimension diagnostic")
require(generated_gpu, "VideoGpuConverter.mapDisplayUvForRotation(\n                    rotation,", "manual display-space rotation retained")

generated_converter = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MediaFileConverter.java"
require(generated_converter, "GameBoyFilter.getVideoTargetWidth", "CPU fallback portrait output width")
require(generated_converter, "GameBoyFilter.getVideoTargetHeight", "CPU fallback portrait output height")
require(generated_converter, "GameBoyFilter.getCenterCropBoundsForTarget", "CPU fallback crop follows output orientation")

tests = "app/src/test/java/com/sktpj/gbmoder/GameBoyFilterResolutionTest.java"
require(tests, "portraitVideoSwapsFixedPresetDimensions", "portrait fixed preset unit test")
require(tests, "portraitVideoCropsToRotatedPresetAspect", "portrait crop unit test")
require(tests, "landscapeVideoKeepsFixedPresetDimensions", "landscape regression unit test")
require(tests, "portraitPhoneAndNativeVideoKeepSourceDimensions", "phone/native portrait regression unit test")
require(tests, "assertEquals(144, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_GB, 1080, 1920))", "GB portrait 144x160")
require(tests, "assertEquals(160, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_GBA, 1080, 1920))", "GBA portrait 160x240")
require(tests, "assertEquals(192, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_DS, 1080, 1920))", "DS portrait 192x256")

reject(
    "tools/finish_portrait_video_v038.py",
    "getTargetWidth(options.resolution, displayWidth));\n            int targetHeight = makeEven(GameBoyFilter.getTargetHeight(options.resolution, displayHeight))",
    "portrait GPU target no longer uses un-oriented fixed dimensions",
)

print("PORTRAIT VIDEO ASPECT v0.1.40 AUTOMATED GATE: PASS")
