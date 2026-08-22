#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_fit_resolution_ui_v047.py <generated_kotlin_root>")

root = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder"
ui_path = root / "GbModerComposeUi.kt"
text = ui_path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    '''private const val NATIVE_RESOLUTION_POSITION = 23
''',
    '''private const val NATIVE_RESOLUTION_POSITION = 23
private const val FIT_GB_RESOLUTION_POSITION = 24
private const val FIT_GBC_RESOLUTION_POSITION = 25
private const val FIT_GBA_RESOLUTION_POSITION = 26
private const val FIT_DS_RESOLUTION_POSITION = 27
''',
    "fit resolution positions",
)

replace_once(
    '''        add("スマホの元解像度 / 100%")
    }
''',
    '''        add("スマホの元解像度 / 100%")
        add(androidx.compose.ui.res.stringResource(R.string.resolution_fit_gb_v047))
        add(androidx.compose.ui.res.stringResource(R.string.resolution_fit_gbc_v047))
        add(androidx.compose.ui.res.stringResource(R.string.resolution_fit_gba_v047))
        add(androidx.compose.ui.res.stringResource(R.string.resolution_fit_ds_v047))
    }
''',
    "fit resolution labels",
)

replace_once(
    '''        resolutionPosition == NATIVE_RESOLUTION_POSITION -> GameBoyFilter.RESOLUTION_NATIVE
        else -> GameBoyFilter.RESOLUTION_GB
''',
    '''        resolutionPosition == NATIVE_RESOLUTION_POSITION -> GameBoyFilter.RESOLUTION_NATIVE
        resolutionPosition == FIT_GB_RESOLUTION_POSITION -> GameBoyFilter.RESOLUTION_GB_FIT
        resolutionPosition == FIT_GBC_RESOLUTION_POSITION -> GameBoyFilter.RESOLUTION_GBC_FIT
        resolutionPosition == FIT_GBA_RESOLUTION_POSITION -> GameBoyFilter.RESOLUTION_GBA_FIT
        resolutionPosition == FIT_DS_RESOLUTION_POSITION -> GameBoyFilter.RESOLUTION_DS_FIT
        else -> GameBoyFilter.RESOLUTION_GB
''',
    "fit resolution mapping",
)

ui_path.write_text(text)
print("v0.1.47 UI exposes full-content fit-inside fixed resolutions", flush=True)
