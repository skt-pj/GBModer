#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_text_defaults_v045.py <generated_kotlin_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"
ui = root / "GbModerComposeUi.kt"
text = ui.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    "private const val DEFAULT_RESOLUTION_POSITION = 0",
    "private const val DEFAULT_RESOLUTION_POSITION = 9",
    "30 percent default resolution",
)

replace_once(
    '''        for (percent in 5..95 step 5) {
            if (percent == 20) {
                add("端末比 / 20%（テキスト推奨）")
            } else {
                add("端末比 / ${percent}%")
            }
        }
''',
    '''        for (percent in 5..95 step 5) {
            if (percent == 30) {
                add("端末比 / 30%（テキスト推奨）")
            } else {
                add("端末比 / ${percent}%")
            }
        }
''',
    "30 percent text recommendation label",
)

replace_once(
    "    var textRecognitionEnabled by rememberSaveable { mutableStateOf(false) }\n",
    "",
    "remove readable text state",
)

replace_once(
    '''        if (BuildConfig.DEBUG_FEATURES) {
            ToggleSettingRow(
                title = "文字を読みやすくする",
                description = "文字表示には端末比 / 20%を推奨します。",
                checked = textRecognitionEnabled,
                onCheckedChange = { textRecognitionEnabled = it },
                contentDescription = "文字を読みやすくする",
                tag = "text-recognition-row",
            )
        }
''',
    "",
    "remove readable text toggle",
)

replace_once(
    "                        textRecognitionEnabled,\n",
    "                        true,\n",
    "always enable text recognition",
)

ui.write_text(text)

localization = root / "GbModerLocalization.kt"
localization_text = localization.read_text()


def replace_localization_once(old: str, new: str, label: str) -> None:
    global localization_text
    count = localization_text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    localization_text = localization_text.replace(old, new, 1)


replace_localization_once(
    '        "端末比 / 20%（テキスト推奨）" to R.string.phone_ratio_text_recommended_v041,',
    '        "端末比 / 30%（テキスト推奨）" to R.string.phone_ratio_text_recommended_v041,',
    "30 percent recommendation localization",
)
replace_localization_once(
    '        "文字表示には端末比 / 20%を推奨します。" to R.string.readable_text_description_v041,',
    '        "文字表示には端末比 / 30%を推奨します。" to R.string.readable_text_description_v041,',
    "30 percent text copy localization",
)
localization.write_text(localization_text)

print("v0.1.45 readable-text toggle removed; text recognition always enabled; 30% recommended/default")
