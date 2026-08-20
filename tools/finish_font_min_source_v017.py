#!/usr/bin/env python3
from pathlib import Path
import hashlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_font_min_source_v017.py <generated_src_root>")

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


def extract_java_hex(source: str, name: str) -> bytes:
    match = re.search(rf"{name}\s*=\s*(.*?);", source, re.S)
    if not match:
        raise SystemExit(f"missing {name}")
    hex_text = "".join(re.findall(r'"([0-9a-f]+)"', match.group(1)))
    return bytes.fromhex(hex_text)


# Verify the exact data embedded into the APK against the supplied canonical vector.
renderer = read("FontMinRenderer.java")
mapping = extract_java_hex(renderer, "MAPPING_HEX")
glyphs = extract_java_hex(renderer, "GLYPHS_HEX")
if len(mapping) != 128:
    raise SystemExit(f"font_min mapping length mismatch: {len(mapping)}")
if len(glyphs) != 37 * 8:
    raise SystemExit(f"font_min glyph length mismatch: {len(glyphs)}")

reference = b"GAME BOY\n0123456789\nABCDEFGHIJ\nKLMNOPQRST\nUVWXYZ"
frame = bytearray(160 * 144)
origin_x = 1
tile_x = origin_x
tile_y = 1

# Pre-validation pass: no partial output on invalid input.
for value in reference:
    if value >= 0x80:
        raise SystemExit("reference contains non-ASCII byte")
    if value == 0x0A:
        tile_x = origin_x
        tile_y += 1
        continue
    if not (0 <= tile_x <= 19) or not (0 <= tile_y <= 17):
        raise SystemExit("reference layout out of range")
    tile_x += 1

tile_x = origin_x
tile_y = 1
for value in reference:
    if value == 0x0A:
        tile_x = origin_x
        tile_y += 1
        continue
    tile_index = mapping[value]
    glyph_base = tile_index * 8
    for row in range(8):
        bits = glyphs[glyph_base + row]
        offset = (tile_y * 8 + row) * 160 + tile_x * 8
        for col in range(8):
            frame[offset + col] = 3 if bits & (0x80 >> col) else 0
    tile_x += 1

foreground = sum(1 for value in frame if value == 3)
digest = hashlib.sha256(frame).hexdigest()
expected_digest = "38bb88a2b5413ed15770d76f77ab45a0def0543d208fa206403e1a3f4a5106c5"
if foreground != 671:
    raise SystemExit(f"font_min foreground mismatch: {foreground}")
if digest != expected_digest:
    raise SystemExit(f"font_min SHA-256 mismatch: {digest}")
print(f"font_min reference verified: fg={foreground} sha256={digest}")

# Expose the DMG display colors for logical indices 0 and 3.
gameboy = read("GameBoyFilter.java")
gameboy = replace_once(
    gameboy,
    '''    private GameBoyFilter() {\n    }\n\n''',
    '''    private GameBoyFilter() {\n    }\n\n    public static int getGameBoyPaletteColor(int colorIndex) {\n        int safeIndex = Math.max(0, Math.min(3, colorIndex));\n        int[] color = GB_PALETTE[safeIndex];\n        return Color.rgb(color[0], color[1], color[2]);\n    }\n\n''',
    "GB palette accessor",
)
write("GameBoyFilter.java", gameboy)

# Add deterministic Accessibility text extraction and font_min replacement.
accessibility = read("FilterAccessibilityService.java")
accessibility = replace_once(
    accessibility,
    "import java.util.List;\n",
    "import java.util.HashSet;\nimport java.util.List;\nimport java.util.Set;\n",
    "font_min imports",
)

