#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (repo / path).read_text()


def require(path: str, needle: str, label: str) -> None:
    text = read(path)
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r} in {path}")
    print(f"PASS {label}")


def reject(path: str, needle: str, label: str) -> None:
    text = read(path)
    if needle in text:
        raise SystemExit(f"FAIL {label}: unexpected {needle!r} in {path}")
    print(f"PASS {label}")


require("version.properties", "VERSION_NAME=0.1.48", "version name")
require("version.properties", "VERSION_CODE=49", "version code")
require("tools/prepare_billing_release_v041.py", "finish_ui_restore_v046.py", "v046 Kotlin finalizer registered")
require("tools/prepare_billing_release_v041.py", "finish_mode_backdrop_v047.py", "v047 mode backdrop finalizer registered")
require("tools/prepare_billing_release_v041.py", "finish_mode_shell_v048.py", "v048 full mode shell finalizer registered")
require("tools/prepare_all_sources_v020.py", "finish_text_disabled_v046.py", "v046 Java finalizer registered")
require("app/build.gradle", "finish_ui_restore_v046.py", "v046 Kotlin finalizer tracked")
require("app/build.gradle", "finish_mode_backdrop_v047.py", "v047 mode backdrop finalizer tracked")
require("app/build.gradle", "finish_mode_shell_v048.py", "v048 full mode shell finalizer tracked")
require("app/build.gradle", "finish_text_disabled_v046.py", "v046 Java finalizer tracked")

ui = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt"
require(ui, "private const val DEFAULT_RESOLUTION_POSITION = 9", "default resolution remains device ratio 30 percent")
require(ui, 'add("端末比 / 30%（テキスト推奨）")', "30 percent recommendation retained")
require(ui, "captureRoutePosition,\n                        false,", "Compose always passes text recognition OFF")
reject(ui, "captureRoutePosition,\n                        true,", "Compose no longer forces text recognition ON")
reject(ui, 'tag = "text-recognition-row"', "readable-text toggle removed")
reject(ui, 'title = "文字を読みやすくする"', "readable-text title removed")

require(ui, "androidx.compose.material3.lightColorScheme(", "stable light Game Boy theme")
require(ui, "background = Color(0xFFE2E6D6)", "non-black Game Boy base background")
require(ui, "surface = Color(0xFFF2F4E8)", "light Game Boy surface")
reject(ui, "dynamicDarkColorScheme(activity)", "dynamic black theme disabled")

require(ui, "ModeBackdrop(modePosition)", "mode identity panel is rendered on compact settings screen")
require(ui, 'testTag("mode-backdrop")', "mode identity panel test tag")
for label in ('shortLabel = "GB"', 'shortLabel = "GBC"', 'shortLabel = "GBA"', 'shortLabel = "DS"'):
    require(ui, label, f"mode backdrop {label}")
require(ui, 'text = "GB  /  GBC  /  GBA  /  DS"', "all mode labels shown in backdrop")
require(ui, 'longLabel = "GAME BOY"', "Game Boy backdrop label")
require(ui, 'longLabel = "GAME BOY COLOR"', "Game Boy Color backdrop label")
require(ui, 'longLabel = "GAME BOY ADVANCE"', "Game Boy Advance backdrop label")
require(ui, 'longLabel = "NINTENDO DS"', "Nintendo DS backdrop label")

require(ui, "val modeShellColor = when (modePosition)", "selected mode drives full settings background")
require(ui, "1 -> Color(0xFFD8D3F0) // GBC shell", "GBC full background")
require(ui, "2 -> Color(0xFFD2D9EC) // GBA shell", "GBA full background")
require(ui, "3 -> Color(0xFFD7D9D7) // DS shell", "DS full background")
require(ui, "else -> Color(0xFFB7C48D) // GB shell", "GB full background")
require(ui, ".background(modeShellColor)", "full settings pane paints selected console shell")
require(ui, 'testTag("mode-shell-background")', "mode shell background test tag")

require(ui, 'SectionTitle("2048TD")', "2048TD section on main screen")
require(ui, 'testTag("main-2048td")', "2048TD main-screen action")
require(ui, '"com.sktpj.gbmoder.Game2048ContentActivity"', "2048TD main-screen route")
ui_text = read(ui)
live_index = ui_text.find("SectionTitle(androidx.compose.ui.res.stringResource(R.string.live_mode_title))")
conversion_index = ui_text.find('SectionTitle("変換")')
game_index = ui_text.find('SectionTitle("2048TD")')
if not (0 <= live_index < conversion_index < game_index):
    raise SystemExit(
        f"FAIL main section order: live={live_index} conversion={conversion_index} 2048={game_index}"
    )
print("PASS main section order is live -> conversion -> 2048TD")

menu = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/AppMenuActivity.kt"
reject(menu, 'tag = "menu-2048td"', "2048TD removed from overflow menu")
require(menu, 'tag = "menu-diagnostics"', "diagnostics menu item retained")

main = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java"
require(main, "uiTextRecognitionEnabled = false;", "Java ignores attempts to enable text recognition")
require(main, "private boolean isUiTextRecognitionEnabled() {\n        return false;\n    }", "live routes hard-disable text recognition")
require(main, "private int uiResolutionPosition = 9;", "live default remains device ratio 30 percent")

accessibility = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/FilterAccessibilityService.java"
require(accessibility, "&& !windowTextRecognitionEnabled", "GPU route is available when text recognition is off")

workflow = ".github/workflows/build-apk.yml"
require(workflow, "python3 tools/verify_ui_restore_v046.py", "UI restore gate in CI")

print("UI RESTORE + FULL MODE SHELL + TEXT DISABLED v0.1.48 AUTOMATED GATE: PASS")
