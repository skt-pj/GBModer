#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_mode_shell_v048.py <generated_kotlin_root>")

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
    '''    Column(
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp)
            .testTag("settings-scroll"),
''',
    '''    val modeShellColor = when (modePosition) {
        1 -> Color(0xFFD8D3F0) // GBC shell
        2 -> Color(0xFFD2D9EC) // GBA shell
        3 -> Color(0xFFD7D9D7) // DS shell
        else -> Color(0xFFB7C48D) // GB shell
    }

    Column(
        modifier = modifier
            .background(modeShellColor)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp)
            .testTag("settings-scroll")
            .testTag("mode-shell-background"),
''',
    "apply selected console shell color to full compact settings background",
)

replace_once(
    '''        colors = CardDefaults.cardColors(containerColor = backgroundColor),
''',
    '''        colors = CardDefaults.cardColors(containerColor = backgroundColor),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
''',
    "make console identity panel visibly separate from full shell background",
)

ui.write_text(text)
print("v0.1.48 selected GB/GBC/GBA/DS mode now drives the full settings background", flush=True)