font_methods = r'''    /**
     * Replaces visible ASCII Accessibility text with deterministic GBDK font_min
     * glyphs when the output is the canonical 160x144 GB framebuffer.
     * Non-ASCII and out-of-range runs are rejected before drawing, matching the
     * supplied specification's pre-validation/no-partial-frame rule per run.
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
            Set<String> seen = new HashSet<>();
            int rendered = renderFontMinNode(
                    root,
                    windowBounds,
                    pixels,
                    seen,
                    background,
                    foreground
            );

            if (rendered > 0) {
                bitmap.setPixels(
                        pixels,
                        0,
                        FontMinRenderer.SCREEN_WIDTH,
                        0,
                        0,
                        FontMinRenderer.SCREEN_WIDTH,
                        FontMinRenderer.SCREEN_HEIGHT
                );
            }
            return rendered;
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

    private int renderFontMinNode(
            AccessibilityNodeInfo node,
            Rect windowBounds,
            int[] pixels,
            Set<String> seen,
            int background,
            int foreground
    ) {
        if (node == null) {
            return 0;
        }

        int rendered = 0;
        if (node.isVisibleToUser()) {
            CharSequence text = node.getText();
            if (text != null && text.length() > 0) {
                Rect bounds = new Rect();
                node.getBoundsInScreen(bounds);
                if (!bounds.isEmpty() && Rect.intersects(bounds, windowBounds)) {
                    String key = bounds.flattenToString() + "\u0000" + text;
                    if (seen.add(key)) {
                        int relativeX = Math.max(0, bounds.left - windowBounds.left);
                        int relativeY = Math.max(0, bounds.top - windowBounds.top);
                        int windowWidth = Math.max(1, windowBounds.width());
                        int windowHeight = Math.max(1, windowBounds.height());
                        int tileX = Math.max(0, Math.min(
                                FontMinRenderer.VISIBLE_TILE_WIDTH - 1,
                                (int) (((long) relativeX * FontMinRenderer.VISIBLE_TILE_WIDTH) / windowWidth)
                        ));
                        int tileY = Math.max(0, Math.min(
                                FontMinRenderer.VISIBLE_TILE_HEIGHT - 1,
                                (int) (((long) relativeY * FontMinRenderer.VISIBLE_TILE_HEIGHT) / windowHeight)
                        ));

                        if (FontMinRenderer.drawArgbText(
                                pixels,
                                FontMinRenderer.SCREEN_WIDTH,
                                FontMinRenderer.SCREEN_HEIGHT,
                                text,
                                tileX,
                                tileY,
                                background,
                                foreground
                        )) {
                            rendered++;
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
                rendered += renderFontMinNode(
                        child,
                        windowBounds,
                        pixels,
                        seen,
                        background,
                        foreground
                );
            } finally {
                child.recycle();
            }
        }
        return rendered;
    }

'''
accessibility = replace_once(
    accessibility,
    "    public void prepareProbe() {\n",
    font_methods + "    public void prepareProbe() {\n",
    "font_min accessibility renderer",
)
write("FilterAccessibilityService.java", accessibility)

# Apply the text replacement after the normal GB image filter and record its cost.
capture = read("FilterCaptureService.java")
capture = replace_once(
    capture,
    '''            long filterStartedNs = SystemClock.elapsedRealtimeNanos();
            GameBoyFilter.apply(
                    lowResolutionBitmap,
                    mode,
                    brightness,
                    contrast,
                    dither
            );
            long filterFinishedNs = SystemClock.elapsedRealtimeNanos();

            long frameCopyStartedNs = SystemClock.elapsedRealtimeNanos();
''',
    '''            long filterStartedNs = SystemClock.elapsedRealtimeNanos();
            GameBoyFilter.apply(
                    lowResolutionBitmap,
                    mode,
                    brightness,
                    contrast,
                    dither
            );
            long filterFinishedNs = SystemClock.elapsedRealtimeNanos();

            long fontMinStartedNs = SystemClock.elapsedRealtimeNanos();
            int fontMinNodes = 0;
            if (GameBoyFilter.MODE_GB.equals(mode)
                    && GameBoyFilter.RESOLUTION_GB.equals(resolution)
                    && targetWidth == FontMinRenderer.SCREEN_WIDTH
                    && targetHeight == FontMinRenderer.SCREEN_HEIGHT) {
                FilterAccessibilityService textService = FilterAccessibilityService.getInstance();
                if (textService != null) {
                    fontMinNodes = textService.applyFontMinTextOverlay(lowResolutionBitmap);
                }
            }
            long fontMinFinishedNs = SystemClock.elapsedRealtimeNanos();

            long frameCopyStartedNs = SystemClock.elapsedRealtimeNanos();
''',
    "font_min frame integration",
)
capture = replace_once(
    capture,
    '''            long filterNs = filterFinishedNs - filterStartedNs;
            long frameCopyNs = frameCopyFinishedNs - frameCopyStartedNs;
''',
    '''            long filterNs = filterFinishedNs - filterStartedNs;
            long fontMinNs = fontMinFinishedNs - fontMinStartedNs;
            int fontMinNodeCount = fontMinNodes;
            long frameCopyNs = frameCopyFinishedNs - frameCopyStartedNs;
''',
    "font_min metrics",
)
capture = replace_once(
    capture,
    '''                                    + " filter_ms=" + PerformanceLog.formatMs(filterNs)
                                    + " frame_copy_ms=" + PerformanceLog.formatMs(frameCopyNs)
''',
    '''                                    + " filter_ms=" + PerformanceLog.formatMs(filterNs)
                                    + " font_min_ms=" + PerformanceLog.formatMs(fontMinNs)
                                    + " font_min_nodes=" + fontMinNodeCount
                                    + " frame_copy_ms=" + PerformanceLog.formatMs(frameCopyNs)
''',
    "font_min performance log",
)
write("FilterCaptureService.java", capture)
