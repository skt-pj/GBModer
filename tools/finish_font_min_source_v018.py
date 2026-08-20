#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_font_min_source_v018.py <generated_src_root>")

root = Path(sys.argv[1])
package = root / "com/sktpj/gbmoder"


def read(path_name: str) -> str:
    return (package / path_name).read_text()


def write(path_name: str, text: str) -> None:
    (package / path_name).write_text(text)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f"{label}: start marker missing")
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit(f"{label}: end marker missing")
    return text[:start] + replacement + text[end:]


# Extend the canonical renderer with a reusable logical-plane API. The method
# still performs the exact same strict ASCII/pre-validation and writes only
# Tile Color Index 0/3 into a 160x144 uint8-equivalent byte array.
renderer = read("FontMinRenderer.java")
renderer_methods = r'''    public static boolean canRenderText(CharSequence text, int lineOriginX, int startTileY) {
        byte[] input = strictAscii(text);
        if (input == null) {
            return false;
        }
        try {
            validate(input, lineOriginX, startTileY);
            return true;
        } catch (IllegalArgumentException error) {
            return false;
        }
    }

    public static int getTextTileWidth(CharSequence text) {
        byte[] input = strictAscii(text);
        if (input == null) {
            return -1;
        }
        int maxWidth = 0;
        int width = 0;
        for (byte value : input) {
            if ((value & 0xFF) == 0x0A) {
                maxWidth = Math.max(maxWidth, width);
                width = 0;
            } else {
                width++;
            }
        }
        return Math.max(maxWidth, width);
    }

    public static int getTextTileHeight(CharSequence text) {
        byte[] input = strictAscii(text);
        if (input == null) {
            return -1;
        }
        int rows = 1;
        for (byte value : input) {
            if ((value & 0xFF) == 0x0A) {
                rows++;
            }
        }
        return rows;
    }

    /**
     * Draws into an existing canonical 160x144 logical framebuffer.
     * Validation completes before the first pixel is touched, so an invalid run
     * never leaves a partial logical result.
     */
    public static boolean drawLogicalText(
            byte[] framebuffer,
            CharSequence text,
            int lineOriginX,
            int startTileY
    ) {
        if (framebuffer == null || framebuffer.length != SCREEN_WIDTH * SCREEN_HEIGHT) {
            return false;
        }
        byte[] input = strictAscii(text);
        if (input == null) {
            return false;
        }
        try {
            validate(input, lineOriginX, startTileY);
        } catch (IllegalArgumentException error) {
            return false;
        }

        int tileX = lineOriginX;
        int tileY = startTileY;
        for (byte value : input) {
            int unsigned = value & 0xFF;
            if (unsigned == 0x0A) {
                tileX = lineOriginX;
                tileY++;
                continue;
            }
            int tileIndex = MAPPING[unsigned] & 0xFF;
            drawLogicalGlyph(framebuffer, tileIndex, tileX, tileY);
            tileX++;
        }
        return true;
    }

'''
renderer = replace_once(
    renderer,
    "    public static boolean verifyReferenceVector() {\n",
    renderer_methods + "    public static boolean verifyReferenceVector() {\n",
    "logical text-plane API",
)
write("FontMinRenderer.java", renderer)


# Replace the v0.1.17 direct ARGB glyph overlay with a logical Tile Color Index
# text plane. All renderable Accessibility text bounds are erased first, then
# font_min is drawn, preventing remnants of the original Android font.
accessibility = read("FilterAccessibilityService.java")
accessibility = replace_once(
    accessibility,
    "import java.util.HashSet;\n",
    "import java.util.ArrayList;\nimport java.util.HashSet;\n",
    "font_min v018 imports",
)

