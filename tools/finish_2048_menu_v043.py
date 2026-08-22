#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_2048_menu_v043.py <generated_kotlin_root>")

root = Path(sys.argv[1]).resolve()
path = root / "com/sktpj/gbmoder/AppMenuActivity.kt"
text = path.read_text()

old = '''    if (BuildConfig.DEBUG_FEATURES) {
        MenuEntry(
            title = stringResource(R.string.menu_diagnostics_title),
'''
new = '''    if (BuildConfig.DEBUG_FEATURES) {
        MenuEntry(
            title = "2048TD",
            description = "現在のフィルター設定を適用した状態でプレイ",
            tag = "menu-2048td",
            onClick = {
                context.startActivity(
                    Intent().setClassName(context, "com.sktpj.gbmoder.Game2048ContentActivity").apply {
                        putExtra(MediaConversionActivity.EXTRA_MODE, options.mode)
                        putExtra(MediaConversionActivity.EXTRA_RESOLUTION, options.resolution)
                        putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, options.brightness)
                        putExtra(MediaConversionActivity.EXTRA_CONTRAST, options.contrast)
                        putExtra(MediaConversionActivity.EXTRA_DITHER, options.dither)
                    },
                )
            },
        )

        MenuEntry(
            title = stringResource(R.string.menu_diagnostics_title),
'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"2048TD menu entry: expected exactly one match, got {count}")

path.write_text(text.replace(old, new, 1))
print("v0.1.43 2048TD menu entry prepared", flush=True)
