#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_ui_restore_v046.py <generated_kotlin_root>")

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
    '''@Composable
internal fun GbModerTheme(activity: Activity, content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val colorScheme = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && dark -> dynamicDarkColorScheme(activity)
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> dynamicLightColorScheme(activity)
        dark -> androidx.compose.material3.darkColorScheme()
        else -> androidx.compose.material3.lightColorScheme()
    }
    MaterialTheme(colorScheme = colorScheme, content = content)
}
''',
    '''@Composable
internal fun GbModerTheme(activity: Activity, content: @Composable () -> Unit) {
    val colorScheme = androidx.compose.material3.lightColorScheme(
        primary = Color(0xFF485438),
        onPrimary = Color(0xFFF7F9EA),
        primaryContainer = Color(0xFFC9D3A8),
        onPrimaryContainer = Color(0xFF1F241D),
        secondary = Color(0xFF667055),
        secondaryContainer = Color(0xFFDCE4C4),
        background = Color(0xFFE2E6D6),
        onBackground = Color(0xFF1F241D),
        surface = Color(0xFFF2F4E8),
        onSurface = Color(0xFF1F241D),
        surfaceVariant = Color(0xFFD8DDC8),
        onSurfaceVariant = Color(0xFF4E5546),
        outline = Color(0xFF747C68),
    )
    MaterialTheme(colorScheme = colorScheme, content = content)
}
''',
    "restore non-black Game Boy light theme",
)

replace_once(
    "    var resolutionMenuExpanded by remember { mutableStateOf(false) }\n\n    val resolutions = buildList {",
    "    var resolutionMenuExpanded by remember { mutableStateOf(false) }\n    val context = androidx.compose.ui.platform.LocalContext.current\n\n    val resolutions = buildList {",
    "main screen context",
)

replace_once(
    "                        captureRoutePosition,\n                        true,\n",
    "                        captureRoutePosition,\n                        false,\n",
    "disable text recognition from Compose",
)

conversion_block = '''        UnifiedConversionControls(
            options = MediaFileConverter.Options(
                modeValueForPosition(modePosition),
                resolutionValueForPosition(resolutionPosition),
                brightness.roundToInt(),
                contrast.roundToInt(),
                dither,
            ),
            modifier = Modifier.fillMaxWidth().testTag("media-conversion-card"),
        )
'''
inserted_block = conversion_block + '''
        if (BuildConfig.DEBUG_FEATURES) {
            HorizontalDivider()
            SectionTitle("2048TD")
            OutlinedButton(
                onClick = {
                    context.startActivity(
                        android.content.Intent().setClassName(
                            context,
                            "com.sktpj.gbmoder.Game2048ContentActivity",
                        ).apply {
                            putExtra(MediaConversionActivity.EXTRA_MODE, modeValueForPosition(modePosition))
                            putExtra(MediaConversionActivity.EXTRA_RESOLUTION, resolutionValueForPosition(resolutionPosition))
                            putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, brightness.roundToInt())
                            putExtra(MediaConversionActivity.EXTRA_CONTRAST, contrast.roundToInt())
                            putExtra(MediaConversionActivity.EXTRA_DITHER, dither)
                        },
                    )
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp)
                    .testTag("main-2048td"),
            ) {
                Text("2048TDをプレイ")
            }
        }
'''
replace_once(conversion_block, inserted_block, "place 2048TD after conversion")
ui.write_text(text)

menu = root / "AppMenuActivity.kt"
menu_text = menu.read_text()
menu_block = '''        MenuEntry(
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

'''
count = menu_text.count(menu_block)
if count != 1:
    raise SystemExit(f"remove 2048TD from menu: expected exactly one match, got {count}")
menu.write_text(menu_text.replace(menu_block, "", 1))

print("v0.1.46 text recognition disabled; Game Boy light UI restored; 2048TD moved after conversion", flush=True)
