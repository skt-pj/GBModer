#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
compose = (root / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt").read_text()
media = (root / "app/src/main/kotlin/com/sktpj/gbmoder/MediaConversionActivity.kt").read_text()


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
mode = compose.find('SectionTitle("表示モード")', settings)
if settings < 0 or quiet < 0 or first_setup < 0 or mode < 0 or not (quiet < first_setup < mode):
    raise SystemExit("FAIL top quiet zone must precede settings text/content")
print("PASS quiet zone precedes settings content")

need(compose, "FilledTonalButton", "Material 3 secondary conversion buttons")
need(compose, "ButtonDefaults.IconSize", "Material 3 icon sizing")
need(compose, "ButtonDefaults.IconSpacing", "Material 3 icon spacing")
for tag in ("convert-photo", "convert-video", "convert-model"):
    need(compose, f'tag = "{tag}"', f"conversion action {tag}")

need(media, "Scaffold(", "conversion Material 3 scaffold")
need(media, "WindowInsets.safeDrawing", "conversion safe drawing insets")
need(media, 'testTag("media-top-quiet-zone")', "conversion top quiet zone")
if "TopAppBar(" in media:
    raise SystemExit("FAIL conversion screen must not add top app-bar text")
print("PASS conversion top app bar absent")
need(media, "OutlinedCard", "source file grouping")
need(media, "FilledTonalButton", "source secondary action")
need(media, "Button(", "conversion primary action")
need(media, "TextButton(", "low-emphasis close action")
need(media, ".heightIn(min = 52.dp)", "large source touch target")
need(media, ".heightIn(min = 56.dp)", "large primary touch target")
need(media, ".heightIn(min = 48.dp)", "minimum close touch target")
need(media, "ActivityResultContracts.OpenDocument", "typed source picker")

print("UIUX v0.1.28 AUTOMATED GATE: PASS")
