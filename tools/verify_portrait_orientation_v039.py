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
require("tools/prepare_all_sources_v020.py", "finish_portrait_orientation_v039.py", "orientation finalizer registered")
require("app/build.gradle", "finish_portrait_orientation_v039.py", "orientation finalizer tracked by Gradle")

generated = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/VideoGpuConverter.java"
require(generated, "static float[] mapDisplayUvForRotation(", "testable GPU rotation mapping")
require(generated, "if (rotation == 90)", "90 degree branch")
require(generated, "mapped[i] = 1.0f - v;", "clockwise 90 x mapping")
require(generated, "mapped[i + 1] = u;", "clockwise 90 y mapping")
require(generated, "else if (rotation == 270)", "270 degree branch")
require(generated, "mapped[i] = v;", "clockwise 270 x mapping")
require(generated, "mapped[i + 1] = 1.0f - u;", "clockwise 270 y mapping")
require(generated, "VideoGpuConverter.mapDisplayUvForRotation(\n                    rotation,", "renderer uses corrected rotation mapping")
require(generated, "sourceFormat.setInteger(MediaFormat.KEY_ROTATION, 0)", "decoder rotation still neutralized")
require(generated, "rotation_mapping=clockwise_upright", "orientation diagnostic")

finalizer = "tools/finish_portrait_orientation_v039.py"
require(finalizer, "mapped[i] = 1.0f - v;", "90 mapping fixed in finalizer")
require(finalizer, "mapped[i + 1] = u;", "90 mapping direction fixed in finalizer")
require(finalizer, "mapped[i] = v;", "270 mapping fixed in finalizer")
require(finalizer, "mapped[i + 1] = 1.0f - u;", "270 mapping direction fixed in finalizer")

unit = "app/src/test/java/com/sktpj/gbmoder/VideoGpuRotationTest.java"
require(unit, "clockwiseNinetyKeepsPortraitTopUpright", "90 degree upright unit test")
require(unit, "clockwiseTwoSeventyKeepsPortraitTopUpright", "270 degree upright unit test")
require(unit, "clockwiseNinetyPreservesCroppedRegionOrientation", "cropped portrait orientation unit test")
require(unit, "zeroAndOneEightyRemainStable", "0/180 regression unit test")
require(unit, "new float[]{1f, 0f, 1f, 1f, 0f, 0f, 0f, 1f}", "expected clockwise 90 corner order")
require(unit, "new float[]{0f, 1f, 0f, 0f, 1f, 1f, 1f, 0f}", "expected clockwise 270 corner order")

print("PORTRAIT VIDEO UPRIGHT ORIENTATION v0.1.40 AUTOMATED GATE: PASS")
