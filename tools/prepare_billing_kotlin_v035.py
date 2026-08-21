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
print("v0.1.36 menu, privacy, accessibility disclosure, and billing Kotlin UI prepared")
