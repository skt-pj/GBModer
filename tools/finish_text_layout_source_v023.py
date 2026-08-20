#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_text_layout_source_v023.py <generated_src_root>")

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


def replace_font_region(text: str, replacement: str) -> str:
    method = text.find("    public int applyFontMinTextOverlay(Bitmap bitmap) {\n")
    if method < 0:
        raise SystemExit("font overlay method marker missing")
    start = text.rfind("    /**\n", 0, method)
    if start < 0:
        raise SystemExit("font overlay documentation marker missing")
    end = text.find("    public void prepareProbe() {\n", method)
    if end < 0:
        raise SystemExit("font overlay end marker missing")
    return text[:start] + replacement + text[end:]


accessibility = read("FilterAccessibilityService.java")

accessibility = replace_once(
    accessibility,
    "    private boolean windowTextRecognitionEnabled = false;\n"
    "    private boolean gpuWindowPathDisabled = false;\n"
    "    private long performanceFrameIndex = 0L;\n",
    "    private boolean windowTextRecognitionEnabled = false;\n"
    "    private boolean gpuWindowPathDisabled = false;\n"
    "    private long performanceFrameIndex = 0L;\n"
    "    private long contentRevision = 0L;\n",
    "content revision field",
)

accessibility = replace_once(
    accessibility,
    '''    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        updateSystemUiVisibility();
        if (overlayView != null && !windowFilterRunning) {
            updateOverlayBoundsIfNeeded();
        }
    }
''',
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
    "scroll revision handling",
)

accessibility = replace_once(
    accessibility,
    '''        performanceFrameIndex = 0L;

        PerformanceLog.startSession(
''',
    '''        performanceFrameIndex = 0L;
        contentRevision = 0L;

        PerformanceLog.startSession(
''',
    "reset content revision",
)

accessibility = replace_once(
    accessibility,
    '''        screenshotInFlight = true;
        long requestStartedNs = SystemClock.elapsedRealtimeNanos();
''',
    '''        screenshotInFlight = true;
        long requestContentRevision = contentRevision;
        long requestStartedNs = SystemClock.elapsedRealtimeNanos();
''',
    "capture revision snapshot",
)

accessibility = replace_once(
    accessibility,
    '''                        ensureFilterThread();
                        Handler handler = filterHandler;
''',
    '''                        if (windowTextRecognitionEnabled
                                && requestContentRevision != contentRevision) {
                            softwareBitmap.recycle();
                            PerformanceLog.log(
                                    "frame_drop pipeline=accessibility_window"
                                            + " reason=content_revision_before_processing"
                                            + " requested=" + requestContentRevision
                                            + " current=" + contentRevision
                            );
                            scheduleNextWindowCapture(60L);
                            return;
                        }

                        ensureFilterThread();
                        Handler handler = filterHandler;
''',
    "drop stale screenshot before processing",
)

accessibility = replace_once(
    accessibility,
    '''                        handler.post(() -> processWindowScreenshot(
                                softwareBitmap,
                                target,
                                requestStartedNs,
                                screenshotWaitNs,
                                copyNs
                        ));
''',
    '''                        handler.post(() -> processWindowScreenshot(
                                softwareBitmap,
                                target,
                                requestStartedNs,
                                screenshotWaitNs,
                                copyNs,
                                requestContentRevision
                        ));
''',
    "pass content revision to processor",
)

accessibility = replace_once(
    accessibility,
    '''    private void processWindowScreenshot(
            Bitmap source,
            TargetWindow target,
            long requestStartedNs,
            long screenshotWaitNs,
            long copyNs
    ) {
''',
    '''    private void processWindowScreenshot(
            Bitmap source,
            TargetWindow target,
            long requestStartedNs,
            long screenshotWaitNs,
            long copyNs,
            long frameContentRevision
    ) {
''',
    "processor revision signature",
)

accessibility = replace_once(
    accessibility,
    "                fontMinNodes = applyFontMinTextOverlay(lowResolutionBitmap);\n",
    "                fontMinNodes = applyFontMinTextOverlay(lowResolutionBitmap, frameContentRevision);\n",
    "revision-aware text overlay",
)

