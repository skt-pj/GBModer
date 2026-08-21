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


require("version.properties", "VERSION_NAME=0.1.41", "version name")
require("version.properties", "VERSION_CODE=42", "version code")

build = "app/build.gradle"
require(build, "GBMODER_DEBUG_FEATURES", "explicit build-time debug flag")
require(build, "?: 'false'", "debug features default off")
require(build, "buildConfigField 'boolean', 'DEBUG_FEATURES'", "BuildConfig debug flag")
require(build, "manifestPlaceholders = [debugFeaturesEnabled:", "manifest debug placeholder")
require(build, "prepare_billing_release_v041.py", "v041 Kotlin wrapper tracked")
require(build, "finish_release_ui_v041.py", "v041 release UI finalizer tracked")
require(build, "finish_debug_features_v041.py", "v041 Java gate tracked")

manifest = "app/src/main/AndroidManifest.xml"
for component in (
    ".LiveModePaywallActivity",
    ".VideoDiagnosticsActivity",
    ".FilterAccessibilityService",
    ".FilterCaptureService",
    ".FilterControlReceiver",
):
    require(manifest, component, f"{component} manifest component retained")
require(manifest, 'android:enabled="${debugFeaturesEnabled}"', "debug-only components use manifest flag")

ui = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt"
require(ui, "BuildConfig.DEBUG_FEATURES && !state.accessibilityReady", "accessibility setup debug-only")
require(ui, "if (BuildConfig.DEBUG_FEATURES) {\n            ToggleSettingRow(", "readable-text control debug-only")
require(ui, "SectionTitle(androidx.compose.ui.res.stringResource(R.string.live_mode_title))", "live section retained behind debug gate")
require(ui, "if (BuildConfig.DEBUG_FEATURES) {\n            DiagnosticsCard(", "diagnostics card debug-only")
require(ui, 'SectionTitle("表示モード", modifier = Modifier.weight(1f))', "menu shares display-mode row")
require(ui, ".padding(horizontal = 20.dp, vertical = 8.dp)", "compact top content padding")
require(ui, "Arrangement.spacedBy(14.dp)", "compact settings rhythm")
require(ui, 'description = "",', "dither explanation removed")
require(ui, '文字表示には端末比 / 20%を推奨します。', "concise text recommendation")
reject(ui, 'testTag("top-quiet-zone")', "standalone top quiet-zone removed")
reject(ui, "端末比は5%刻みで選択できます。表示モードの色・階調処理と解像度の出力サイズを組み合わせて適用します。", "resolution implementation explanation removed")
reject(ui, 'SectionTitle("共通")', "redundant common heading removed")

shortcut = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/AppMenuShortcut.kt"
require(shortcut, "IconButton(", "menu icon retained")
reject(shortcut, "modifier = Modifier.fillMaxWidth(),", "menu no longer consumes standalone full-width row")

menu = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/AppMenuActivity.kt"
require(menu, "if (BuildConfig.DEBUG_FEATURES) {\n            LiveModeBillingManager.initialize(this)", "menu billing init debug-only")
require(menu, "if (BuildConfig.DEBUG_FEATURES) {\n        MenuEntry(\n            title = stringResource(R.string.menu_diagnostics_title)", "diagnostics menu debug-only")
require(menu, "if (BuildConfig.DEBUG_FEATURES) {\n        HorizontalDivider()\n        MaterialText(\n            text = stringResource(R.string.live_mode_title)", "subscription menu debug-only")
require(menu, "R.string.menu_description_v041", "release menu copy")
require(menu, "R.string.menu_libraries_description_v041", "release libraries copy")
require(menu, "R.string.menu_privacy_description_v041", "release privacy copy")

main = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java"
require(main, "if (BuildConfig.DEBUG_FEATURES) {\n            LiveModeBillingManager.initialize(this);", "main billing init debug-only")
require(main, "if (!BuildConfig.DEBUG_FEATURES) {", "defensive live start gate")
require(main, "if (BuildConfig.DEBUG_FEATURES) {\n            LiveModeBillingManager.refreshEntitlement();", "main billing refresh debug-only")

for values_dir in ("values", "values-ja", "values-zh-rCN", "values-ko"):
    strings = f"app/src/main/res/{values_dir}/strings_release_v041.xml"
    require(strings, 'name="phone_ratio_text_recommended_v041"', f"{values_dir} concise 20 percent copy")
    require(strings, 'name="readable_text_description_v041"', f"{values_dir} concise text copy")
    require(strings, 'name="menu_description_v041"', f"{values_dir} release menu copy")
    require(strings, 'name="menu_libraries_description_v041"', f"{values_dir} release libraries copy")
    require(strings, 'name="menu_privacy_description_v041"', f"{values_dir} release privacy copy")

workflow = ".github/workflows/build-apk.yml"
require(workflow, "python3 tools/verify_release_debug_v041.py", "v041 release/debug gate in CI")
require(workflow, "-PGBMODER_DEBUG_FEATURES=true", "CI builds debug-feature APK explicitly")

print("RELEASE UI + DEBUG FEATURES v0.1.41 AUTOMATED GATE: PASS")
