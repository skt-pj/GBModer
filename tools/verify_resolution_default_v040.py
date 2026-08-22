#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def require(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r} in {path}")
    print(f"PASS {label}")


require("version.properties", "VERSION_NAME=0.1.43", "version name")
require("version.properties", "VERSION_CODE=44", "version code")
require("tools/prepare_all_sources_v020.py", "finish_resolution_default_v040.py", "GB-default Java finalizer registered")
require("app/build.gradle", "finish_resolution_default_v040.py", "GB-default Java finalizer tracked")
require("tools/prepare_billing_kotlin_v035.py", 'DEFAULT_RESOLUTION_POSITION = 0', "generated Compose defaults to GB")
require("tools/prepare_billing_kotlin_v035.py", '端末比 / 20%（テキスト表示時推奨）', "v040 recommendation input retained")
require("tools/prepare_billing_kotlin_v035.py", 'else -> GameBoyFilter.RESOLUTION_GB', "Compose invalid-position fallback is GB")

ui = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt"
require(ui, "private const val DEFAULT_RESOLUTION_POSITION = 0", "compiled UI initial resolution is GB")
require(ui, 'add("端末比 / 20%（テキスト推奨）")', "compiled concise 20 percent label")
require(ui, '文字表示には端末比 / 20%を推奨します。', "compiled concise text recommendation")
require(ui, "GameBoyFilter.phoneResolution((resolutionPosition - 3) * 5)", "20 percent remains a selectable phone-ratio resolution")
require(ui, "else -> GameBoyFilter.RESOLUTION_GB", "compiled UI fallback is GB")

localization = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerLocalization.kt"
require(localization, "R.string.phone_ratio_text_recommended_v041", "recommended resolution localized")
require(localization, "R.string.readable_text_description_v041", "text recommendation description localized")

generated_main = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java"
require(generated_main, "private int uiResolutionPosition = 0;", "live-mode state initial resolution is GB")
require(generated_main, "return GameBoyFilter.RESOLUTION_GB;", "generated resolution fallback includes GB")

for values_dir in ("values", "values-ja", "values-zh-rCN", "values-ko"):
    strings = f"app/src/main/res/{values_dir}/strings_release_v041.xml"
    require(strings, 'name="phone_ratio_text_recommended_v041"', f"{values_dir} recommended resolution copy")
    require(strings, 'name="readable_text_description_v041"', f"{values_dir} text recommendation copy")

print("GB DEFAULT + 20% TEXT RECOMMENDATION v0.1.43 AUTOMATED GATE: PASS")
