#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
compose = (root / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt").read_text()
media = (root / "app/src/main/kotlin/com/sktpj/gbmoder/MediaConversionActivity.kt").read_text()
unified = (root / "app/src/main/kotlin/com/sktpj/gbmoder/UnifiedConversionControls.kt").read_text()


def need(text: str, value: str, label: str) -> None:
    if value not in text:
        raise SystemExit(f"FAIL {label}: missing {value}")
    print(f"PASS {label}")


need(compose, "WindowInsets.safeDrawing", "main safe drawing insets")
need(compose, 'testTag("top-quiet-zone")', "main top quiet zone")
if "TopAppBar(" in compose or 'Text("GBModer"' in compose:
    raise SystemExit("FAIL main screen still places app text in the top app-bar area")
print("PASS main top app-bar text removed")

settings = compose.find("private fun SettingsPane(")
quiet = compose.find('testTag("top-quiet-zone")', settings)
first_setup = compose.find("FirstSetupCard(actions)", settings)
common = compose.find('SectionTitle("共通")', settings)
mode = compose.find('SectionTitle("表示モード")', common)
if min(settings, quiet, first_setup, common, mode) < 0 or not (quiet < first_setup < common < mode):
    raise SystemExit("FAIL top quiet zone/common settings ordering changed")
print("PASS quiet zone precedes unchanged common settings")

need(unified, "FilledTonalButton", "Material 3 source action")
need(unified, "OutlinedButton", "Material 3 output action")
need(unified, "Button(", "Material 3 conversion primary action")
need(unified, "ButtonDefaults.IconSize", "Material 3 icon sizing")
need(unified, "ButtonDefaults.IconSpacing", "Material 3 icon spacing")
need(unified, '.heightIn(min = 52.dp)', "large source/output touch targets")
need(unified, '.heightIn(min = 56.dp)', "large conversion touch target")
need(unified, 'testTag("conversion-source-select")', "source selection action")
need(unified, 'testTag("conversion-output-select")', "output destination action")
need(unified, 'testTag("conversion-run")', "explicit conversion action")

need(media, "Scaffold(", "compatibility conversion Material 3 scaffold")
need(media, "WindowInsets.safeDrawing", "conversion safe drawing insets")
need(media, 'testTag("media-top-quiet-zone")', "conversion top quiet zone")
if "TopAppBar(" in media:
    raise SystemExit("FAIL conversion screen must not add top app-bar text")
print("PASS conversion top app bar absent")

for obsolete in ("OutlinedCard", "TextButton(", 'testTag("choose-output-and-convert")'):
    if obsolete in media:
        raise SystemExit(f"FAIL obsolete multi-step conversion chrome remains: {obsolete}")
print("PASS compatibility conversion screen delegates to the same minimal controls")

print("UIUX v0.1.34 AUTOMATED GATE: PASS")
