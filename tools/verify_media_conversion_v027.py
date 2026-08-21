#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
compose = (root / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt").read_text()
activity = (root / "app/src/main/kotlin/com/sktpj/gbmoder/MediaConversionActivity.kt").read_text()
converter = (root / "app/src/main/java/com/sktpj/gbmoder/MediaFileConverter.java").read_text()
manifest = (root / "app/src/main/AndroidManifest.xml").read_text()
version = (root / "version.properties").read_text()


def need(text: str, value: str, label: str) -> None:
    if value not in text:
        raise SystemExit(f"FAIL {label}: {value}")
    print(f"PASS {label}")


need(version, "VERSION_NAME=0.1.30", "version name")
need(version, "VERSION_CODE=31", "version code")
need(manifest, 'android:name=".MediaConversionActivity"', "conversion activity registered")
need(compose, 'testTag("media-conversion-card")', "conversion card")
need(compose, 'tag = "convert-photo"', "photo action")
need(compose, 'tag = "convert-video"', "video action")
need(compose, 'tag = "convert-model"', "model action")
need(compose, "FilledTonalButton", "Material 3 tonal conversion actions")
need(compose, "iconRes = R.drawable.ic_photo_24", "photo icon")
need(compose, "iconRes = R.drawable.ic_video_24", "video icon")
need(compose, "iconRes = R.drawable.ic_3d_model_24", "model icon")
need(compose, "painterResource(iconRes)", "shared icon renderer")
need(compose, "MediaConversionActivity.KIND_PHOTO", "photo route")
need(compose, "MediaConversionActivity.KIND_VIDEO", "video route")
need(compose, "MediaConversionActivity.KIND_MODEL", "model route")
need(compose, "resolutionValueForPosition(resolutionPosition)", "media route shares current resolution mapping")
need(activity, "ComponentActivity", "conversion Compose host")
need(activity, "enableEdgeToEdge()", "edge-to-edge setup")
need(activity, "rememberLauncherForActivityResult", "Activity Result API")
need(activity, "ActivityResultContracts.OpenDocument", "source document contract")
need(activity, "Intent.ACTION_CREATE_DOCUMENT", "output document flow")
need(activity, 'testTag("media-top-quiet-zone")', "conversion top quiet zone")
need(activity, "FilledTonalButton", "source secondary action")
need(activity, 'testTag("choose-output-and-convert")', "conversion primary action")
need(activity, "LinearProgressIndicator", "Material 3 progress")
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

for legacy in ("LinearLayout", "android.widget.Button", "TextView", "ProgressBar"):
    if legacy in activity:
        raise SystemExit(f"FAIL legacy conversion UI remains: {legacy}")
print("PASS legacy View conversion UI removed")

primary = compose.find('testTag("primary-action")')
media = compose.find('MediaConversionCard(', primary)
diagnostics = compose.find('DiagnosticsCard(', media)
if primary < 0 or media < 0 or diagnostics < 0 or not (primary < media < diagnostics):
    raise SystemExit("FAIL file conversion must follow the primary filter action and precede diagnostics")
print("PASS conversion placement")

print("MEDIA CONVERSION v0.1.30 AUTOMATED GATE: PASS")
