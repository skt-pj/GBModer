#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_icon_localization_source_v030.py <generated_src_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)

capture_path = root / "FilterCaptureService.java"
capture = capture_path.read_text()
capture = replace_once(
    capture,
    'Toast.makeText(this, "GBModerのユーザー補助サービスを有効にしてください", Toast.LENGTH_LONG).show();',
    'Toast.makeText(this, getString(R.string.capture_accessibility_required), Toast.LENGTH_LONG).show();',
    "capture accessibility toast",
)
capture = replace_once(
    capture,
    '.setContentText("他アプリの画面をGame Boy風に変換中")',
    '.setContentText(getString(R.string.notification_filter_active))',
    "notification text",
)
capture = replace_once(
    capture,
    '.setSmallIcon(android.R.drawable.ic_menu_view)',
    '.setSmallIcon(R.drawable.ic_notification)',
    "notification small icon",
)
capture = replace_once(
    capture,
    '                        "解除",\n                        stopPendingIntent',
    '                        getString(R.string.notification_stop),\n                        stopPendingIntent',
    "notification stop action",
)
capture = replace_once(
    capture,
    '                                "画面全体共有は使用できません。「1つのアプリ」を選択してください。",',
    '                                getString(R.string.whole_screen_not_supported),',
    "whole screen warning",
)
capture = replace_once(
    capture,
    '                "GBModer filter",\n                NotificationManager.IMPORTANCE_LOW',
    '                getString(R.string.notification_channel_name),\n                NotificationManager.IMPORTANCE_LOW',
    "notification channel name",
)
capture = replace_once(
    capture,
    '        channel.setDescription("MediaProjection screen filter");',
    '        channel.setDescription(getString(R.string.notification_channel_description));',
    "notification channel description",
)
capture_path.write_text(capture)

main_path = root / "MainActivity.java"
main = main_path.read_text()
method_start = main.find("    private void showAdbGuide() {\n")
method_end = main.find("\n    private boolean isAccessibilityServiceEnabled() {", method_start)
if method_start < 0 or method_end < 0:
    raise SystemExit("ADB guide method markers not found")
localized_method = '''    private void showAdbGuide() {
        new AlertDialog.Builder(this)
                .setTitle(getString(R.string.adb_guide_title))
                .setMessage(getString(R.string.adb_guide_message))
                .setNeutralButton(getString(R.string.adb_open_developer_settings), (dialog, which) -> {
                    try {
                        startActivity(new Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS));
                    } catch (Throwable error) {
                        startActivity(new Intent(Settings.ACTION_SETTINGS));
                    }
                })
                .setPositiveButton(getString(R.string.adb_guide_close), null)
                .show();
    }
'''
main = main[:method_start] + localized_method + main[method_end:]
main = replace_once(
    main,
    '            composeUiState.setStatus(value);',
    '            composeUiState.setStatus(GbModerLocalization.localize(this, value));',
    "localized Compose status bridge",
)
main_path.write_text(main)

print("v0.1.30 Android icon/localization source adjustments applied")
