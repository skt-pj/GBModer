#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_2048_main_v045.py <generated_kotlin_root>")

root = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder"
ui = root / "GbModerComposeUi.kt"
text = ui.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


# A utility screen should keep the tool controls primary. The game is therefore presented as
# one coherent supporting-content card after the visual settings, not as another primary section.
anchor = '''        if (BuildConfig.DEBUG_FEATURES) {
            HorizontalDivider()
            SectionTitle(androidx.compose.ui.res.stringResource(R.string.live_mode_title))
'''
replacement = '''        if (BuildConfig.DEBUG_FEATURES) {
            GameContentCard(
                options = MediaFileConverter.Options(
                    modeValueForPosition(modePosition),
                    resolutionValueForPosition(resolutionPosition),
                    brightness.roundToInt(),
                    contrast.roundToInt(),
                    dither,
                ),
            )
        }

        if (BuildConfig.DEBUG_FEATURES) {
            HorizontalDivider()
            SectionTitle(androidx.compose.ui.res.stringResource(R.string.live_mode_title))
'''
replace_once(anchor, replacement, "main-screen 2048TD card placement")

helper_anchor = '''@Composable
private fun SectionTitle(text: String, modifier: Modifier = Modifier) {
'''
helper = '''@Composable
private fun GameContentCard(options: MediaFileConverter.Options) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val boardAlpha = listOf(
        0.12f, 0.22f, 0.10f, 0.36f,
        0.30f, 0.10f, 0.48f, 0.16f,
        0.10f, 0.58f, 0.22f, 0.10f,
        0.42f, 0.14f, 0.10f, 0.68f,
    )

    Card(
        onClick = {
            context.startActivity(
                android.content.Intent().setClassName(
                    context,
                    "com.sktpj.gbmoder.Game2048ContentActivity",
                ).apply {
                    putExtra(MediaConversionActivity.EXTRA_MODE, options.mode)
                    putExtra(MediaConversionActivity.EXTRA_RESOLUTION, options.resolution)
                    putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, options.brightness)
                    putExtra(MediaConversionActivity.EXTRA_CONTRAST, options.contrast)
                    putExtra(MediaConversionActivity.EXTRA_DITHER, options.dither)
                },
            )
        },
        modifier = Modifier
            .fillMaxWidth()
            .testTag("main-2048td-card"),
        shape = MaterialTheme.shapes.extraLarge,
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer,
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(18.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(
                    androidx.compose.ui.res.stringResource(R.string.playground_label_v045),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.72f),
                    fontWeight = FontWeight.SemiBold,
                    letterSpacing = 0.8.sp,
                )
                Text(
                    "2048TD",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    androidx.compose.ui.res.stringResource(R.string.playground_description_v045),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.82f),
                )
                Surface(
                    shape = RoundedCornerShape(999.dp),
                    color = MaterialTheme.colorScheme.primary,
                ) {
                    Text(
                        androidx.compose.ui.res.stringResource(R.string.playground_action_v045),
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onPrimary,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }

            Column(
                modifier = Modifier
                    .background(
                        MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.08f),
                        RoundedCornerShape(16.dp),
                    )
                    .padding(9.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                for (row in 0 until 4) {
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        for (column in 0 until 4) {
                            val alpha = boardAlpha[row * 4 + column]
                            Box(
                                Modifier
                                    .size(16.dp)
                                    .background(
                                        MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = alpha),
                                        RoundedCornerShape(5.dp),
                                    ),
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String, modifier: Modifier = Modifier) {
'''
replace_once(helper_anchor, helper, "2048TD supporting card composable")
ui.write_text(text)

menu = root / "AppMenuActivity.kt"
menu_text = menu.read_text()
old_menu = '''        MenuEntry(
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
if menu_text.count(old_menu) != 1:
    raise SystemExit("2048TD menu removal: expected exactly one match")
menu.write_text(menu_text.replace(old_menu, "", 1))

print("v0.1.45 2048TD moved from overflow menu to a main-screen playground card", flush=True)
