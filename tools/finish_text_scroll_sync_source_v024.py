#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_text_scroll_sync_source_v024.py <generated_src_root>")

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


# Accessibility service: subscribe to actual scroll/content events, invalidate any
# text-bearing overlay for BOTH capture routes, and expose a revision gate that
# MediaProjection can use around Accessibility text replacement.
accessibility = read("FilterAccessibilityService.java")
accessibility = replace_once(
    accessibility,
    "import android.accessibilityservice.AccessibilityService;\n",
    "import android.accessibilityservice.AccessibilityService;\n"
    "import android.accessibilityservice.AccessibilityServiceInfo;\n",
    "accessibility service info import",
)
accessibility = replace_once(
    accessibility,
    "    private boolean windowTextRecognitionEnabled = false;\n"
    "    private boolean gpuWindowPathDisabled = false;\n"
    "    private long performanceFrameIndex = 0L;\n"
    "    private long contentRevision = 0L;\n",
    "    private boolean windowTextRecognitionEnabled = false;\n"
    "    private boolean gpuWindowPathDisabled = false;\n"
    "    private long performanceFrameIndex = 0L;\n"
    "    private volatile long contentRevision = 0L;\n"
    "    private volatile long lastContentMutationUptimeMs = 0L;\n"
    "    private volatile boolean externalTextRecognitionActive = false;\n",
    "text sync state fields",
)
accessibility = replace_once(
    accessibility,
    '''    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        createNotificationChannel();
        Log.i(TAG, "Accessibility overlay service connected");
    }
''',
    '''    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        configureTextSyncEvents();
        createNotificationChannel();
        Log.i(TAG, "Accessibility overlay service connected");
    }

    private void configureTextSyncEvents() {
        AccessibilityServiceInfo info = getServiceInfo();
        if (info == null) {
            return;
        }
        int required = AccessibilityEvent.TYPE_VIEW_SCROLLED
                | AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED
                | AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED
                | AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
                | AccessibilityEvent.TYPE_WINDOWS_CHANGED;
        if ((info.eventTypes & required) != required) {
            info.eventTypes |= required;
            setServiceInfo(info);
        }
    }
''',
    "runtime accessibility event subscription",
)
accessibility = replace_once(
    accessibility,
    '''    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        updateSystemUiVisibility();
        if (event != null) {
            int eventType = event.getEventType();
            if (eventType == AccessibilityEvent.TYPE_VIEW_SCROLLED
                    || eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
                    || eventType == AccessibilityEvent.TYPE_WINDOWS_CHANGED) {
                contentRevision++;

                // Never leave a pre-scroll text frame on top of a post-scroll app state.
                // Hide it immediately and only show a freshly captured matching revision.
                if (windowFilterRunning && windowTextRecognitionEnabled) {
                    captureVisible = false;
                    updateOverlayVisibility();
                    mainHandler.removeCallbacks(captureRunnable);
                    if (!screenshotInFlight) {
                        mainHandler.postDelayed(captureRunnable, 60L);
                    }
                    PerformanceLog.log(
                            "content_revision pipeline=accessibility_window"
                                    + " revision=" + contentRevision
                                    + " event=" + eventType
                    );
                }
            }
        }
        if (overlayView != null && !windowFilterRunning) {
            updateOverlayBoundsIfNeeded();
        }
    }
''',
    '''    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        updateSystemUiVisibility();
        if (event != null && isTargetContentMutationEvent(event)) {
            contentRevision++;
            lastContentMutationUptimeMs = SystemClock.uptimeMillis();

            // A stale filtered frame is worse than briefly revealing the live app.
            // Hide immediately for both Accessibility-window and MediaProjection text modes.
            if (windowTextRecognitionEnabled || externalTextRecognitionActive) {
                captureVisible = false;
                updateOverlayVisibility();

                if (windowFilterRunning) {
                    mainHandler.removeCallbacks(captureRunnable);
                    if (!screenshotInFlight) {
                        mainHandler.postDelayed(captureRunnable, 40L);
                    }
                }

                PerformanceLog.log(
                        "content_revision pipeline="
                                + (windowFilterRunning ? "accessibility_window" : "media_projection")
                                + " revision=" + contentRevision
                                + " event=" + event.getEventType()
                );
            }
        }
        if (overlayView != null && !windowFilterRunning) {
            updateOverlayBoundsIfNeeded();
        }
    }

    private boolean isTargetContentMutationEvent(AccessibilityEvent event) {
        if (event == null) {
            return false;
        }
        CharSequence packageSequence = event.getPackageName();
        String packageName = packageSequence == null ? null : packageSequence.toString();
        if (getPackageName().equals(packageName) || SYSTEM_UI_PACKAGE.equals(packageName)) {
            return false;
        }

        int eventType = event.getEventType();
        return eventType == AccessibilityEvent.TYPE_VIEW_SCROLLED
                || eventType == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED
                || eventType == AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED
                || eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
                || eventType == AccessibilityEvent.TYPE_WINDOWS_CHANGED;
    }
''',
    "cross-route content invalidation",
)
accessibility = replace_once(
    accessibility,
    '''        performanceFrameIndex = 0L;
        contentRevision = 0L;

        PerformanceLog.startSession(
''',
    '''        performanceFrameIndex = 0L;
        contentRevision = 0L;
        lastContentMutationUptimeMs = SystemClock.uptimeMillis();

        PerformanceLog.startSession(
''',
    "window route sync reset",
)
accessibility = replace_once(
    accessibility,
    "    private int applyFontMinTextOverlay(Bitmap bitmap, long expectedRevision) {\n",
    "    public int applyFontMinTextOverlay(Bitmap bitmap, long expectedRevision) {\n",
    "public revision-aware text overlay",
)
accessibility = replace_once(
    accessibility,
    '''    public long getContentRevision() {
        return contentRevision;
    }

    private AccessibilityWindowInfo resolveFontMinTextWindow() {
''',
    '''    public long getContentRevision() {
        return contentRevision;
    }

    public boolean isContentRevisionCurrent(long expectedRevision) {
        return expectedRevision == contentRevision;
    }

    public boolean isTextContentStable(long expectedRevision, long minimumQuietMs) {
        if (expectedRevision != contentRevision) {
            return false;
        }
        long quietMs = Math.max(0L, SystemClock.uptimeMillis() - lastContentMutationUptimeMs);
        return quietMs >= Math.max(0L, minimumQuietMs);
    }

    public void setExternalTextRecognitionActive(boolean active) {
        externalTextRecognitionActive = active;
        if (active) {
            contentRevision++;
            lastContentMutationUptimeMs = SystemClock.uptimeMillis();
            runOnMain(() -> {
                captureVisible = false;
                updateOverlayVisibility();
            });
        }
    }

    private AccessibilityWindowInfo resolveFontMinTextWindow() {
''',
    "media projection text sync API",
)
accessibility = replace_once(
    accessibility,
    '''    public void showFrame(Bitmap frame) {
        runOnMain(() -> {
            ensureOverlay();
            updateOverlayBoundsIfNeeded();
            overlayView.setFrame(frame);
            updateOverlayVisibility();
        });
    }
''',
    '''    public void showFrame(Bitmap frame) {
        runOnMain(() -> {
            ensureOverlay();
            updateOverlayBoundsIfNeeded();
            // Scroll/content invalidation hides the old MediaProjection overlay.
            // Only a newly revision-validated frame reaches this method, so it is
            // safe to make the overlay visible again here.
            captureVisible = true;
            overlayView.setFrame(frame);
            updateOverlayVisibility();
        });
    }
''',
    "fresh media projection frame restores visibility",
)
write("FilterAccessibilityService.java", accessibility)


