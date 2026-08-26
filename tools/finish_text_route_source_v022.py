#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_text_route_source_v022.py <generated_src_root>")

root = Path(sys.argv[1])
package = root / "com/sktpj/gbmoder"


def read(name: str) -> str:
    return (package / name).read_text()


def write(name: str, text: str) -> None:
    (package / name).write_text(text)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# MainActivity: expose the generated v0.1.16 MediaProjection route and the
# Android 14+ Accessibility-window route as an explicit UI choice. Text
# recognition/redraw is independently switchable and defaults OFF.
main = read("MainActivity.java")
main = replace_once(
    main,
    "    private boolean uiDither = true;\n    private boolean pendingStartAfterAccessibility = false;\n",
    "    private boolean uiDither = true;\n"
    "    private int uiCaptureRoutePosition = 0;\n"
    "    private boolean uiTextRecognitionEnabled = false;\n"
    "    private boolean pendingStartAfterAccessibility = false;\n",
    "route state fields",
)
main = replace_once(
    main,
    "        setContentView(GbModerComposeUi.createView(this, composeUiState, new GbModerUiActions() {\n",
    "        View composeView = GbModerComposeUi.createView(this, composeUiState, new GbModerUiActions() {\n",
    "compose view capture",
)
main = replace_once(
    main,
    '''            @Override
            public void onAccessibilitySetup() {
                pendingStartAfterAccessibility = false;
                startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
                setUiStatus("ユーザー補助で「GBModer screen filter」を有効にしてください");
            }
        }));
    }

    private View buildContentView() {
''',
    '''            @Override
            public void onAccessibilitySetup() {
                pendingStartAfterAccessibility = false;
                startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
                setUiStatus("ユーザー補助で「GBModer screen filter」を有効にしてください");
            }
        });

        LinearLayout routeRoot = new LinearLayout(this);
        routeRoot.setOrientation(LinearLayout.VERTICAL);
        routeRoot.setPadding(dp(12), dp(20), dp(12), 0);

        TextView routeLabel = text("処理ルート", 13, true);
        routeRoot.addView(routeLabel, matchWrap());

        Spinner captureRouteSpinner = new Spinner(this);
        String[] captureRoutes = {
                "MediaProjection（既存ルート）",
                "Accessibility Window（Android 14+）"
        };
        ArrayAdapter<String> captureRouteAdapter = new ArrayAdapter<>(
                this,
                android.R.layout.simple_spinner_item,
                captureRoutes
        );
        captureRouteAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        captureRouteSpinner.setAdapter(captureRouteAdapter);
        captureRouteSpinner.setSelection(uiCaptureRoutePosition);
        captureRouteSpinner.setContentDescription("画面処理ルート選択");
        captureRouteSpinner.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(android.widget.AdapterView<?> parent, View view, int position, long id) {
                uiCaptureRoutePosition = position;
            }

            @Override
            public void onNothingSelected(android.widget.AdapterView<?> parent) {
            }
        });
        routeRoot.addView(captureRouteSpinner, matchWrap());

        Switch textRecognitionSwitch = new Switch(this);
        textRecognitionSwitch.setText("文字認識・8×8再描画");
        textRecognitionSwitch.setTextSize(13f);
        textRecognitionSwitch.setChecked(uiTextRecognitionEnabled);
        textRecognitionSwitch.setPadding(0, dp(6), 0, dp(6));
        textRecognitionSwitch.setContentDescription("文字認識と8×8フォント再描画のオンオフ");
        textRecognitionSwitch.setOnCheckedChangeListener((buttonView, checked) -> {
            uiTextRecognitionEnabled = checked;
            setUiStatus(checked
                    ? "文字認識・8×8再描画: ON"
                    : "文字認識・8×8再描画: OFF");
        });
        routeRoot.addView(textRecognitionSwitch, matchWrap());
        routeRoot.addView(
                composeView,
                new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        0,
                        1f
                )
        );
        setContentView(routeRoot);
    }

    private View buildContentView() {
''',
    "route selection UI",
)
main = replace_once(
    main,
    '''    private void startFilterForCurrentPlatform() {
        pendingStartAfterAccessibility = false;

        FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
        if (accessibilityService == null) {
            setUiStatus("ユーザー補助サービスに接続できません");
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
    '''    private void startFilterForCurrentPlatform() {
        pendingStartAfterAccessibility = false;

        FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
        if (accessibilityService == null) {
            setUiStatus("ユーザー補助サービスに接続できません");
            return;
        }

        if (uiCaptureRoutePosition == 1) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                setUiStatus("Accessibility WindowルートはAndroid 14以降が必要です");
                return;
            }
            accessibilityService.startWindowFilter(
                    getSelectedMode(),
                    getSelectedResolution(),
                    getBrightness(),
                    getContrast(),
                    isUiDitherEnabled(),
                    isUiTextRecognitionEnabled()
            );
            setUiRunning(true);
            setUiStatus("Accessibility Windowルートで開始しました");
            return;
        }

        accessibilityService.stopWindowFilter();
        accessibilityService.clearOverlay();
        requestScreenCapture();
    }
