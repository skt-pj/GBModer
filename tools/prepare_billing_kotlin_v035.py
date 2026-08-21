#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: prepare_billing_kotlin_v035.py <source_kotlin_root> <generated_kotlin_root>")

source_root = Path(sys.argv[1]).resolve()
generated_root = Path(sys.argv[2]).resolve()

if generated_root.exists():
    shutil.rmtree(generated_root)
shutil.copytree(source_root, generated_root)

ui_path = generated_root / "com/sktpj/gbmoder/GbModerComposeUi.kt"
ui_text = ui_path.read_text()


def replace_ui_once(old: str, new: str, label: str) -> None:
    global ui_text
    count = ui_text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    ui_text = ui_text.replace(old, new, 1)


replace_ui_once(
    '        HorizontalDivider()\n        SectionTitle("フィルター")\n\n        Button(\n',
    '        HorizontalDivider()\n        SectionTitle("フィルター")\n\n        LiveModeSubscriptionCard()\n\n        Button(\n',
    "live subscription card",
)

replace_ui_once(
    'contentDescription = if (state.running) "フィルターを停止" else "フィルターを開始"',
    'contentDescription = if (state.running) "フィルターを停止" else "ライブモードを開始"',
    "live start accessibility label",
)

replace_ui_once(
    'Text(if (state.running) "停止" else "フィルター開始")',
    'Text(if (state.running) "停止" else "ライブモード開始")',
    "live start button label",
)

ui_path.write_text(ui_text)
print("v0.1.35 billing Kotlin UI prepared")
