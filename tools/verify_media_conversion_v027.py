#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
compose = (root / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt").read_text()
activity = (root / "app/src/main/java/com/sktpj/gbmoder/MediaConversionActivity.java").read_text()
converter = (root / "app/src/main/java/com/sktpj/gbmoder/MediaFileConverter.java").read_text()
manifest = (root / "app/src/main/AndroidManifest.xml").read_text()
version = (root / "version.properties").read_text()


def need(text: str, value: str, label: str) -> None:
    if value not in text:
        raise SystemExit(f"FAIL {label}: {value}")
    print(f"PASS {label}")


need(version, "VERSION_NAME=0.1.27", "version name")
need(version, "VERSION_CODE=28", "version code")
need(manifest, 'android:name=".MediaConversionActivity"', "conversion activity registered")
need(compose, 'testTag("media-conversion-card")', "conversion card")
need(compose, 'testTag("convert-photo")', "photo action")
need(compose, 'testTag("convert-video")', "video action")
need(compose, 'testTag("convert-model")', "model action")
need(compose, "MediaConversionActivity.KIND_PHOTO", "photo route")
need(compose, "MediaConversionActivity.KIND_VIDEO", "video route")
need(compose, "MediaConversionActivity.KIND_MODEL", "model route")
need(activity, "Intent.ACTION_OPEN_DOCUMENT", "source picker")
need(activity, "Intent.ACTION_CREATE_DOCUMENT", "output picker")
need(activity, "MediaFileConverter.convertPhoto", "photo conversion dispatch")
need(activity, "MediaFileConverter.convertVideo", "video conversion dispatch")
need(activity, "MediaFileConverter.convertModel", "model conversion dispatch")
need(converter, "GameBoyFilter.apply", "shared filter processing")
need(converter, "MediaCodec.createEncoderByType", "video encoding")
need(converter, "MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4", "mp4 output")
need(converter, '"ply".equals(ext)', "ply model support")
need(converter, '"obj".equals(ext)', "obj model support")
need(converter, '"gltf".equals(ext)', "gltf model support")
need(converter, '"glb".equals(ext)', "glb model support")

primary = compose.find('testTag("primary-action")')
media = compose.find('testTag("media-conversion-card")')
diagnostics = compose.find('DiagnosticsCard(')
if primary < 0 or media < 0 or diagnostics < 0 or not (primary < media < diagnostics):
    raise SystemExit("FAIL file conversion must follow the primary filter action and precede diagnostics")
print("PASS conversion placement")

print("MEDIA CONVERSION v0.1.27 AUTOMATED GATE: PASS")
