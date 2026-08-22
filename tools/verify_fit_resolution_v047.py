#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def require(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r} in {path}")
    print(f"PASS {label}")


require("version.properties", "VERSION_NAME=0.1.47", "version name")
require("version.properties", "VERSION_CODE=48", "version code")
require("tools/prepare_all_sources_v020.py", "finish_fit_resolution_v047.py", "Java fit finalizer registered")
require("tools/prepare_billing_release_v041.py", "finish_fit_resolution_ui_v047.py", "UI fit finalizer registered")
require("app/build.gradle", "finish_fit_resolution_v047.py", "Gradle tracks Java fit finalizer")
require("app/build.gradle", "finish_fit_resolution_ui_v047.py", "Gradle tracks UI fit finalizer")

game_filter = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/GameBoyFilter.java"
require(game_filter, 'RESOLUTION_GB_FIT = "gb_fit"', "GB fit alias")
require(game_filter, 'RESOLUTION_GBC_FIT = "gbc_fit"', "GBC fit alias")
require(game_filter, 'RESOLUTION_GBA_FIT = "gba_fit"', "GBA fit alias")
require(game_filter, 'RESOLUTION_DS_FIT = "ds_fit"', "DS fit alias")
require(game_filter, "public static boolean isFitResolution", "fit policy helper")
require(game_filter, "public static int[] getFitDestinationBounds", "fit destination geometry")
require(game_filter, "isFitResolution(resolution) || !isFixedAspectResolution(resolution)", "fit mode keeps complete source")

converter = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MediaFileConverter.java"
require(converter, "GameBoyFilter.getFitDestinationBounds(", "photo and CPU video fit inside")
require(converter, "new Rect(destination[0], destination[1], destination[2], destination[3])", "CPU destination uses fit rectangle")

capture = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/FilterCaptureService.java"
require(capture, "GameBoyFilter.getFitDestinationBounds(", "MediaProjection fit inside")

access = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/FilterAccessibilityService.java"
require(access, "GameBoyFilter.getFitDestinationBounds(", "accessibility live fit inside")
require(access, "ConsoleFrameRenderer.compose(sourceFrame, windowFilterResolution)", "fit screen stays inside handheld frame")

video = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/VideoGpuConverter.java"
require(video, "private final int contentWidth;", "GPU fit viewport state")
require(video, "frameSpec.screenLeft + contentLeft", "GPU fit viewport horizontally centered")
require(video, "outputHeight - frameSpec.screenTop - contentTop - contentHeight", "GPU fit viewport vertically centered")
require(video, "GameBoyFilter.getCenterCropBounds(", "crop mode retained in GPU video")

main = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java"
for position, constant in ((24, "RESOLUTION_GB_FIT"), (25, "RESOLUTION_GBC_FIT"), (26, "RESOLUTION_GBA_FIT"), (27, "RESOLUTION_DS_FIT")):
    require(main, f"if (position == {position}) return GameBoyFilter.{constant};", f"live UI position {position}")

ui = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt"
require(ui, "FIT_GB_RESOLUTION_POSITION = 24", "GB fit option position")
require(ui, "R.string.resolution_fit_gb_v047", "GB fit label")
require(ui, "R.string.resolution_fit_gbc_v047", "GBC fit label")
require(ui, "R.string.resolution_fit_gba_v047", "GBA fit label")
require(ui, "R.string.resolution_fit_ds_v047", "DS fit label")
require(ui, "GameBoyFilter.RESOLUTION_GB_FIT", "conversion GB fit mapping")
require(ui, "GameBoyFilter.RESOLUTION_DS_FIT", "conversion DS fit mapping")

for values_dir in ("values", "values-ja", "values-zh-rCN", "values-ko"):
    strings = f"app/src/main/res/{values_dir}/strings_fit_v047.xml"
    require(strings, 'name="resolution_fit_gb_v047"', f"{values_dir} GB fit localization")
    require(strings, 'name="resolution_fit_ds_v047"', f"{values_dir} DS fit localization")

workflow = ".github/workflows/build-apk.yml"
require(workflow, "python3 tools/verify_fit_resolution_v047.py", "fit resolution gate in CI")

print("FIT-INSIDE FIXED RESOLUTION v0.1.47 AUTOMATED GATE: PASS")
