#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_text_disabled_v046.py <generated_java_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"
main = root / "MainActivity.java"
text = main.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    "                uiTextRecognitionEnabled = textRecognitionEnabled;\n",
    "                uiTextRecognitionEnabled = false;\n",
    "ignore Compose text-recognition argument",
)
replace_once(
    '''    private boolean isUiTextRecognitionEnabled() {
        return uiTextRecognitionEnabled;
    }
''',
    '''    private boolean isUiTextRecognitionEnabled() {
        return false;
    }
''',
    "force text-recognition processing off",
)

main.write_text(text)
print("v0.1.46 text recognition processing forced OFF for live routes", flush=True)