font_methods = r'''    /**
     * Builds a canonical 160x144 Tile Color Index text plane from visible ASCII
     * Accessibility text, masks the original Android glyph bounds, and finally
     * converts indices 0/3 to the configured DMG display colors.
     *
     * The Android node-to-tile placement is an integration rule outside the
     * canonical font_min vector: each complete run is centered in its source
     * node bounds and shifted only as needed to fit the 20x18 visible tile area.
     * There is no automatic wrapping or truncation.
     */
    public int applyFontMinTextOverlay(Bitmap bitmap) {
        if (bitmap == null || bitmap.isRecycled()
                || bitmap.getWidth() != FontMinRenderer.SCREEN_WIDTH
                || bitmap.getHeight() != FontMinRenderer.SCREEN_HEIGHT) {
            return 0;
        }

        AccessibilityWindowInfo targetWindow = resolveFontMinTextWindow();
        if (targetWindow == null) {
            return 0;
        }

        AccessibilityNodeInfo root = null;
        try {
            root = targetWindow.getRoot();
            if (root == null) {
                return 0;
            }

            Rect windowBounds = new Rect();
            targetWindow.getBoundsInScreen(windowBounds);
            if (windowBounds.isEmpty()) {
                return 0;
            }

            ArrayList<FontMinRun> runs = new ArrayList<>();
            Set<String> seen = new HashSet<>();
            collectFontMinRuns(root, windowBounds, runs, seen);
            if (runs.isEmpty()) {
                return 0;
            }

            // Do not touch the Bitmap until every candidate run has already been
            // validated. This preserves the no-partial-frame rule at the visible
            // output boundary.
            byte[] textIndices = new byte[FontMinRenderer.SCREEN_WIDTH * FontMinRenderer.SCREEN_HEIGHT];
            byte[] textCoverage = new byte[FontMinRenderer.SCREEN_WIDTH * FontMinRenderer.SCREEN_HEIGHT];

            for (FontMinRun run : runs) {
                markLogicalRect(textIndices, textCoverage, run.maskBounds);
                markLogicalTileRun(textIndices, textCoverage, run);
            }

            for (FontMinRun run : runs) {
                if (!FontMinRenderer.drawLogicalText(
                        textIndices,
                        run.text,
                        run.tileX,
                        run.tileY
                )) {
                    Log.w(TAG, "font_min run failed after pre-validation; preserving source frame");
                    return 0;
                }
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

            bitmap.setPixels(
                    pixels,
                    0,
                    FontMinRenderer.SCREEN_WIDTH,
                    0,
                    0,
                    FontMinRenderer.SCREEN_WIDTH,
                    FontMinRenderer.SCREEN_HEIGHT
            );
            return runs.size();
        } catch (Throwable error) {
            Log.w(TAG, "font_min accessibility text rendering failed", error);
            return 0;
        } finally {
            if (root != null) {
                root.recycle();
            }
        }
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

    private void collectFontMinRuns(
            AccessibilityNodeInfo node,
            Rect windowBounds,
            ArrayList<FontMinRun> runs,
            Set<String> seen
    ) {
        if (node == null) {
            return;
        }

        if (node.isVisibleToUser()) {
            CharSequence textSequence = node.getText();
            if (textSequence != null && textSequence.length() > 0) {
                String text = textSequence.toString();
                int tileWidth = FontMinRenderer.getTextTileWidth(text);
                int tileHeight = FontMinRenderer.getTextTileHeight(text);

                if (tileWidth > 0
                        && tileWidth <= FontMinRenderer.VISIBLE_TILE_WIDTH
                        && tileHeight > 0
                        && tileHeight <= FontMinRenderer.VISIBLE_TILE_HEIGHT) {
                    Rect screenBounds = new Rect();
                    node.getBoundsInScreen(screenBounds);
                    if (!screenBounds.isEmpty() && Rect.intersects(screenBounds, windowBounds)) {
                        Rect logicalBounds = toLogicalBounds(screenBounds, windowBounds);
                        int runPixelWidth = tileWidth * FontMinRenderer.TILE_SIZE;
                        int runPixelHeight = tileHeight * FontMinRenderer.TILE_SIZE;

                        int preferredLeft = logicalBounds.left
                                + Math.max(0, (logicalBounds.width() - runPixelWidth) / 2);
                        int preferredTop = logicalBounds.top
                                + Math.max(0, (logicalBounds.height() - runPixelHeight) / 2);

                        int tileX = clamp(
                                (preferredLeft + (FontMinRenderer.TILE_SIZE / 2)) / FontMinRenderer.TILE_SIZE,
                                0,
                                FontMinRenderer.VISIBLE_TILE_WIDTH - tileWidth
                        );
                        int tileY = clamp(
                                (preferredTop + (FontMinRenderer.TILE_SIZE / 2)) / FontMinRenderer.TILE_SIZE,
                                0,
                                FontMinRenderer.VISIBLE_TILE_HEIGHT - tileHeight
                        );

                        if (FontMinRenderer.canRenderText(text, tileX, tileY)) {
                            String key = tileX + ":" + tileY + "\u0000" + text;
                            if (seen.add(key)) {
                                runs.add(new FontMinRun(
                                        text,
                                        tileX,
                                        tileY,
                                        tileWidth,
                                        tileHeight,
                                        logicalBounds
                                ));
                            }
                        }
                    }
                }
            }
        }

        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child == null) {
                continue;
            }
            try {
                collectFontMinRuns(child, windowBounds, runs, seen);
            } finally {
                child.recycle();
            }
        }
    }

    private Rect toLogicalBounds(Rect bounds, Rect windowBounds) {
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

        left = clamp(left - 1, 0, FontMinRenderer.SCREEN_WIDTH);
        top = clamp(top - 1, 0, FontMinRenderer.SCREEN_HEIGHT);
        right = clamp(right + 1, left, FontMinRenderer.SCREEN_WIDTH);
        bottom = clamp(bottom + 1, top, FontMinRenderer.SCREEN_HEIGHT);
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

    private void markLogicalTileRun(byte[] indices, byte[] coverage, FontMinRun run) {
        Rect glyphBounds = new Rect(
                run.tileX * FontMinRenderer.TILE_SIZE,
                run.tileY * FontMinRenderer.TILE_SIZE,
                (run.tileX + run.tileWidth) * FontMinRenderer.TILE_SIZE,
                (run.tileY + run.tileHeight) * FontMinRenderer.TILE_SIZE
        );
        markLogicalRect(indices, coverage, glyphBounds);
    }

    private static final class FontMinRun {
        final String text;
        final int tileX;
        final int tileY;
        final int tileWidth;
        final int tileHeight;
        final Rect maskBounds;

        FontMinRun(
                String text,
                int tileX,
                int tileY,
                int tileWidth,
                int tileHeight,
                Rect maskBounds
        ) {
            this.text = text;
            this.tileX = tileX;
            this.tileY = tileY;
            this.tileWidth = tileWidth;
            this.tileHeight = tileHeight;
            this.maskBounds = new Rect(maskBounds);
        }
    }

'''
accessibility = replace_between(
    accessibility,
    "    /**\n     * Replaces visible ASCII Accessibility text with deterministic GBDK font_min\n",
    "    public void prepareProbe() {\n",
    font_methods,
    "font_min v018 accessibility renderer",
)
write("FilterAccessibilityService.java", accessibility)

print("font_min v0.1.18 logical text plane and readability integration applied")