# MediaProjection route: snapshot the Accessibility revision for each captured
# image. Apply text only after a short quiet period, drop any frame whose revision
# changed before processing/presentation, and arm event-driven overlay hiding.
capture = read("FilterCaptureService.java")
capture = replace_once(
    capture,
    '''        textRecognitionEnabled = intent.getBooleanExtra(EXTRA_TEXT_RECOGNITION_ENABLED, false);

        PerformanceLog.startSession(
''',
    '''        textRecognitionEnabled = intent.getBooleanExtra(EXTRA_TEXT_RECOGNITION_ENABLED, false);
        accessibilityService.setExternalTextRecognitionActive(textRecognitionEnabled);

        PerformanceLog.startSession(
''',
    "arm media projection text invalidation",
)
capture = replace_once(
    capture,
    '''            lastFrameNanos = frameStartedNs;

            Image.Plane plane = image.getPlanes()[0];
''',
    '''            lastFrameNanos = frameStartedNs;

            FilterAccessibilityService frameTextService = FilterAccessibilityService.getInstance();
            long frameContentRevision = frameTextService == null
                    ? -1L
                    : frameTextService.getContentRevision();

            Image.Plane plane = image.getPlanes()[0];
''',
    "snapshot media projection content revision",
)
capture = replace_once(
    capture,
    '''                FilterAccessibilityService textService = FilterAccessibilityService.getInstance();
                if (textService != null) {
                    fontMinNodes = textService.applyFontMinTextOverlay(lowResolutionBitmap);
                }
''',
    '''                FilterAccessibilityService textService = FilterAccessibilityService.getInstance();
                if (textService != null
                        && textService.isTextContentStable(frameContentRevision, 100L)) {
                    fontMinNodes = textService.applyFontMinTextOverlay(
                            lowResolutionBitmap,
                            frameContentRevision
                    );
                }
''',
    "revision-gated media projection text overlay",
)
capture = replace_once(
    capture,
    '''            long fontMinFinishedNs = SystemClock.elapsedRealtimeNanos();

            long frameCopyStartedNs = SystemClock.elapsedRealtimeNanos();
''',
    '''            long fontMinFinishedNs = SystemClock.elapsedRealtimeNanos();

            FilterAccessibilityService syncService = FilterAccessibilityService.getInstance();
            if (textRecognitionEnabled
                    && syncService != null
                    && !syncService.isContentRevisionCurrent(frameContentRevision)) {
                PerformanceLog.log(
                        "frame_drop pipeline=media_projection"
                                + " reason=content_revision_before_copy"
                                + " requested=" + frameContentRevision
                                + " current=" + syncService.getContentRevision()
                );
                return;
            }

            long frameCopyStartedNs = SystemClock.elapsedRealtimeNanos();
''',
    "drop stale media projection frame before copy",
)
capture = replace_once(
    capture,
    '''                FilterAccessibilityService service = FilterAccessibilityService.getInstance();
                if (service != null) {
                    service.showFrame(frameForOverlay);
''',
    '''                FilterAccessibilityService service = FilterAccessibilityService.getInstance();
                if (service != null) {
                    if (textRecognitionEnabled
                            && !service.isContentRevisionCurrent(frameContentRevision)) {
                        frameForOverlay.recycle();
                        PerformanceLog.log(
                                "frame_drop pipeline=media_projection"
                                        + " reason=content_revision_before_present"
                                        + " requested=" + frameContentRevision
                                        + " current=" + service.getContentRevision()
                        );
                        return;
                    }
                    service.showFrame(frameForOverlay);
''',
    "drop stale media projection frame before presentation",
)
capture = replace_once(
    capture,
    '''        FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
        if (accessibilityService != null) {
            accessibilityService.clearOverlay();
        }
''',
    '''        FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
        if (accessibilityService != null) {
            accessibilityService.setExternalTextRecognitionActive(false);
            accessibilityService.clearOverlay();
        }
''',
    "disarm media projection text invalidation",
)
write("FilterCaptureService.java", capture)

print("v0.1.24 cross-route scroll synchronization applied")
