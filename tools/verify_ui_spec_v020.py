#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r}")
    print(f"PASS {label}")


root_build = (ROOT / "build.gradle").read_text()
app_build = (ROOT / "app/build.gradle").read_text()
workflow = (ROOT / ".github/workflows/build-apk.yml").read_text()
ui = (ROOT / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt").read_text()
generated_ui = (ROOT / "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt").read_text()
filter_source = (ROOT / "app/src/main/java/com/sktpj/gbmoder/GameBoyFilter.java").read_text()
generated = (ROOT / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java").read_text()

# Toolchain / current stable stack
require(root_build, "com.android.application' version '9.3.0'", "BUILD-002 AGP 9.3.0")
require(root_build, "org.jetbrains.kotlin.plugin.compose' version '2.3.21'", "BUILD-008 Compose compiler 2.3.21")
require(app_build, "compileSdk 37", "BUILD-001 compileSdk 37")
require(app_build, "compose-bom:2026.08.00", "BUILD-004 Compose BOM 2026.08.00")
require(app_build, "androidx.compose.material3:material3", "BUILD-005 Material 3")
require(app_build, "androidx.activity:activity-compose:1.13.0", "BUILD-006 Activity Compose 1.13.0")
require(app_build, "androidx.compose.material3.adaptive:adaptive:1.3.0", "BUILD-007 Adaptive 1.3.0")
require(workflow, "gradle-version: '9.5.0'", "BUILD-003 Gradle 9.5.0")
require(workflow, 'platforms;android-37.0', "BUILD-001 CI API 37.0")

# Current UI requirements
require(ui, "Scaffold(", "UI-002 Scaffold")
require(ui, ".verticalScroll(rememberScrollState())", "UI-003 scrollable settings")
require(ui, "WindowInsets.safeDrawing", "UI-004 safe drawing insets")
if "TopAppBar(" in ui or 'Text("GBModer"' in ui:
    raise SystemExit("FAIL UI-006: top app bar/title must not occupy the Pixel top area")
print("PASS UI-006 no top app bar/title")
if 'testTag("top-quiet-zone")' in generated_ui:
    raise SystemExit("FAIL UI-007: compiled UI must not reserve a standalone top quiet-zone row")
print("PASS UI-007 compact compiled top area")
require(generated_ui, 'SectionTitle("表示モード", modifier = Modifier.weight(1f))', "UI-008 menu shares first settings row")
require(ui, "SingleChoiceSegmentedButtonRow", "UI-010 segmented modes")
for mode in ('"GB"', '"GBC"', '"GBA"', '"DS"'):
    require(ui, mode, f"UI-010 mode {mode}")
for resolution in (
    "GB / 160×144",
    "GBC / 160×144",
    "GBA / 240×160",
    "DS / 256×192",
):
    require(ui, resolution, f"UI-012 resolution {resolution}")
require(generated_ui, "DEFAULT_RESOLUTION_POSITION = 0", "UI-012 compiled default resolution is GB")
require(generated_ui, '端末比 / 20%（テキスト推奨）', "UI-012 20 percent text recommendation")
require(ui, "for (percent in 5..95 step 5)", "UI-012 phone resolution increments by 5 percent")
require(ui, 'add("端末比 / ${percent}%")', "UI-012 generated phone percentage labels")
require(ui, 'add("スマホの元解像度 / 100%")', "UI-012 native 100 percent label")
require(ui, "GameBoyFilter.phoneResolution((resolutionPosition - 3) * 5)", "UI-012 media conversion uses shared percentage mapping")
require(filter_source, 'RESOLUTION_PHONE_20 = "phone_20"', "UI-012 filter 20 percent resolution")
require(filter_source, "percent >= 5 && percent <= 95 && percent % 5 == 0", "UI-012 filter accepts 5-percent steps")
require(generated, "private int uiResolutionPosition = 0;", "UI-012 generated live default resolution is GB")
require(generated, "position >= 4 && position <= 22", "UI-012 generated mapping covers 5 to 95 percent")
require(generated, "GameBoyFilter.phoneResolution((position - 3) * 5)", "UI-012 generated mapping uses shared percentage helper")
require(ui, 'mutableStateOf(6f)', "UI-014 brightness initial 6")
require(ui, 'mutableStateOf(122f)', "UI-016 contrast initial 122")
require(ui, 'mutableStateOf(true)', "UI-018 dither initially on")
require(ui, '"詳細設定・診断"', "UI-020 diagnostics implementation retained")
require(ui, 'if (state.running) "停止" else "フィルター開始"', "UI-022/023 live implementation retained")
require(ui, "LocalWindowInfo.current", "UI-029/030 adaptive window info")
require(ui, ">= 840.dp", "UI-030 expanded threshold")
require(ui, '"GAME BOY"', "UI-031 preview")
require(ui, '"GB (DMG) パレット"', "UI-032 DMG palette")
require(ui, "dynamicDarkColorScheme", "UI-034/035 dark dynamic theme")
require(ui, "dynamicLightColorScheme", "UI-033/035 light dynamic theme")
require(ui, ".semantics", "UI-037 accessibility semantics")

# Java/Compose bridge and existing behavior connection
require(generated, "GbModerComposeUi.createView", "UI-001 Compose host installed")
require(generated, "new GbModerUiActions()", "UI-025 Java bridge")
require(generated, "composeUiState.setStatus", "UI-026 status bridge")
require(generated, "uiModePosition = modePosition", "UI-025 mode bridge")
require(generated, "uiResolutionPosition = resolutionPosition", "UI-025 resolution bridge")
require(generated, "uiBrightness = brightness", "UI-025 brightness bridge")
require(generated, "uiContrast = contrast", "UI-025 contrast bridge")
require(generated, "uiDither = dither", "UI-025 dither bridge")
if "setContentView(buildContentView())" in generated:
    raise SystemExit("FAIL UI-001: retired LinearLayout UI is still installed")
print("PASS UI-001 retired LinearLayout not installed")

# Startup/lifecycle preconditions for ComposeView.
require(generated, "import androidx.activity.ComponentActivity;", "START-001 ComponentActivity import")
require(generated, "public class MainActivity extends ComponentActivity", "START-001 ComponentActivity base class")
if "public class MainActivity extends Activity" in generated:
    raise SystemExit("FAIL START-002: generated MainActivity still extends android.app.Activity")
print("PASS START-002 android.app.Activity base removed")

print("UI SPEC AUTOMATED GATE: PASS")