accessibility = replace_once(
    accessibility,
    '''                if (!windowFilterRunning) {
                    frame.recycle();
                    return;
                }

                long mainStartedNs = SystemClock.elapsedRealtimeNanos();
''',
    '''                if (!windowFilterRunning) {
                    frame.recycle();
                    return;
                }
                if (textRecognitionEnabled && frameContentRevision != contentRevision) {
                    frame.recycle();
                    captureVisible = false;
                    updateOverlayVisibility();
                    PerformanceLog.log(
                            "frame_drop pipeline=accessibility_window"
                                    + " reason=content_revision_before_present"
                                    + " requested=" + frameContentRevision
                                    + " current=" + contentRevision
                    );
                    scheduleNextWindowCapture(60L);
                    return;
                }

                long mainStartedNs = SystemClock.elapsedRealtimeNanos();
''',
    "drop stale frame before presentation",
)

font_region = r'''    /**
     * Replaces visible Accessibility text while preserving the source node's
     * apparent size and aspect on screen. Layout is solved in source-window
     * pixels first, then each 8x8 GB glyph is nearest-neighbour mapped into the
     * canonical 160x144 framebuffer. This avoids treating every Android text run
     * as one fixed 8x8 logical tile regardless of its original size.
     */
    public int applyFontMinTextOverlay(Bitmap bitmap) {
        return applyFontMinTextOverlay(bitmap, contentRevision);
    }

    private int applyFontMinTextOverlay(Bitmap bitmap, long expectedRevision) {
        if (bitmap == null || bitmap.isRecycled()
                || bitmap.getWidth() != FontMinRenderer.SCREEN_WIDTH
                || bitmap.getHeight() != FontMinRenderer.SCREEN_HEIGHT) {
            return 0;
        }
        if (expectedRevision != contentRevision) {
            return 0;
        }

        AccessibilityWindowInfo targetWindow = resolveFontMinTextWindow();
        if (targetWindow == null) {
            return 0;
        }

        AccessibilityNodeInfo root = null;
        try {
            root = targetWindow.getRoot();
            if (root == null || expectedRevision != contentRevision) {
                return 0;
            }

            Rect windowBounds = new Rect();
            targetWindow.getBoundsInScreen(windowBounds);
            if (windowBounds.isEmpty()) {
                return 0;
            }

            ArrayList<ScaledTextRun> runs = new ArrayList<>();
            Set<String> seen = new HashSet<>();
            collectScaledTextRuns(root, windowBounds, runs, seen);
            if (runs.isEmpty() || expectedRevision != contentRevision) {
                return 0;
            }

            byte[] textIndices = new byte[
                    FontMinRenderer.SCREEN_WIDTH * FontMinRenderer.SCREEN_HEIGHT
            ];
            byte[] textCoverage = new byte[textIndices.length];
            byte[] glyphScratch = new byte[textIndices.length];
            int renderedRuns = 0;

            for (ScaledTextRun run : runs) {
                if (expectedRevision != contentRevision) {
                    return 0;
                }

                Rect mask = toLogicalMaskBounds(run.screenBounds, windowBounds);
                if (mask.isEmpty()) {
                    continue;
                }

                // Only erase the original Android glyphs after a replacement layout
                // is known to fit, so failed runs do not create blank rectangles.
                int cellSize = findBestSourceCellSize(
                        run.text,
                        run.screenBounds.width(),
                        run.screenBounds.height()
                );
                if (cellSize <= 0) {
                    continue;
                }

                markLogicalRect(textIndices, textCoverage, mask);
                if (drawScaledRun(
                        textIndices,
                        textCoverage,
                        glyphScratch,
                        run,
                        windowBounds,
                        cellSize
                )) {
                    renderedRuns++;
                }
            }

            if (renderedRuns == 0 || expectedRevision != contentRevision) {
                return 0;
            }

            int[] pixels = new int[FontMinRenderer.SCREEN_WIDTH * FontMinRenderer.SCREEN_HEIGHT];
            bitmap.getPixels(
                    pixels,
                    0,
                    FontMinRenderer.SCREEN_WIDTH,
                    0,
                    0,
                    FontMinRenderer.SCREEN_WIDTH,
                    FontMinRenderer.SCREEN_HEIGHT
            );

            int background = GameBoyFilter.getGameBoyPaletteColor(FontMinRenderer.BACKGROUND_INDEX);
            int foreground = GameBoyFilter.getGameBoyPaletteColor(FontMinRenderer.FOREGROUND_INDEX);
            for (int i = 0; i < pixels.length; i++) {
                if (textCoverage[i] == 0) {
                    continue;
                }
                pixels[i] = (textIndices[i] & 0xFF) == FontMinRenderer.FOREGROUND_INDEX
                        ? foreground
                        : background;
            }

            if (expectedRevision != contentRevision) {
                return 0;
            }
            bitmap.setPixels(
                    pixels,
                    0,
                    FontMinRenderer.SCREEN_WIDTH,
                    0,
                    0,
                    FontMinRenderer.SCREEN_WIDTH,
                    FontMinRenderer.SCREEN_HEIGHT
            );
            return renderedRuns;
        } catch (Throwable error) {
            Log.w(TAG, "scaled accessibility text rendering failed", error);
            return 0;
        } finally {
            if (root != null) {
                root.recycle();
            }
        }
    }

    public long getContentRevision() {
        return contentRevision;
    }

    private AccessibilityWindowInfo resolveFontMinTextWindow() {
        List<AccessibilityWindowInfo> windows = getWindows();
        if (windows == null) {
            return null;
        }

        AccessibilityWindowInfo fallback = null;
        for (AccessibilityWindowInfo window : windows) {
            if (window == null || window.getType() != AccessibilityWindowInfo.TYPE_APPLICATION) {
                continue;
            }

            AccessibilityNodeInfo root = null;
            try {
                root = window.getRoot();
                CharSequence packageSequence = root == null ? null : root.getPackageName();
                String packageName = packageSequence == null ? null : packageSequence.toString();
                if (getPackageName().equals(packageName) || SYSTEM_UI_PACKAGE.equals(packageName)) {
                    continue;
                }
                Rect bounds = new Rect();
                window.getBoundsInScreen(bounds);
                if (bounds.isEmpty()) {
                    continue;
                }
                if (window.isActive() || window.isFocused()) {
                    return window;
                }
                if (fallback == null) {
                    fallback = window;
                }
            } finally {
                if (root != null) {
                    root.recycle();
                }
            }
        }
        return fallback;
    }

    private void collectScaledTextRuns(
            AccessibilityNodeInfo node,
            Rect windowBounds,
            ArrayList<ScaledTextRun> runs,
            Set<String> seen
    ) {
        if (node == null) {
            return;
        }

        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child == null) {
                continue;
            }
            try {
                collectScaledTextRuns(child, windowBounds, runs, seen);
            } finally {
                child.recycle();
            }
        }

        if (!node.isVisibleToUser() || hasDirectVisibleTextChild(node)) {
            return;
        }

        CharSequence textSequence = node.getText();
        if (textSequence == null || textSequence.length() == 0) {
            return;
        }

        String text = normalizeAccessibilityText(textSequence.toString());
        if (text.isEmpty()) {
            return;
        }

        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);
        if (bounds.isEmpty() || !Rect.intersects(bounds, windowBounds)) {
            return;
        }
        if (!bounds.intersect(windowBounds) || bounds.width() <= 1 || bounds.height() <= 1) {
            return;
        }

        String key = bounds.flattenToString() + "\u0000" + text;
        if (seen.add(key)) {
            runs.add(new ScaledTextRun(text, bounds));
        }
    }

    private boolean hasDirectVisibleTextChild(AccessibilityNodeInfo node) {
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child == null) {
                continue;
            }
            try {
                CharSequence childText = child.getText();
                if (child.isVisibleToUser() && childText != null && childText.length() > 0) {
                    return true;
                }
            } finally {
                child.recycle();
            }
        }
        return false;
    }

    private String normalizeAccessibilityText(String text) {
        if (text == null || text.isEmpty()) {
            return "";
        }
        StringBuilder result = new StringBuilder(text.length());
        boolean previousSpace = false;
        for (int i = 0; i < text.length();) {
            int codePoint = Character.codePointAt(text, i);
            i += Character.charCount(codePoint);
            if (codePoint == '\r') {
                continue;
            }
            if (codePoint == '\t' || codePoint == 0x00A0) {
                codePoint = ' ';
            }
            if (codePoint == ' ') {
                if (previousSpace) {
                    continue;
                }
                previousSpace = true;
            } else {
                previousSpace = false;
            }
            result.appendCodePoint(codePoint);
        }
        return result.toString().trim();
    }

    private int findBestSourceCellSize(String text, int width, int height) {
        if (text == null || text.isEmpty() || width <= 0 || height <= 0) {
            return -1;
        }
        int maxCell = Math.max(1, Math.min(width, height));
        for (int cell = maxCell; cell >= 1; cell--) {
            int columns = Math.max(1, width / cell);
            int rows = wrappedRowCount(text, columns);
            if (rows > 0 && ((long) rows * cell) <= height) {
                return cell;
            }
        }
        return -1;
    }

    private int wrappedRowCount(String text, int columns) {
        if (columns <= 0) {
            return Integer.MAX_VALUE;
        }
        int rows = 1;
        int column = 0;
        for (int i = 0; i < text.length();) {
            int codePoint = Character.codePointAt(text, i);
            i += Character.charCount(codePoint);
            if (codePoint == '\n') {
                rows++;
                column = 0;
                continue;
            }
            if (column >= columns) {
                rows++;
                column = 0;
            }
            column++;
        }
        return rows;
    }

    private boolean drawScaledRun(
            byte[] indices,
            byte[] coverage,
            byte[] glyphScratch,
            ScaledTextRun run,
            Rect windowBounds,
            int cellSize
    ) {
        int columns = Math.max(1, run.screenBounds.width() / cellSize);
        int rows = wrappedRowCount(run.text, columns);
        if (rows <= 0 || ((long) rows * cellSize) > run.screenBounds.height()) {
            return false;
        }

        int startY = run.screenBounds.top
                + Math.max(0, (run.screenBounds.height() - (rows * cellSize)) / 2);
        int row = 0;
        int column = 0;
        boolean drewAny = false;

        for (int i = 0; i < run.text.length();) {
            int codePoint = Character.codePointAt(run.text, i);
            i += Character.charCount(codePoint);

            if (codePoint == '\n') {
                row++;
                column = 0;
                continue;
            }
            if (column >= columns) {
                row++;
                column = 0;
            }
            if (row >= rows) {
                break;
            }

            int sourceLeft = run.screenBounds.left + (column * cellSize);
            int sourceTop = startY + (row * cellSize);
            Rect sourceCell = new Rect(
                    sourceLeft,
                    sourceTop,
                    Math.min(run.screenBounds.right, sourceLeft + cellSize),
                    Math.min(run.screenBounds.bottom, sourceTop + cellSize)
            );
            Rect logicalCell = toLogicalGlyphBounds(sourceCell, windowBounds);
            if (!logicalCell.isEmpty()
                    && drawScaledGlyph(indices, glyphScratch, codePoint, logicalCell)) {
                drewAny = true;
            }
            column++;
        }
        return drewAny;
    }

    private boolean drawScaledGlyph(
            byte[] indices,
            byte[] glyphScratch,
            int codePoint,
            Rect logicalCell
    ) {
        boolean drawn;
        if (codePoint >= 0 && codePoint <= 0x7F) {
            drawn = FontMinRenderer.drawLogicalAsciiGlyph(glyphScratch, codePoint, 0, 0);
        } else {
            drawn = JapaneseFont8x8.drawLogicalGlyph(glyphScratch, codePoint, 0, 0);
        }
        if (!drawn) {
            return false;
        }

        int width = logicalCell.width();
        int height = logicalCell.height();
        if (width <= 0 || height <= 0) {
            return false;
        }
        for (int y = logicalCell.top; y < logicalCell.bottom; y++) {
            int sourceY = Math.min(7, ((y - logicalCell.top) * 8) / height);
            int destinationOffset = y * FontMinRenderer.SCREEN_WIDTH;
            int sourceOffset = sourceY * FontMinRenderer.SCREEN_WIDTH;
            for (int x = logicalCell.left; x < logicalCell.right; x++) {
                int sourceX = Math.min(7, ((x - logicalCell.left) * 8) / width);
                indices[destinationOffset + x] = glyphScratch[sourceOffset + sourceX];
            }
        }
        return true;
    }

    private Rect toLogicalMaskBounds(Rect bounds, Rect windowBounds) {
        Rect logical = mapScreenRectToLogical(bounds, windowBounds);
        logical.left = clamp(logical.left - 1, 0, FontMinRenderer.SCREEN_WIDTH);
        logical.top = clamp(logical.top - 1, 0, FontMinRenderer.SCREEN_HEIGHT);
        logical.right = clamp(logical.right + 1, logical.left, FontMinRenderer.SCREEN_WIDTH);
        logical.bottom = clamp(logical.bottom + 1, logical.top, FontMinRenderer.SCREEN_HEIGHT);
        return logical;
    }

    private Rect toLogicalGlyphBounds(Rect bounds, Rect windowBounds) {
        return mapScreenRectToLogical(bounds, windowBounds);
    }

    private Rect mapScreenRectToLogical(Rect bounds, Rect windowBounds) {
        int windowWidth = Math.max(1, windowBounds.width());
        int windowHeight = Math.max(1, windowBounds.height());

        int relativeLeft = clamp(bounds.left - windowBounds.left, 0, windowWidth);
        int relativeTop = clamp(bounds.top - windowBounds.top, 0, windowHeight);
        int relativeRight = clamp(bounds.right - windowBounds.left, relativeLeft, windowWidth);
        int relativeBottom = clamp(bounds.bottom - windowBounds.top, relativeTop, windowHeight);

        int left = (int) (((long) relativeLeft * FontMinRenderer.SCREEN_WIDTH) / windowWidth);
        int top = (int) (((long) relativeTop * FontMinRenderer.SCREEN_HEIGHT) / windowHeight);
        int right = (int) ((((long) relativeRight * FontMinRenderer.SCREEN_WIDTH) + windowWidth - 1L)
                / windowWidth);
        int bottom = (int) ((((long) relativeBottom * FontMinRenderer.SCREEN_HEIGHT) + windowHeight - 1L)
                / windowHeight);

        left = clamp(left, 0, FontMinRenderer.SCREEN_WIDTH);
        top = clamp(top, 0, FontMinRenderer.SCREEN_HEIGHT);
        right = clamp(right, left, FontMinRenderer.SCREEN_WIDTH);
        bottom = clamp(bottom, top, FontMinRenderer.SCREEN_HEIGHT);
        return new Rect(left, top, right, bottom);
    }

    private void markLogicalRect(byte[] indices, byte[] coverage, Rect rect) {
        int left = clamp(rect.left, 0, FontMinRenderer.SCREEN_WIDTH);
        int top = clamp(rect.top, 0, FontMinRenderer.SCREEN_HEIGHT);
        int right = clamp(rect.right, left, FontMinRenderer.SCREEN_WIDTH);
        int bottom = clamp(rect.bottom, top, FontMinRenderer.SCREEN_HEIGHT);
        for (int y = top; y < bottom; y++) {
            int offset = y * FontMinRenderer.SCREEN_WIDTH;
            for (int x = left; x < right; x++) {
                int index = offset + x;
                indices[index] = (byte) FontMinRenderer.BACKGROUND_INDEX;
                coverage[index] = 1;
            }
        }
    }

    private static final class ScaledTextRun {
        final String text;
        final Rect screenBounds;

        ScaledTextRun(String text, Rect screenBounds) {
            this.text = text;
            this.screenBounds = new Rect(screenBounds);
        }
    }

'''

accessibility = replace_font_region(accessibility, font_region)
write("FilterAccessibilityService.java", accessibility)

print("v0.1.23 proportional text layout and stale-scroll frame rejection applied")
