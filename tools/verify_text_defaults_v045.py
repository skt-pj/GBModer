#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def require(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r} in {path}")
    print(f"PASS {label}")


def reject(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle in text:
        raise SystemExit(f"FAIL {label}: unexpected {needle!r} in {path}")
    print(f"PASS {label}")


require("version.properties", "VERSION_NAME=0.1.45", "version name")
require("version.properties", "VERSION_CODE=46", "version code")
require("tools/prepare_billing_release_v041.py", "finish_text_defaults_v045.py", "Kotlin v045 finalizer registered")
require("tools/prepare_all_sources_v020.py", "finish_resolution_default_v045.py", "Java v045 finalizer registered")
require("app/build.gradle", "finish_text_defaults_v045.py", "Kotlin v045 finalizer tracked")
require("app/build.gradle", "finish_resolution_default_v045.py", "Java v045 finalizer tracked")

ui = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt"
require(ui, "private const val DEFAULT_RESOLUTION_POSITION = 9", "default resolution is device ratio 30 percent")
require(ui, 'add("端末比 / 30%（テキスト推奨）")', "30 percent text recommendation label")
require(ui, "captureRoutePosition,\n                        true,", "text recognition always enabled")
reject(ui, 'tag = "text-recognition-row"', "readable-text toggle removed")
reject(ui, 'title = "文字を読みやすくする"', "readable-text toggle title removed")
reject(ui, '端末比 / 20%（テキスト推奨）', "20 percent recommendation removed")

main = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java"
require(main, "private int uiResolutionPosition = 9;", "live state defaults to device ratio 30 percent")

for values_dir in ("values", "values-ja", "values-zh-rCN", "values-ko"):
    strings = f"app/src/main/res/{values_dir}/strings_release_v041.xml"
    require(strings, "30%", f"{values_dir} 30 percent recommendation copy")
    reject(strings, "20%", f"{values_dir} old 20 percent recommendation removed")

workflow = ".github/workflows/build-apk.yml"
require(workflow, "python3 tools/verify_text_defaults_v045.py", "v045 gate in CI")

print("TEXT DEFAULTS v0.1.45 AUTOMATED GATE: PASS")
