#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
compose = (root / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt").read_text()
unified = (root / "app/src/main/kotlin/com/sktpj/gbmoder/UnifiedConversionControls.kt").read_text()
activity = (root / "app/src/main/kotlin/com/sktpj/gbmoder/MediaConversionActivity.kt").read_text()


def need(text, needle, label):
    if needle not in text:
        raise SystemExit(f"FAIL {label}: {needle}")
    print(f"PASS {label}")


need(compose, 'SectionTitle("共通")', "common section")
need(compose, 'SectionTitle("フィルター")', "filter section")
need(compose, 'SectionTitle("変換")', "conversion section")
need(compose, "UnifiedConversionControls(", "conversion controls on main screen")

for tag in ("conversion-source-select", "conversion-output-select", "conversion-run"):
    need(unified, f'testTag("{tag}")', tag)

for removed in ("convert-photo", "convert-video", "convert-model"):
    if removed in compose or removed in unified:
        raise SystemExit(f"FAIL media-specific action remains: {removed}")
print("PASS media-specific action split removed")

need(unified, "detectConversionSource", "automatic file detection")
need(unified, "contentResolver.getType(uri)", "MIME detection")
need(unified, 'setOf("ply", "obj", "gltf", "glb")', "model extension detection")
need(unified, "Intent.ACTION_CREATE_DOCUMENT", "output picker")
need(unified, "MediaFileConverter.convertPhoto", "photo internal dispatch")
need(unified, "MediaFileConverter.convertVideo", "video internal dispatch")
need(unified, "MediaFileConverter.convertModel", "model internal dispatch")
need(activity, "UnifiedConversionControls(", "compatibility activity uses shared controls")

source_pos = unified.find('testTag("conversion-source-select")')
output_pos = unified.find('testTag("conversion-output-select")')
run_pos = unified.find('testTag("conversion-run")')
if not (source_pos < output_pos < run_pos):
    raise SystemExit("FAIL action order")
print("PASS source -> output -> convert order")

print("UNIFIED CONVERSION UI v0.1.34 FEATURE GATE: PASS")
