#!/usr/bin/env python3
"""Expose distinct layout modes in the Compose live-filter controls."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_live_layout_kotlin_v057.py <generated_kotlin_root>")

ui_path = Path(sys.argv[1]) / "com/sktpj/gbmoder/GbModerComposeUi.kt"
text = ui_path.read_text()


def once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    text = text.replace(old, new, 1)


once(
    "        captureRoutePosition: Int,\n        textRecognitionEnabled: Boolean,\n",
    "        captureRoutePosition: Int,\n        textRecognitionEnabled: Boolean,\n"
    "        layoutPosition: Int,\n",
    "UI onStart contract",
)

once(
    "    var modePosition by rememberSaveable { mutableStateOf(0) }\n",
    "    var modePosition by rememberSaveable { mutableStateOf(0) }\n"
    "    var layoutPosition by rememberSaveable { mutableStateOf(1) }\n",
    "save selected layout; chassis is the current default",
)

once(
    '''        SectionTitle("解像度")
        Box(modifier = Modifier.fillMaxWidth()) {
''',
    '''        SectionTitle("画面レイアウト")
        val layouts = listOf("全画面", "筐体", "SGB")
        SingleChoiceSegmentedButtonRow(
            modifier = Modifier.fillMaxWidth().testTag("layout-segmented"),
        ) {
            layouts.forEachIndexed { index, label ->
                SegmentedButton(
                    selected = layoutPosition == index,
                    onClick = { layoutPosition = index },
                    shape = SegmentedButtonDefaults.itemShape(index = index, count = layouts.size),
                    label = { Text(label) },
                )
            }
        }
        Text(
            "全画面：筐体なし / 筐体：ゲーム機全体 / SGB：ゲーム画面を専用フレームで囲む",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        SectionTitle("解像度")
        Box(modifier = Modifier.fillMaxWidth()) {
''',
    "three-way layout selector",
)

once(
    '''                        captureRoutePosition,
                        false,
                    )
''',
    '''                        captureRoutePosition,
                        false,
                        layoutPosition,
                    )
''',
    "pass layout to running capture",
)
ui_path.write_text(text)
print("v0.1.57 Compose layout mode selector applied", flush=True)
