#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
compose = (root / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt").read_text()
activity = (root / "app/src/main/kotlin/com/sktpj/gbmoder/MediaConversionActivity.kt").read_text()
unified = (root / "app/src/main/kotlin/com/sktpj/gbmoder/UnifiedConversionControls.kt").read_text()
converter = (root / "app/src/main/java/com/sktpj/gbmoder/MediaFileConverter.java").read_text()
manifest = (root / "app/src/main/AndroidManifest.xml").read_text()
version = (root / "version.properties").read_text()


def need(text: str, value: str, label: str) -> None:
    if value not in text:
        raise SystemExit(f"FAIL {label}: {value}")
    print(f"PASS {label}")


need(version, "VERSION_NAME=0.1.34", "version name")
need(version, "VERSION_CODE=35", "version code")
need(manifest, 'android:name=".MediaConversionActivity"', "compatibility conversion activity registered")

# Main screen is one hierarchy: common settings, filter, then conversion.
need(compose, 'SectionTitle("共通")', "common section")
need(compose, 'SectionTitle("フィルター")', "filter section")
need(compose, 'SectionTitle("変換")', "conversion section")
need(compose, "UnifiedConversionControls(", "unified conversion controls embedded on main screen")
need(compose, "resolutionValueForPosition(resolutionPosition)", "conversion shares current resolution")
need(compose, "modeValueForPosition(modePosition)", "conversion shares current mode")

common = compose.find('SectionTitle("共通")')
filter_section = compose.find('SectionTitle("フィルター")', common)
primary = compose.find('testTag("primary-action")', filter_section)
conversion_section = compose.find('SectionTitle("変換")', primary)
unified_controls = compose.find("UnifiedConversionControls(", conversion_section)
diagnostics = compose.find("DiagnosticsCard(", unified_controls)
if min(common, filter_section, primary, conversion_section, unified_controls, diagnostics) < 0 or not (
    common < filter_section < primary < conversion_section < unified_controls < diagnostics
):
    raise SystemExit("FAIL main hierarchy must be common -> filter -> conversion -> diagnostics")
print("PASS common/filter/conversion hierarchy")

# Exactly one source picker, one destination picker and one conversion action; no media-kind buttons.
for tag in ("conversion-source-select", "conversion-output-select", "conversion-run"):
    need(unified, f'testTag("{tag}")', f"unified action {tag}")
for obsolete in (
    'testTag("convert-photo")',
    'testTag("convert-video")',
    'testTag("convert-model")',
    '"写真をPNGに変換"',
    '"動画をMP4に変換"',
    '"3Dモデルを変換"',
):
    if obsolete in compose or obsolete in unified:
        raise SystemExit(f"FAIL media-kind-specific UI remains: {obsolete}")
print("PASS photo/video/model UI split removed")

need(unified, "ActivityResultContracts.OpenDocument", "single source document picker")
need(unified, "Intent.ACTION_CREATE_DOCUMENT", "independent output destination picker")
need(unified, "detectConversionSource", "file kind is detected after selection")
need(unified, 'mime.startsWith("image/")', "image auto detection")
need(unified, 'mime.startsWith("video/")', "video auto detection")
need(unified, 'setOf("ply", "obj", "gltf", "glb")', "3D extension auto detection")
need(unified, "MediaFileConverter.convertPhoto", "photo conversion dispatch")
need(unified, "MediaFileConverter.convertVideo", "video conversion dispatch")
need(unified, "MediaFileConverter.convertModel", "model conversion dispatch")

# Compatibility activity reuses exactly the same controls instead of keeping a second kind-specific UI.
need(activity, "UnifiedConversionControls(", "compatibility screen shares unified controls")
if "when (kind)" in activity or "kindTitle(" in activity or "kindDescription(" in activity:
    raise SystemExit("FAIL compatibility activity still branches UI by media kind")
print("PASS compatibility activity has no media-kind UI branching")

need(converter, "GameBoyFilter.apply", "shared filter processing")
need(converter, "MediaCodec.createEncoderByType", "video encoding")
need(converter, "MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4", "mp4 output")
need(converter, '"ply".equals(ext)', "ply model support")
need(converter, '"obj".equals(ext)', "obj model support")
need(converter, '"gltf".equals(ext)', "gltf model support")
need(converter, '"glb".equals(ext)', "glb model support")

print("MEDIA CONVERSION v0.1.34 AUTOMATED GATE: PASS")
