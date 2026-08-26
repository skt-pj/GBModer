#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_mode_backdrop_v047.py <generated_kotlin_root>")

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
    '''        if (BuildConfig.DEBUG_FEATURES && !state.accessibilityReady) {
            FirstSetupCard(actions)
        }
''',
    '''        ModeBackdrop(modePosition)

        if (BuildConfig.DEBUG_FEATURES && !state.accessibilityReady) {
            FirstSetupCard(actions)
        }
''',
    "restore compact mode backdrop",
)

anchor = '''@Composable
private fun FirstSetupCard(actions: GbModerUiActions) {'''
mode_backdrop = '''@Composable
private fun ModeBackdrop(modePosition: Int) {
    val shortLabel: String
    val longLabel: String
    val backgroundColor: Color
    when (modePosition) {
        1 -> {
            shortLabel = "GBC"
            longLabel = "GAME BOY COLOR"
            backgroundColor = Color(0xFFD8D3F0)
        }
        2 -> {
            shortLabel = "GBA"
            longLabel = "GAME BOY ADVANCE"
            backgroundColor = Color(0xFFD2D9EC)
        }
        3 -> {
            shortLabel = "DS"
            longLabel = "NINTENDO DS"
            backgroundColor = Color(0xFFD7D9D7)
        }
        else -> {
            shortLabel = "GB"
            longLabel = "GAME BOY"
            backgroundColor = Color(0xFFB7C48D)
        }
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(112.dp)
            .testTag("mode-backdrop"),
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = backgroundColor),
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 18.dp, vertical = 14.dp),
        ) {
            Text(
                text = shortLabel,
                modifier = Modifier.align(Alignment.CenterEnd),
                color = Color(0x331F241D),
                fontFamily = FontFamily.Monospace,
                fontSize = 58.sp,
                fontWeight = FontWeight.Bold,
            )
            Column(
                modifier = Modifier.align(Alignment.CenterStart),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text(
                    text = longLabel,
                    color = Color(0xFF1F241D),
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    text = "GB  /  GBC  /  GBA  /  DS",
                    color = Color(0xFF4A5143),
                    fontFamily = FontFamily.Monospace,
                    style = MaterialTheme.typography.labelMedium,
                )
            }
        }
    }
}

'''
replace_once(anchor, mode_backdrop + anchor, "add mode backdrop composable")

ui.write_text(text)
print("v0.1.47 GB/GBC/GBA/DS mode backdrop restored on compact phone UI", flush=True)
