#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_compose_ui_source_v020.py <generated_src_root>")

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
    "import android.view.accessibility.AccessibilityManager;\n",
    "import android.view.accessibility.AccessibilityManager;\nimport androidx.core.view.WindowCompat;\n",
    "window compat import",
)

replace_once(
    "    private TextView statusText;\n    private boolean pendingStartAfterAccessibility = false;\n",
    "    private TextView statusText;\n"
    "    private GbModerUiState composeUiState;\n"
    "    private int uiModePosition = 0;\n"
    "    private int uiResolutionPosition = 0;\n"
    "    private int uiBrightness = 6;\n"
    "    private int uiContrast = 122;\n"
    "    private boolean uiDither = true;\n"
    "    private boolean pendingStartAfterAccessibility = false;\n",
    "compose state fields",
)

replace_once(
    '''    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        projectionManager = (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        setContentView(buildContentView());
    }
''',
    '''    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        projectionManager = (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        WindowCompat.enableEdgeToEdge(getWindow());
        composeUiState = new GbModerUiState();
        composeUiState.setAccessibilityReady(isAccessibilityServiceEnabled());
        setContentView(GbModerComposeUi.createView(this, composeUiState, new GbModerUiActions() {
            @Override
            public void onStart(int modePosition, int resolutionPosition, int brightness, int contrast, boolean dither) {
                uiModePosition = modePosition;
                uiResolutionPosition = resolutionPosition;
                uiBrightness = brightness;
                uiContrast = contrast;
                uiDither = dither;
                beginStartFlow();
            }

            @Override
            public void onStop() {
                stopFilter();
            }

            @Override
            public void onLogSync() {
                beginLogSync();
            }

            @Override
            public void onAdbGuide() {
                showAdbGuide();
            }

            @Override
            public void onAccessibilitySetup() {
                pendingStartAfterAccessibility = false;
                startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
                setUiStatus("ユーザー補助で「GBModer screen filter」を有効にしてください");
            }
        }));
    }
''',
    "compose onCreate",
)

# Generated business logic should never depend on the retired View status TextView.
text = text.replace("statusText.setText(", "setUiStatus(")
text = text.replace("statusText.postDelayed(", "postUiDelayed(")
text = text.replace("ditherSwitch.isChecked()", "isUiDitherEnabled()")

replace_once(
    '''    @Override
    protected void onResume() {
        super.onResume();
        if (pendingStartAfterAccessibility) {
            postUiDelayed(this::continueAfterAccessibilityIfReady, 300L);
        }
    }
''',
    '''    @Override
    protected void onResume() {
        super.onResume();
        if (composeUiState != null) {
            composeUiState.setAccessibilityReady(isAccessibilityServiceEnabled());
        }
        if (pendingStartAfterAccessibility) {
            postUiDelayed(this::continueAfterAccessibilityIfReady, 300L);
        }
    }
''',
    "resume accessibility state",
)

replace_once(
    '''        startForegroundService(serviceIntent);
        setUiStatus("MediaProjection高速キャプチャで開始しました");
''',
    '''        startForegroundService(serviceIntent);
        setUiRunning(true);
        setUiStatus("MediaProjection高速キャプチャで開始しました");
''',
    "running after capture start",
)

replace_once(
    '''        setUiStatus("停止しました");
    }

    private void beginLogSync() {
''',
    '''        setUiRunning(false);
        setUiStatus("停止しました");
    }

    private void beginLogSync() {
''',
    "running false on stop",
)

replace_once(
    '''    private String getSelectedMode() {
        int position = modeSpinner.getSelectedItemPosition();
        if (position == 1) return GameBoyFilter.MODE_GBC;
        if (position == 2) return GameBoyFilter.MODE_GBA;
        if (position == 3) return GameBoyFilter.MODE_DS;
        return GameBoyFilter.MODE_GB;
    }

    private String getSelectedResolution() {
        int position = resolutionSpinner.getSelectedItemPosition();
        if (position == 1) return GameBoyFilter.RESOLUTION_GBC;
        if (position == 2) return GameBoyFilter.RESOLUTION_GBA;
        if (position == 3) return GameBoyFilter.RESOLUTION_DS;
        if (position == 4) return GameBoyFilter.RESOLUTION_PHONE_25;
        if (position == 5) return GameBoyFilter.RESOLUTION_PHONE_33;
        if (position == 6) return GameBoyFilter.RESOLUTION_PHONE_50;
        if (position == 7) return GameBoyFilter.RESOLUTION_PHONE_67;
        if (position == 8) return GameBoyFilter.RESOLUTION_PHONE_75;
        if (position == 9) return GameBoyFilter.RESOLUTION_NATIVE;
        return GameBoyFilter.RESOLUTION_GB;
    }

    private int getBrightness() {
        return brightnessSeek.getProgress() - 80;
    }

    private int getContrast() {
        return contrastSeek.getProgress() + 50;
    }
''',
    '''    private String getSelectedMode() {
        int position = uiModePosition;
        if (position == 1) return GameBoyFilter.MODE_GBC;
        if (position == 2) return GameBoyFilter.MODE_GBA;
        if (position == 3) return GameBoyFilter.MODE_DS;
        return GameBoyFilter.MODE_GB;
    }

    private String getSelectedResolution() {
        int position = uiResolutionPosition;
        if (position == 1) return GameBoyFilter.RESOLUTION_GBC;
        if (position == 2) return GameBoyFilter.RESOLUTION_GBA;
        if (position == 3) return GameBoyFilter.RESOLUTION_DS;
        if (position == 4) return GameBoyFilter.RESOLUTION_PHONE_25;
        if (position == 5) return GameBoyFilter.RESOLUTION_PHONE_33;
        if (position == 6) return GameBoyFilter.RESOLUTION_PHONE_50;
        if (position == 7) return GameBoyFilter.RESOLUTION_PHONE_67;
        if (position == 8) return GameBoyFilter.RESOLUTION_PHONE_75;
        if (position == 9) return GameBoyFilter.RESOLUTION_NATIVE;
        return GameBoyFilter.RESOLUTION_GB;
    }

    private int getBrightness() {
        return uiBrightness;
    }

    private int getContrast() {
        return uiContrast;
    }

    private boolean isUiDitherEnabled() {
        return uiDither;
    }

    private void setUiStatus(String value) {
        if (composeUiState != null) {
            composeUiState.setStatus(value);
        }
        if (statusText != null) {
            statusText.setText(value);
        }
    }

    private void setUiRunning(boolean running) {
        if (composeUiState != null) {
            composeUiState.setRunning(running);
        }
    }

    private void postUiDelayed(Runnable runnable, long delayMillis) {
        View target = statusText != null ? statusText : getWindow().getDecorView();
        target.postDelayed(runnable, delayMillis);
    }
''',
    "compose value getters and helpers",
)

path.write_text(text)
print("Compose UI bridge v0.1.20 applied")
