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


# MainActivity: keep the existing image-only path as the default (OFF) and add
# one explicit UI switch that enables Accessibility text extraction + 8x8 redraw.
main = read("MainActivity.java")
main = replace_once(
    main,
    "    private boolean uiDither = true;\n    private boolean pendingStartAfterAccessibility = false;\n",
    "    private boolean uiDither = true;\n"
    "    private boolean uiTextRecognitionEnabled = false;\n"
    "    private boolean pendingStartAfterAccessibility = false;\n",
    "text route state field",
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
        Switch textRecognitionSwitch = new Switch(this);
        textRecognitionSwitch.setText("文字認識ルート\nOFF: 既存ルート / ON: 文字取得→8×8再描画");
        textRecognitionSwitch.setTextSize(13f);
        textRecognitionSwitch.setChecked(uiTextRecognitionEnabled);
        textRecognitionSwitch.setPadding(dp(16), dp(28), dp(16), dp(8));
        textRecognitionSwitch.setContentDescription("文字認識ルート切替。オフは既存画像フィルター、オンは文字認識と8×8再描画");
        textRecognitionSwitch.setOnCheckedChangeListener((buttonView, checked) -> {
            uiTextRecognitionEnabled = checked;
            setUiStatus(checked
                    ? "文字認識ルート: ON（文字取得→8×8再描画）"
                    : "文字認識ルート: OFF（既存画像フィルター）");
        });
        routeRoot.addView(
                textRecognitionSwitch,
                new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT
                )
        );
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
    "text route UI switch",
)
main = replace_once(
    main,
    '''            accessibilityService.startWindowFilter(
                    getSelectedMode(),
                    getSelectedResolution(),
                    getBrightness(),
                    getContrast(),
                    isUiDitherEnabled()
            );
''',
    '''            accessibilityService.startWindowFilter(
                    getSelectedMode(),
                    getSelectedResolution(),
                    getBrightness(),
                    getContrast(),
                    isUiDitherEnabled(),
                    isUiTextRecognitionEnabled()
            );
''',
    "accessibility route flag",
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
    "media projection route flag",
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


# Android 14+ accessibility-window path: run text extraction after the normal
# image filter and before the overlay is posted. OFF therefore remains exactly
# the existing image-only processing route.
accessibility = read("FilterAccessibilityService.java")
accessibility = replace_once(
    accessibility,
    "    private boolean windowFilterDither = true;\n    private long performanceFrameIndex = 0L;\n",
    "    private boolean windowFilterDither = true;\n"
    "    private boolean windowTextRecognitionEnabled = false;\n"
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
        windowFilterRunning = true;
''',
    '''        windowFilterContrast = contrast;
        windowFilterDither = dither;
        windowTextRecognitionEnabled = textRecognitionEnabled;
        windowFilterRunning = true;
''',
    "accessibility route assignment",
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
    "accessibility route frame log",
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


# MediaProjection path: the same UI switch controls the pre-existing font_min /
# Misaki text replacement so OFF consistently means image-only on every OS path.
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

print("v0.1.22 selectable text-recognition route applied")
