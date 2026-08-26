#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


version_text = (repo / "version.properties").read_text()
require("VERSION_NAME=0.1.47" in version_text, "v0.1.47 versionName missing")
require("VERSION_CODE=48" in version_text, "versionCode 48 missing")

build_text = (repo / "app/build.gradle").read_text()
require("prepare2048Content" in build_text, "2048TD prepare task missing")
require("generated2048SourceDir" in build_text, "2048TD generated source directory missing")
require("finish_2048_fit_v044.py" in build_text, "2048TD contain-fit patch input missing")
require("finish_ui_restore_v046.py" in build_text, "2048TD main-screen placement patch missing")
require(
    "2fa62d4b636e3e403466256dc452bf72fe6fda42" in build_text,
    "2048TD pinned commit missing from Gradle inputs",
)

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
require("stopWindowFilter" in activity_text, "embedded filter is not stopped on exit")

ui_path = repo / "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt"
require(ui_path.exists(), "generated main UI is missing")
ui_text = ui_path.read_text()
require('testTag("main-2048td")' in ui_text, "2048TD main-screen action missing")
require('SectionTitle("2048TD")' in ui_text, "2048TD main-screen section missing")
require("BuildConfig.DEBUG_FEATURES" in ui_text, "2048TD main-screen action is not debug-gated")
require('"com.sktpj.gbmoder.Game2048ContentActivity"' in ui_text, "2048TD main-screen route missing")

menu_path = repo / "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/AppMenuActivity.kt"
require(menu_path.exists(), "generated app menu is missing")
menu_text = menu_path.read_text()
require('tag = "menu-2048td"' not in menu_text, "2048TD must not remain in overflow menu")

filter_path = repo / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/FilterAccessibilityService.java"
require(filter_path.exists(), "generated accessibility filter source is missing")
filter_text = filter_path.read_text()
require("startEmbeddedContentFilter" in filter_text, "embedded content filter method missing")
require("allowOwnPackageWindow" in filter_text, "own-package filter gate missing")
require("embeddedContentFit" in filter_text, "embedded contain-fit state missing")
require("layout=contain" in filter_text, "embedded contain-fit startup marker missing")
require("getContainFitBounds" in filter_text, "CPU contain-fit path missing")
require("service.embeddedContentFit" in filter_text, "GPU contain-fit flag missing")
require("FLAG_NOT_TOUCHABLE" in filter_text, "filter overlay must remain touch-through")

gpu_path = repo / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/GpuFilterRenderer.java"
require(gpu_path.exists(), "generated GPU renderer is missing")
gpu_text = gpu_path.read_text()
require("boolean fitSource" in gpu_text, "GPU contain-fit parameter missing")
require("if (fitSource)" in gpu_text, "GPU contain-fit branch missing")
require("getContainFitBounds" in gpu_text, "GPU contain-fit geometry missing")

filter_core_path = repo / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/GameBoyFilter.java"
require(filter_core_path.exists(), "generated GameBoyFilter is missing")
filter_core_text = filter_core_path.read_text()
require("getContainFitBounds" in filter_core_text, "contain-fit geometry helper missing")

game_screen_path = repo / "app/build/generated/gbmoder2048/kotlin/com/sktpj/td2048/GameScreen.kt"
require(game_screen_path.exists(), "generated 2048TD GameScreen is missing")
game_screen_text = game_screen_path.read_text()
require("BackHandler(enabled = false)" in game_screen_text, "embedded 2048TD must allow system back")
require(
    not (repo / "app/build/generated/gbmoder2048/kotlin/com/sktpj/td2048/MainActivity.kt").exists(),
    "standalone 2048TD MainActivity must not be embedded",
)

print("v0.1.47 2048TD contain-fit + main placement gate PASS")
