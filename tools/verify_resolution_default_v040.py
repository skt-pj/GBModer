#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def require(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r} in {path}")
    print(f"PASS {label}")


require("version.properties", "VERSION_NAME=0.1.45", "version name")
require("version.properties", "VERSION_CODE=46", "version code")
require("tools/prepare_all_sources_v020.py", "finish_resolution_default_v040.py", "legacy resolution finalizer registered")
require("tools/prepare_all_sources_v020.py", "finish_resolution_default_v045.py", "30-percent Java finalizer registered")
require("tools/prepare_billing_release_v041.py", "finish_text_defaults_v045.py", "30-percent Kotlin finalizer registered")
require("app/build.gradle", "finish_resolution_default_v045.py", "30-percent Java finalizer tracked")
require("app/build.gradle", "finish_text_defaults_v045.py", "30-percent Kotlin finalizer tracked")

ui = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt"
require(ui, "private const val DEFAULT_RESOLUTION_POSITION = 9", "compiled UI initial resolution is 30 percent")
require(ui, 'add("端末比 / 30%（テキスト推奨）")', "compiled 30 percent recommendation label")
require(ui, "GameBoyFilter.phoneResolution((resolutionPosition - 3) * 5)", "30 percent remains a selectable phone-ratio resolution")
require(ui, "else -> GameBoyFilter.RESOLUTION_GB", "compiled invalid-position fallback remains safe")

localization = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerLocalization.kt"
require(localization, '"端末比 / 30%（テキスト推奨）" to R.string.phone_ratio_text_recommended_v041', "30 percent recommendation localized")

generated_main = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java"
require(generated_main, "private int uiResolutionPosition = 9;", "live-mode state initial resolution is 30 percent")
require(generated_main, "return GameBoyFilter.RESOLUTION_GB;", "generated invalid-position fallback remains safe")

for values_dir in ("values", "values-ja", "values-zh-rCN", "values-ko"):
    strings = f"app/src/main/res/{values_dir}/strings_release_v041.xml"
    require(strings, 'name="phone_ratio_text_recommended_v041"', f"{values_dir} recommended resolution copy")
    require(strings, "30%", f"{values_dir} recommendation is 30 percent")

print("30% DEFAULT + TEXT RECOMMENDATION v0.1.45 AUTOMATED GATE: PASS")
