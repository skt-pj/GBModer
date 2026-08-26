#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (
    root
    / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java"
).read_text()
compose = (
    root
    / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt"
).read_text()


def need(text: str, value: str, label: str) -> None:
    if value not in text:
        raise SystemExit(f"FAIL {label}: {value}")
    print(f"PASS {label}")


need(main, "setContentView(composeView);", "single Compose root")
if "LinearLayout routeRoot = new LinearLayout(this);" in main:
    raise SystemExit("FAIL external route UI still exists")
print("PASS external route UI removed")
if "routeControls.post(routeControls::requestApplyInsets);" in main:
    raise SystemExit("FAIL external route inset layer still exists")
print("PASS external route inset layer removed")

need(main, "int captureRoutePosition,", "route value passed from Compose")
need(main, "boolean textRecognitionEnabled", "text recognition value passed from Compose")
need(main, "uiCaptureRoutePosition = captureRoutePosition;", "route state applied at start")
need(main, "uiTextRecognitionEnabled = false;", "text recognition hard-disabled at start")

if compose.count(".verticalScroll(rememberScrollState())") != 1:
    raise SystemExit("FAIL settings must have exactly one vertical scroll container")
print("PASS one settings scroll container")

if 'title = "文字を読みやすくする"' in compose or 'tag = "text-recognition-row"' in compose:
    raise SystemExit("FAIL readable-text control remains in source UI")
print("PASS readable-text control removed from source UI")
need(compose, 'Text("詳細設定・診断"', "advanced section")
need(compose, 'Text("画面取得方式"', "capture route inside advanced section")
need(compose, 'testTag("capture-route-selector")', "capture route selector test tag")
need(compose, '"標準（推奨）"', "recommended route wording")
need(compose, '"互換モード（Android 14+）"', "compatibility route wording")

primary = compose.find('testTag("primary-action")')
diagnostics = compose.find('DiagnosticsCard(')
if primary < 0 or diagnostics < 0 or primary > diagnostics:
    raise SystemExit("FAIL primary action must precede advanced diagnostics")
print("PASS primary action before advanced diagnostics")

if "処理ルート" in compose:
    raise SystemExit("FAIL implementation-centric route label exposed in normal UI")
print("PASS implementation-centric top label removed")

print("UIUX v0.1.47 AUTOMATED GATE: PASS")
