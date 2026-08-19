#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_capture_source_v016.py <generated_src_root>")

root = Path(sys.argv[1])
path = root / "com/sktpj/gbmoder/MainActivity.java"
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    '''        TextView note = text(
                "Android 14以降では対象アプリのウィンドウだけを直接取得するため、GBModer自身のフィルター表示は再取得しません。" +
                        " 通知欄の「解除」からいつでも停止できます。DRM/FLAG_SECURE等で保護された画面は取得できません。",
                12,
                false
        );
''',
    '''        TextView note = text(
                "Android 14以降は高速化のためMediaProjectionの『1つのアプリ』共有を使います。" +
                        " 画面全体を選ぶと自己キャプチャを検出して停止します。対象アプリを切り替える場合は再度開始してください。" +
                        " 通知欄の『解除』からいつでも停止できます。DRM/FLAG_SECURE等で保護された画面は取得できません。",
                12,
                false
        );
''',
    "capture note",
)

replace_once(
    '''    private void startFilterForCurrentPlatform() {
        pendingStartAfterAccessibility = false;

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
            if (accessibilityService == null) {
                statusText.setText("ユーザー補助サービスに接続できません");
                return;
            }

            accessibilityService.startWindowFilter(
                    getSelectedMode(),
                    getSelectedResolution(),
                    getBrightness(),
                    getContrast(),
                    ditherSwitch.isChecked()
            );
            statusText.setText("表示モード × 解像度の組み合わせで開始しました");
            return;
        }

        requestScreenCapture();
    }
''',
    '''    private void startFilterForCurrentPlatform() {
        pendingStartAfterAccessibility = false;

        FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
        if (accessibilityService == null) {
            statusText.setText("ユーザー補助サービスに接続できません");
            return;
        }

        // Android 14+ also uses MediaProjection now. Single-app projection excludes
        // GBModer's accessibility overlay from the captured content and avoids the
        // AccessibilityService screenshot interval limit seen in performance logs.
        accessibilityService.stopWindowFilter();
        accessibilityService.clearOverlay();
        requestScreenCapture();
    }
''',
    "start capture routing",
)

replace_once(
    '''        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            Intent stopIntent = new Intent(this, FilterCaptureService.class);
            stopIntent.setAction(FilterCaptureService.ACTION_STOP);
            startService(stopIntent);
        }
''',
    '''        Intent stopIntent = new Intent(this, FilterCaptureService.class);
        stopIntent.setAction(FilterCaptureService.ACTION_STOP);
        startService(stopIntent);
''',
    "stop media projection on all versions",
)

replace_once(
    '''    private void requestScreenCapture() {
        pendingStartAfterAccessibility = false;
        statusText.setText("共有する他アプリを選択してください");
        startActivityForResult(createSingleAppPreferredCaptureIntent(), REQUEST_CAPTURE);
    }
''',
    '''    private void requestScreenCapture() {
        pendingStartAfterAccessibility = false;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            statusText.setText("高速キャプチャ: 『1つのアプリ』を選択してください");
        } else {
            statusText.setText("画面共有を許可してください");
        }
        startActivityForResult(createSingleAppPreferredCaptureIntent(), REQUEST_CAPTURE);
    }
''',
    "capture picker status",
)

replace_once(
    '''        startForegroundService(serviceIntent);
        statusText.setText("表示モード × 解像度の組み合わせで開始しました");
''',
    '''        startForegroundService(serviceIntent);
        statusText.setText("MediaProjection高速キャプチャで開始しました");
''',
    "capture started status",
)

path.write_text(text)