''',
    "selectable capture routing",
)
main = replace_once(
    main,
    '''        serviceIntent.putExtra(FilterCaptureService.EXTRA_DITHER, isUiDitherEnabled());
        startForegroundService(serviceIntent);
''',
    '''        serviceIntent.putExtra(FilterCaptureService.EXTRA_DITHER, isUiDitherEnabled());
        serviceIntent.putExtra(
                FilterCaptureService.EXTRA_TEXT_RECOGNITION_ENABLED,
                isUiTextRecognitionEnabled()
        );
        startForegroundService(serviceIntent);
''',
    "media projection text flag",
)
main = replace_once(
    main,
    '''    private boolean isUiDitherEnabled() {
        return uiDither;
    }

    private void setUiStatus(String value) {
''',
    '''    private boolean isUiDitherEnabled() {
        return uiDither;
    }

    private boolean isUiTextRecognitionEnabled() {
        return uiTextRecognitionEnabled;
    }

    private void setUiStatus(String value) {
''',
    "text route getter",
)
write("MainActivity.java", main)


# Accessibility-window path. When text recognition is ON, force the CPU path
# because the GPU hardware path filters directly at draw time and cannot apply
# the logical font_min/Misaki text plane before presentation.
accessibility = read("FilterAccessibilityService.java")
accessibility = replace_once(
    accessibility,
    "    private boolean windowFilterDither = true;\n"
    "    private boolean gpuWindowPathDisabled = false;\n"
    "    private long performanceFrameIndex = 0L;\n",
    "    private boolean windowFilterDither = true;\n"
    "    private boolean windowTextRecognitionEnabled = false;\n"
    "    private boolean gpuWindowPathDisabled = false;\n"
    "    private long performanceFrameIndex = 0L;\n",
    "accessibility route field",
)
accessibility = replace_once(
    accessibility,
    '''    public void startWindowFilter(
            String mode,
            String resolution,
            int brightness,
            int contrast,
            boolean dither
    ) {
''',
    '''    public void startWindowFilter(
            String mode,
            String resolution,
            int brightness,
            int contrast,
            boolean dither,
            boolean textRecognitionEnabled
    ) {
''',
    "accessibility start signature",
)
accessibility = replace_once(
    accessibility,
    '''        windowFilterContrast = contrast;
        windowFilterDither = dither;
        gpuWindowPathDisabled = false;
        windowFilterRunning = true;
''',
    '''        windowFilterContrast = contrast;
        windowFilterDither = dither;
        windowTextRecognitionEnabled = textRecognitionEnabled;
        gpuWindowPathDisabled = false;
        windowFilterRunning = true;
''',
    "accessibility route assignment",
)
accessibility = replace_once(
    accessibility,
    '''        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && !gpuWindowPathDisabled
                && !GameBoyFilter.MODE_GBC.equals(windowFilterMode);
''',
    '''        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && !windowTextRecognitionEnabled
                && !gpuWindowPathDisabled
                && !GameBoyFilter.MODE_GBC.equals(windowFilterMode);
''',
    "disable gpu path during text redraw",
)
accessibility = replace_once(
    accessibility,
    '''                + " contrast=" + windowFilterContrast
                + " dither=" + windowFilterDither
                + " source=takeScreenshotOfWindow");
''',
    '''                + " contrast=" + windowFilterContrast
                + " dither=" + windowFilterDither
                + " textRecognition=" + windowTextRecognitionEnabled
                + " source=takeScreenshotOfWindow");
''',
    "accessibility start log route",
)
accessibility = replace_once(
    accessibility,
    '''                                                + " mode=" + windowFilterMode
                                                + " resolution=" + windowFilterResolution
                                                + " source=" + sourceWidth + "x" + sourceHeight
''',
    '''                                                + " mode=" + windowFilterMode
                                                + " resolution=" + windowFilterResolution
                                                + " text_recognition_enabled=" + windowTextRecognitionEnabled
                                                + " source=" + sourceWidth + "x" + sourceHeight
''',
    "gpu route frame log",
)
accessibility = replace_once(
    accessibility,
    '''            long filterFinishedNs = SystemClock.elapsedRealtimeNanos();

            Bitmap frame = lowResolutionBitmap;
''',
    '''            long filterFinishedNs = SystemClock.elapsedRealtimeNanos();

            long fontMinStartedNs = SystemClock.elapsedRealtimeNanos();
            int fontMinNodes = 0;
            if (windowTextRecognitionEnabled
                    && GameBoyFilter.MODE_GB.equals(windowFilterMode)
                    && GameBoyFilter.RESOLUTION_GB.equals(windowFilterResolution)
                    && targetWidth == FontMinRenderer.SCREEN_WIDTH
                    && targetHeight == FontMinRenderer.SCREEN_HEIGHT) {
                fontMinNodes = applyFontMinTextOverlay(lowResolutionBitmap);
            }
            long fontMinFinishedNs = SystemClock.elapsedRealtimeNanos();

            Bitmap frame = lowResolutionBitmap;
''',
    "accessibility text processing",
)
accessibility = replace_once(
    accessibility,
    '''            long downsampleNs = downsampleFinishedNs - downsampleStartedNs;
            long filterNs = filterFinishedNs - filterStartedNs;

            mainHandler.post(() -> {
''',
    '''            long downsampleNs = downsampleFinishedNs - downsampleStartedNs;
            long filterNs = filterFinishedNs - filterStartedNs;
            long fontMinNs = fontMinFinishedNs - fontMinStartedNs;
            int fontMinNodeCount = fontMinNodes;
            boolean textRecognitionEnabled = windowTextRecognitionEnabled;

            mainHandler.post(() -> {
''',
    "accessibility text metrics",
)
accessibility = replace_once(
    accessibility,
    '''                                + " mode=" + windowFilterMode
                                + " resolution=" + windowFilterResolution
                                + " source=" + sourceWidth + "x" + sourceHeight
''',
    '''                                + " mode=" + windowFilterMode
                                + " resolution=" + windowFilterResolution
                                + " text_recognition_enabled=" + textRecognitionEnabled
                                + " source=" + sourceWidth + "x" + sourceHeight
''',
    "cpu route frame log",
)
accessibility = replace_once(
    accessibility,
    '''                                + " downsample_ms=" + PerformanceLog.formatMs(downsampleNs)
                                + " filter_ms=" + PerformanceLog.formatMs(filterNs)
                                + " main_queue_ms=" + PerformanceLog.formatMs(mainQueueNs)
''',
    '''                                + " downsample_ms=" + PerformanceLog.formatMs(downsampleNs)
                                + " filter_ms=" + PerformanceLog.formatMs(filterNs)
                                + " font_min_ms=" + PerformanceLog.formatMs(fontMinNs)
                                + " font_min_nodes=" + fontMinNodeCount
                                + " main_queue_ms=" + PerformanceLog.formatMs(mainQueueNs)
''',
    "accessibility text timing log",
)
write("FilterAccessibilityService.java", accessibility)


# Existing MediaProjection path: use the same independent text switch.
capture = read("FilterCaptureService.java")
capture = replace_once(
    capture,
    '''    public static final String EXTRA_DITHER = "dither";
''',
    '''    public static final String EXTRA_DITHER = "dither";
    public static final String EXTRA_TEXT_RECOGNITION_ENABLED = "text_recognition_enabled";
''',
    "capture route extra",
)
capture = replace_once(
    capture,
    '''    private boolean dither = true;
    private long lastFrameNanos = 0L;
''',
    '''    private boolean dither = true;
    private boolean textRecognitionEnabled = false;
    private long lastFrameNanos = 0L;
''',
    "capture route field",
)
capture = replace_once(
    capture,
    '''        dither = intent.getBooleanExtra(EXTRA_DITHER, true);

        PerformanceLog.startSession(
''',
    '''        dither = intent.getBooleanExtra(EXTRA_DITHER, true);
        textRecognitionEnabled = intent.getBooleanExtra(EXTRA_TEXT_RECOGNITION_ENABLED, false);

        PerformanceLog.startSession(
''',
    "capture route assignment",
)
capture = replace_once(
    capture,
    '''            if (GameBoyFilter.MODE_GB.equals(mode)
                    && GameBoyFilter.RESOLUTION_GB.equals(resolution)
''',
    '''            if (textRecognitionEnabled
                    && GameBoyFilter.MODE_GB.equals(mode)
                    && GameBoyFilter.RESOLUTION_GB.equals(resolution)
''',
    "capture text route gate",
)
capture = replace_once(
    capture,
    '''                                    + " mode=" + mode
                                    + " resolution=" + resolution
                                    + " source=" + sourceWidth + "x" + sourceHeight
''',
    '''                                    + " mode=" + mode
                                    + " resolution=" + resolution
                                    + " text_recognition_enabled=" + textRecognitionEnabled
                                    + " source=" + sourceWidth + "x" + sourceHeight
''',
    "capture route frame log",
)
write("FilterCaptureService.java", capture)

print("v0.1.22 selectable capture and text-recognition routes applied")
