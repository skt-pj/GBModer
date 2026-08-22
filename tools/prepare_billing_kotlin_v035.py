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
    'private const val DEFAULT_RESOLUTION_POSITION = 7',
    'private const val DEFAULT_RESOLUTION_POSITION = 0',
    "GB default resolution",
)

replace_ui_once(
    '''        for (percent in 5..95 step 5) {
            add("端末比 / ${percent}%")
        }
''',
    '''        for (percent in 5..95 step 5) {
            if (percent == 20) {
                add("端末比 / 20%（テキスト表示時推奨）")
            } else {
                add("端末比 / ${percent}%")
            }
        }
''',
    "20 percent text recommendation label",
)

replace_ui_once(
    'description = "画面内の文字を認識し、低解像度向け8×8フォントで再描画します。GB / 160×144で有効です。",',
    'description = "画面内の文字を認識し、低解像度向け8×8フォントで再描画します。端末比 / 20%はテキスト表示時の推奨解像度です。",',
    "text recommendation description",
)

replace_ui_once(
    'else -> GameBoyFilter.phoneResolution(20)',
    'else -> GameBoyFilter.RESOLUTION_GB',
    "resolution fallback defaults to GB",
)

replace_ui_once(
    '        Spacer(Modifier.height(12.dp).testTag("top-quiet-zone"))\n\n        if (!state.accessibilityReady) {',
    '''        Spacer(Modifier.height(12.dp).testTag("top-quiet-zone"))

        AppMenuShortcut(
            options = MediaFileConverter.Options(
                modeValueForPosition(modePosition),
                resolutionValueForPosition(resolutionPosition),
                brightness.roundToInt(),
                contrast.roundToInt(),
                dither,
            ),
        )

        if (!state.accessibilityReady) {''',
    "main app menu shortcut",
)

replace_ui_once(
    '''@Composable
private fun FirstSetupCard(actions: GbModerUiActions) {
    Card(
        modifier = Modifier.fillMaxWidth().testTag("first-setup-card"),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("初回設定", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "ユーザー補助を有効にして、画面のテキストを取得します。",
                style = MaterialTheme.typography.bodyMedium,
            )
            Button(
                onClick = actions::onAccessibilitySetup,
                modifier = Modifier.fillMaxWidth().testTag("accessibility-setup"),
            ) {
                Text("ユーザー補助を有効化")
            }
        }
    }
}
''',
    '''@Composable
private fun FirstSetupCard(actions: GbModerUiActions) {
    var disclosureVisible by rememberSaveable { mutableStateOf(false) }

    Card(
        modifier = Modifier.fillMaxWidth().testTag("first-setup-card"),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("初回設定", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "ユーザー補助を有効にして、画面のテキストを取得します。",
                style = MaterialTheme.typography.bodyMedium,
            )
            Button(
                onClick = { disclosureVisible = true },
                modifier = Modifier.fillMaxWidth().testTag("accessibility-setup"),
            ) {
                Text("ユーザー補助を有効化")
            }
        }
    }

    if (disclosureVisible) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { disclosureVisible = false },
            title = {
                androidx.compose.material3.Text(
                    androidx.compose.ui.res.stringResource(R.string.accessibility_disclosure_title),
                )
            },
            text = {
                androidx.compose.material3.Text(
                    androidx.compose.ui.res.stringResource(R.string.accessibility_disclosure_body),
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        disclosureVisible = false
                        actions.onAccessibilitySetup()
                    },
                    modifier = Modifier.testTag("accessibility-disclosure-accept"),
                ) {
                    androidx.compose.material3.Text(
                        androidx.compose.ui.res.stringResource(R.string.accessibility_disclosure_accept),
                    )
                }
            },
            dismissButton = {
                OutlinedButton(
                    onClick = { disclosureVisible = false },
                    modifier = Modifier.testTag("accessibility-disclosure-decline"),
                ) {
                    androidx.compose.material3.Text(
                        androidx.compose.ui.res.stringResource(R.string.accessibility_disclosure_decline),
                    )
                }
            },
        )
    }
}
''',
    "accessibility prominent disclosure",
)

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

localization_path = generated_root / "com/sktpj/gbmoder/GbModerLocalization.kt"
localization_text = localization_path.read_text()


def replace_localization_once(old: str, new: str, label: str) -> None:
    global localization_text
    count = localization_text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    localization_text = localization_text.replace(old, new, 1)


replace_localization_once(
    '        "スマホの元解像度 / 100%" to R.string.native_resolution,\n',
    '        "スマホの元解像度 / 100%" to R.string.native_resolution,\n'
    '        "端末比 / 20%（テキスト表示時推奨）" to R.string.phone_ratio_text_recommended,\n',
    "20 percent recommendation localization",
)

replace_localization_once(
    '        "画面内の文字を認識し、低解像度向け8×8フォントで再描画します。GB / 160×144で有効です。" to R.string.readable_text_description,',
    '        "画面内の文字を認識し、低解像度向け8×8フォントで再描画します。端末比 / 20%はテキスト表示時の推奨解像度です。" to R.string.readable_text_description_v040,',
    "text recommendation localization",
)

localization_path.write_text(localization_text)
print("v0.1.40 GB default resolution, text recommendation, menu, privacy, accessibility disclosure, and billing Kotlin UI prepared")
