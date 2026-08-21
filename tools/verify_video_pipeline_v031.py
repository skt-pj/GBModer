#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = (root / "version.properties").read_text()
manifest = (root / "app/src/main/AndroidManifest.xml").read_text()
activity = (root / "app/src/main/kotlin/com/sktpj/gbmoder/VideoDiagnosticsActivity.kt").read_text()
diagnostics = (root / "app/src/main/java/com/sktpj/gbmoder/VideoPipelineDiagnostics.java").read_text()
encoder_diag = (root / "app/src/main/java/com/sktpj/gbmoder/VideoEncoderDiagnostics.java").read_text()
localization = (root / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerLocalization.kt").read_text()
generated_main = (root / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java").read_text()
generated_converter = (root / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MediaFileConverter.java").read_text()


def need(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r}")
    print(f"PASS {label}")


need(version, "VERSION_NAME=0.1.34", "version name")
need(version, "VERSION_CODE=35", "version code")
need(manifest, 'android:name=".VideoDiagnosticsActivity"', "diagnostics activity registered")
need(activity, 'testTag("video-diagnostics-screen")', "diagnostics screen")
need(activity, 'testTag("diagnostics-top-quiet-zone")', "Pixel-safe diagnostics top quiet zone")
need(activity, "WindowInsets.safeDrawing", "diagnostics safe drawing insets")
need(activity, "ActivityResultContracts.OpenDocument", "diagnostic video picker")
need(activity, 'testTag("diagnostic-result")', "diagnostic comparison result")
need(activity, "PerformanceLog.syncToUri", "performance log export retained")
need(activity, "VideoEncoderDiagnostics.measure", "H264 encoder benchmark shown in diagnostics")
need(activity, "diag_encode_ms", "encoder timing line")

need(diagnostics, "MediaExtractor", "source PTS inspection")
need(diagnostics, "getScaledFrameAtTime", "target-size-first benchmark")
need(diagnostics, "COLOR_FormatSurface", "encoder Surface capability check")
need(diagnostics, "isHardwareAccelerated", "hardware codec check")
need(diagnostics, "ptsJitterPercent", "VFR timing diagnostics")
need(diagnostics, "fullFilterMs", "CPU filter timing")
need(diagnostics, "fullYuvMs", "CPU YUV timing")
need(encoder_diag, "MediaCodec.createEncoderByType", "actual encoder microbenchmark")
need(encoder_diag, "MEASURE_FRAMES", "multi-frame encoder benchmark")

need(localization, '"ログ同期" to R.string.video_diagnostics_action', "main diagnostics button relabeled")
need(generated_main, "new Intent(MainActivity.this, VideoDiagnosticsActivity.class)", "main diagnostics route")
need(generated_main, "MediaConversionActivity.EXTRA_RESOLUTION", "diagnostics uses current resolution")

need(generated_converter, "MediaExtractor timingExtractor", "source timing extractor retained for CPU fallback")
need(generated_converter, "timingExtractor.getSampleTime()", "source PTS CPU fallback")
need(generated_converter, "retriever.getScaledFrameAtTime", "target-size-first CPU fallback")
need(generated_converter, "presentationTimeUs", "source presentation timestamp queueing")
need(generated_converter, "source_pts=true", "conversion timing evidence")
if "frameIndex * frameDurationUs" in generated_converter:
    raise SystemExit("FAIL video timing: fixed interval frame generation remains")
print("PASS fixed-interval video frame generation removed")

for path in (
    "app/src/main/res/values/strings_video_diagnostics.xml",
    "app/src/main/res/values-ja/strings_video_diagnostics.xml",
    "app/src/main/res/values-zh-rCN/strings_video_diagnostics.xml",
    "app/src/main/res/values-ko/strings_video_diagnostics.xml",
):
    text = (root / path).read_text()
    need(text, 'name="video_diagnostics_action"', f"diagnostics action localized: {path}")
    need(text, 'name="diag_pipeline_comparison"', f"diagnostics comparison localized: {path}")
for path in (
    "app/src/main/res/values/strings_video_encoder_diagnostics.xml",
    "app/src/main/res/values-ja/strings_video_encoder_diagnostics.xml",
    "app/src/main/res/values-zh-rCN/strings_video_encoder_diagnostics.xml",
    "app/src/main/res/values-ko/strings_video_encoder_diagnostics.xml",
):
    text = (root / path).read_text()
    need(text, 'name="diag_encode_ms"', f"encoder timing localized: {path}")

print("VIDEO PIPELINE DIAGNOSTICS v0.1.34 AUTOMATED GATE: PASS")
