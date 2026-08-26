#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_release_ui_v041.py <generated_kotlin_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"


def patch(path: Path, replacements):
    text = path.read_text()
    for old, new, label in replacements:
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"{path.name} {label}: expected exactly one match, got {count}")
        text = text.replace(old, new, 1)
    path.write_text(text)


ui = root / "GbModerComposeUi.kt"
patch(
    ui,
    [
        (
            ".padding(horizontal = 20.dp, vertical = 16.dp)\n            .testTag(\"settings-scroll\"),\n        verticalArrangement = Arrangement.spacedBy(18.dp),",
            ".padding(horizontal = 20.dp, vertical = 8.dp)\n            .testTag(\"settings-scroll\"),\n        verticalArrangement = Arrangement.spacedBy(14.dp),",
            "compact settings spacing",
        ),
        (
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

        if (!state.accessibilityReady) {
            FirstSetupCard(actions)
        }

        SectionTitle("共通")

        SectionTitle("表示モード")
''',
            '''        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SectionTitle("表示モード", modifier = Modifier.weight(1f))
            AppMenuShortcut(
                options = MediaFileConverter.Options(
                    modeValueForPosition(modePosition),
                    resolutionValueForPosition(resolutionPosition),
                    brightness.roundToInt(),
                    contrast.roundToInt(),
                    dither,
                ),
            )
        }

        if (BuildConfig.DEBUG_FEATURES && !state.accessibilityReady) {
            FirstSetupCard(actions)
        }
''',
            "compact header and debug-only accessibility setup",
        ),
        (
            '''        Text(
            "端末比は5%刻みで選択できます。表示モードの色・階調処理と解像度の出力サイズを組み合わせて適用します。",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

''',
            "",
            "remove resolution implementation explanation",
        ),
        (
            '            description = "階調境界をパターン化して見かけの階調を補います。",',
            '            description = "",',
            "remove dither implementation explanation",
        ),
        (
            '''        ToggleSettingRow(
            title = "文字を読みやすくする",
            description = "画面内の文字を認識し、低解像度向け8×8フォントで再描画します。端末比 / 20%はテキスト表示時の推奨解像度です。",
            checked = textRecognitionEnabled,
            onCheckedChange = { textRecognitionEnabled = it },
            contentDescription = "文字認識と8×8再描画",
            tag = "text-recognition-row",
        )
''',
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
            "debug-only readable text and concise copy",
        ),
        (
            '''        HorizontalDivider()
        SectionTitle("フィルター")

        LiveModeSubscriptionCard()

        Button(
''',
            '''        if (BuildConfig.DEBUG_FEATURES) {
            HorizontalDivider()
            SectionTitle(androidx.compose.ui.res.stringResource(R.string.live_mode_title))

            LiveModeSubscriptionCard()

            Button(
''',
            "debug-only live mode section start",
        ),
        (
            '''        Surface(
            modifier = Modifier.fillMaxWidth().testTag("status-message"),
            shape = RoundedCornerShape(12.dp),
            color = MaterialTheme.colorScheme.surfaceContainer,
        ) {
            Text(
                text = state.status,
                modifier = Modifier.padding(14.dp),
                style = MaterialTheme.typography.bodyMedium,
            )
        }

        HorizontalDivider()
        SectionTitle("変換")
''',
            '''            Surface(
                modifier = Modifier.fillMaxWidth().testTag("status-message"),
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surfaceContainer,
            ) {
                Text(
                    text = state.status,
                    modifier = Modifier.padding(14.dp),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }

        HorizontalDivider()
        SectionTitle("変換")
''',
            "debug-only live mode section end",
        ),
        (
            '''        DiagnosticsCard(
            expanded = detailsExpanded,
            onToggle = { detailsExpanded = !detailsExpanded },
            captureRoutePosition = captureRoutePosition,
            onCaptureRouteChange = { captureRoutePosition = it },
            onLogSync = actions::onLogSync,
            onAdbGuide = actions::onAdbGuide,
        )
''',
            '''        if (BuildConfig.DEBUG_FEATURES) {
            DiagnosticsCard(
                expanded = detailsExpanded,
                onToggle = { detailsExpanded = !detailsExpanded },
                captureRoutePosition = captureRoutePosition,
                onCaptureRouteChange = { captureRoutePosition = it },
                onLogSync = actions::onLogSync,
                onAdbGuide = actions::onAdbGuide,
            )
        }
''',
            "debug-only diagnostics card",
        ),
        (
            '''@Composable
private fun SectionTitle(text: String) {
    Text(text, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
}
''',
            '''@Composable
private fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Text(
        text,
        modifier = modifier,
        style = MaterialTheme.typography.titleSmall,
        fontWeight = FontWeight.SemiBold,
    )
}
''',
            "section title modifier",
        ),
        (
            '''        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(
                description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
''',
            '''        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            if (description.isNotBlank()) {
                Text(
                    description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
''',
            "optional toggle description",
        ),
    ],
)

shortcut = root / "AppMenuShortcut.kt"
patch(
    shortcut,
    [
        (
            '''    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.End,
    ) {
        IconButton(
            onClick = {
                context.startActivity(
                    Intent(context, AppMenuActivity::class.java).apply {
                        putExtra(MediaConversionActivity.EXTRA_MODE, options.mode)
                        putExtra(MediaConversionActivity.EXTRA_RESOLUTION, options.resolution)
                        putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, options.brightness)
                        putExtra(MediaConversionActivity.EXTRA_CONTRAST, options.contrast)
                        putExtra(MediaConversionActivity.EXTRA_DITHER, options.dither)
                    },
                )
            },
            modifier = Modifier.testTag("app-menu"),
        ) {
            Icon(
                imageVector = Icons.Default.MoreVert,
                contentDescription = stringResource(R.string.menu_open),
            )
        }
    }
''',
            '''    IconButton(
        onClick = {
            context.startActivity(
                Intent(context, AppMenuActivity::class.java).apply {
                    putExtra(MediaConversionActivity.EXTRA_MODE, options.mode)
                    putExtra(MediaConversionActivity.EXTRA_RESOLUTION, options.resolution)
                    putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, options.brightness)
                    putExtra(MediaConversionActivity.EXTRA_CONTRAST, options.contrast)
                    putExtra(MediaConversionActivity.EXTRA_DITHER, options.dither)
                },
            )
        },
        modifier = Modifier.testTag("app-menu"),
    ) {
        Icon(
            imageVector = Icons.Default.MoreVert,
            contentDescription = stringResource(R.string.menu_open),
        )
    }
''',
            "inline menu icon",
        ),
    ],
)

localization = root / "GbModerLocalization.kt"
patch(
    localization,
    [
        (
            '        "端末比 / 20%（テキスト表示時推奨）" to R.string.phone_ratio_text_recommended,',
            '        "端末比 / 20%（テキスト推奨）" to R.string.phone_ratio_text_recommended_v041,',
            "concise 20 percent label localization",
        ),
        (
            '        "画面内の文字を認識し、低解像度向け8×8フォントで再描画します。端末比 / 20%はテキスト表示時の推奨解像度です。" to R.string.readable_text_description_v040,',
            '        "文字表示には端末比 / 20%を推奨します。" to R.string.readable_text_description_v041,',
            "concise readable text localization",
        ),
    ],
)

# The visible list label is generated before localization routing.
ui_text = ui.read_text()
old_label = '                add("端末比 / 20%（テキスト表示時推奨）")'
if ui_text.count(old_label) != 1:
    raise SystemExit("GbModerComposeUi.kt concise 20 percent label: expected one match")
ui.write_text(ui_text.replace(old_label, '                add("端末比 / 20%（テキスト推奨）")', 1))

menu = root / "AppMenuActivity.kt"
patch(
    menu,
    [
        (
            "        LiveModeBillingManager.initialize(this)\n",
            "        if (BuildConfig.DEBUG_FEATURES) {\n            LiveModeBillingManager.initialize(this)\n        }\n",
            "debug-only menu billing init",
        ),
        (
            "        LiveModeBillingManager.refreshEntitlement()\n",
            "        if (BuildConfig.DEBUG_FEATURES) {\n            LiveModeBillingManager.refreshEntitlement()\n        }\n",
            "debug-only menu billing refresh",
        ),
        (
            '        text = stringResource(R.string.menu_description),',
            '        text = stringResource(R.string.menu_description_v041),',
            "release menu description",
        ),
        (
            '        description = stringResource(R.string.menu_libraries_description),',
            '        description = stringResource(R.string.menu_libraries_description_v041),',
            "release libraries description",
        ),
        (
            '        description = stringResource(R.string.menu_privacy_description),',
            '        description = stringResource(R.string.menu_privacy_description_v041),',
            "release privacy description",
        ),
        (
            '        description = stringResource(R.string.libraries_page_description),',
            '        description = stringResource(R.string.libraries_page_description_v041),',
            "release libraries page description",
        ),
        (
            '''    MenuEntry(
        title = stringResource(R.string.menu_diagnostics_title),
        description = stringResource(R.string.menu_diagnostics_description),
        tag = "menu-diagnostics",
        onClick = {
            context.startActivity(
                Intent(context, VideoDiagnosticsActivity::class.java).apply {
                    putExtra(MediaConversionActivity.EXTRA_MODE, options.mode)
                    putExtra(MediaConversionActivity.EXTRA_RESOLUTION, options.resolution)
                    putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, options.brightness)
                    putExtra(MediaConversionActivity.EXTRA_CONTRAST, options.contrast)
                    putExtra(MediaConversionActivity.EXTRA_DITHER, options.dither)
                },
            )
        },
    )
''',
            '''    if (BuildConfig.DEBUG_FEATURES) {
        MenuEntry(
            title = stringResource(R.string.menu_diagnostics_title),
            description = stringResource(R.string.menu_diagnostics_description),
            tag = "menu-diagnostics",
            onClick = {
                context.startActivity(
                    Intent(context, VideoDiagnosticsActivity::class.java).apply {
                        putExtra(MediaConversionActivity.EXTRA_MODE, options.mode)
                        putExtra(MediaConversionActivity.EXTRA_RESOLUTION, options.resolution)
                        putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, options.brightness)
                        putExtra(MediaConversionActivity.EXTRA_CONTRAST, options.contrast)
                        putExtra(MediaConversionActivity.EXTRA_DITHER, options.dither)
                    },
                )
            },
        )
    }
''',
            "debug-only diagnostics menu entry",
        ),
        (
            '''    HorizontalDivider()
    MaterialText(
        text = stringResource(R.string.live_mode_title),
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
    )
    LiveModeSubscriptionCard()

    HorizontalDivider()
''',
            '''    if (BuildConfig.DEBUG_FEATURES) {
        HorizontalDivider()
        MaterialText(
            text = stringResource(R.string.live_mode_title),
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
        )
        LiveModeSubscriptionCard()
    }

    HorizontalDivider()
''',
            "debug-only subscription menu section",
        ),
        (
            '''    PrivacySection(
        title = stringResource(R.string.privacy_section_accessibility),
        body = stringResource(R.string.privacy_accessibility_body),
    )
    PrivacySection(
        title = stringResource(R.string.privacy_section_screen_capture),
        body = stringResource(R.string.privacy_screen_capture_body),
    )
''',
            '''    if (BuildConfig.DEBUG_FEATURES) {
        PrivacySection(
            title = stringResource(R.string.privacy_section_accessibility),
            body = stringResource(R.string.privacy_accessibility_body),
        )
        PrivacySection(
            title = stringResource(R.string.privacy_section_screen_capture),
            body = stringResource(R.string.privacy_screen_capture_body),
        )
    }
''',
            "debug-only capture privacy sections",
        ),
        (
            '''    PrivacySection(
        title = stringResource(R.string.privacy_section_billing),
        body = stringResource(R.string.privacy_billing_body),
    )
    PrivacySection(
        title = stringResource(R.string.privacy_section_diagnostics),
        body = stringResource(R.string.privacy_diagnostics_body),
    )
''',
            '''    if (BuildConfig.DEBUG_FEATURES) {
        PrivacySection(
            title = stringResource(R.string.privacy_section_billing),
            body = stringResource(R.string.privacy_billing_body),
        )
        PrivacySection(
            title = stringResource(R.string.privacy_section_diagnostics),
            body = stringResource(R.string.privacy_diagnostics_body),
        )
    }
''',
            "debug-only billing diagnostics privacy sections",
        ),
    ],
)

print("v0.1.41 release UI compacted; live and diagnostics gated by BuildConfig.DEBUG_FEATURES")
