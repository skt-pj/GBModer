#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


version_text = (repo / "version.properties").read_text()
require("VERSION_NAME=0.1.46" in version_text, "v0.1.46 versionName missing")
require("VERSION_CODE=47" in version_text, "versionCode 47 missing")

build_text = (repo / "app/build.gradle").read_text()
require("prepare2048Content" in build_text, "2048TD prepare task missing")
require("generated2048SourceDir" in build_text, "2048TD generated source directory missing")
require("preDebugBuild" in build_text, "2048TD debug build dependency missing")
require(
    "2fa62d4b636e3e403466256dc452bf72fe6fda42" in build_text,
    "2048TD pinned commit missing from Gradle inputs",
)
require("finish_2048_main_v045.py" in build_text, "main-screen 2048TD finalizer is not tracked")

prepare_text = (repo / "tools/prepare_2048td_content_v043.py").read_text()
require(
    'UPSTREAM_COMMIT = "2fa62d4b636e3e403466256dc452bf72fe6fda42"' in prepare_text,
    "2048TD upstream commit is not pinned",
)
require('UPSTREAM_VERSION_NAME = "0.1.7"' in prepare_text, "2048TD upstream version missing")

manifest_text = (repo / "app/src/debug/AndroidManifest.xml").read_text()
require("android.permission.INTERNET" in manifest_text, "2048TD ranking INTERNET permission missing")
require(".Game2048ContentActivity" in manifest_text, "2048TD content activity missing")
require('android:screenOrientation="portrait"' in manifest_text, "2048TD portrait activity missing")

activity_text = (
    repo / "app/src/debug/kotlin/com/sktpj/gbmoder/Game2048ContentActivity.kt"
).read_text()
require("GameApp()" in activity_text, "2048TD GameApp is not hosted")
require("startEmbeddedContentFilter" in activity_text, "embedded filter is not started")
require("override fun onStop()" in activity_text, "embedded filter must stop when game leaves foreground")
require("stopEmbeddedFilter()" in activity_text, "embedded filter stop helper missing")
require("service.stopWindowFilter()" in activity_text, "embedded filter is not stopped on background")
require("service.clearOverlay()" in activity_text, "embedded overlay is not cleared on background")
require(
    activity_text.find("override fun onStop()") < activity_text.find("override fun onDestroy()"),
    "foreground lifecycle stop must not rely on destruction",
)

ui_path = repo / "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt"
require(ui_path.exists(), "generated main UI is missing")
ui_text = ui_path.read_text()
require('testTag("main-2048td-card")' in ui_text, "2048TD main-screen card missing")
require("GameContentCard(" in ui_text, "2048TD main-screen composable missing")
require("MaterialTheme.shapes.extraLarge" in ui_text, "2048TD card does not use expressive Material shape")
require("R.string.playground_description_v045" in ui_text, "2048TD supporting-content copy missing")
require("BuildConfig.DEBUG_FEATURES" in ui_text, "2048TD main-screen card is not debug-gated")
require(
    ui_text.find("GameContentCard(") < ui_text.find("SectionTitle(androidx.compose.ui.res.stringResource(R.string.live_mode_title))"),
    "2048TD card must appear before secondary live/diagnostics content",
)

menu_path = repo / "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/AppMenuActivity.kt"
require(menu_path.exists(), "generated app menu is missing")
menu_text = menu_path.read_text()
require('tag = "menu-2048td"' not in menu_text, "2048TD should no longer be duplicated in overflow menu")

filter_path = repo / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/FilterAccessibilityService.java"
require(filter_path.exists(), "generated accessibility filter source is missing")
filter_text = filter_path.read_text()
require("startEmbeddedContentFilter" in filter_text, "embedded content filter method missing")
require("allowOwnPackageWindow" in filter_text, "own-package filter gate missing")
require("FLAG_NOT_TOUCHABLE" in filter_text, "filter overlay must remain touch-through")

game_screen_path = repo / "app/build/generated/gbmoder2048/kotlin/com/sktpj/td2048/GameScreen.kt"
require(game_screen_path.exists(), "generated 2048TD GameScreen is missing")
game_screen_text = game_screen_path.read_text()
require("BackHandler(enabled = false)" in game_screen_text, "embedded 2048TD must allow system back")
require(
    not (repo / "app/build/generated/gbmoder2048/kotlin/com/sktpj/td2048/MainActivity.kt").exists(),
    "standalone 2048TD MainActivity must not be embedded",
)

for values_dir in ("values", "values-ja", "values-zh-rCN", "values-ko"):
    strings = repo / f"app/src/main/res/{values_dir}/strings_playground_v045.xml"
    require(strings.exists(), f"{values_dir} playground strings missing")
    value = strings.read_text()
    require('name="playground_label_v045"' in value, f"{values_dir} playground label missing")
    require('name="playground_description_v045"' in value, f"{values_dir} playground description missing")
    require('name="playground_action_v045"' in value, f"{values_dir} playground action missing")

print("v0.1.46 2048TD foreground lifecycle gate PASS")
