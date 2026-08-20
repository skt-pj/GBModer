package com.sktpj.gbmoder;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Deterministic GBDK font_min renderer.
 *
 * Source: gbdk-2020/gbdk-2020
 * Commit: 5d955df81231a00b8ea23aa3e493f7b6d4aa8091
 * File: gbdk-lib/libc/targets/f_min.s
 * Git blob: bbfa8d6aa614256a9f733ad99abb5a6be7126b6e
 *
 * Logical output follows the project specification: 160x144, 8x8 tiles,
 * bit7 leftmost, background index 0, foreground index 3, no wrap/scroll.
 */
public final class FontMinRenderer {
    public static final int SCREEN_WIDTH = 160;
    public static final int SCREEN_HEIGHT = 144;
    public static final int TILE_SIZE = 8;
    public static final int VISIBLE_TILE_WIDTH = 20;
    public static final int VISIBLE_TILE_HEIGHT = 18;
    public static final int BACKGROUND_INDEX = 0;
    public static final int FOREGROUND_INDEX = 3;

    public static final String SOURCE_REPOSITORY = "gbdk-2020/gbdk-2020";
    public static final String SOURCE_COMMIT = "5d955df81231a00b8ea23aa3e493f7b6d4aa8091";
    public static final String SOURCE_FILE = "gbdk-lib/libc/targets/f_min.s";
    public static final String SOURCE_BLOB_SHA = "bbfa8d6aa614256a9f733ad99abb5a6be7126b6e";

    public static final String EXPECTED_REFERENCE_SHA256 =
            "38bb88a2b5413ed15770d76f77ab45a0def0543d208fa206403e1a3f4a5106c5";
    public static final int EXPECTED_REFERENCE_FOREGROUND_PIXELS = 671;

    private static final String REFERENCE_TEXT =
            "GAME BOY\n0123456789\nABCDEFGHIJ\nKLMNOPQRST\nUVWXYZ";

    // Exact 128-byte mapping table from f_min.s. Undefined codes map to tile 0.
    private static final String MAPPING_HEX =
            "0000000000000000000000000000000000000000000000000000000000000000" +
            "000000000000000000000000000000000102030405060708090a000000000000" +
            "000b0c0d0e0f101112131415161718191a1b1c1d1e1f20212223240000000000" +
            "000b0c0d0e0f101112131415161718191a1b1c1d1e1f20212223240000000000";

    // 37 glyphs * 8 rows, one byte per 1bpp row. Tile 0 is space.
    private static final String GLYPHS_HEX =
            "0000000000000000" +
            "003c464a52623c000018280808083e00003c42023c407e00003c420c02423c00" +
            "00081828487e0800007e407c02423c00003c407c42423c00007e020408101000" +
            "003c423c42423c00003c42423e023c00003c42427e424200007c427c42427c00" +
            "003c424040423c000078444242447800007e407c40407e00007e407c40404000" +
            "003c42404e423c000042427e42424200003e080808083e000002020242423c00" +
            "00444870484442000040404040407e000042665a42424200004262524a464200" +
            "003c424242423c00007c42427c404000003c4242524a3c00007c42427c444200" +
            "003c403c02423c0000fe1010101010000042424242423c000042424242241800" +
            "00424242425a240000422418182442000082442810101000007e040810207e00";

    private static final byte[] MAPPING = decodeHex(MAPPING_HEX, 128);
    private static final byte[] GLYPHS = decodeHex(GLYPHS_HEX, 37 * 8);

    private FontMinRenderer() {
    }

    public static byte[] renderLogicalFrame(byte[] input, int lineOriginX, int startTileY) {
        validate(input, lineOriginX, startTileY);
        byte[] framebuffer = new byte[SCREEN_WIDTH * SCREEN_HEIGHT];

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
        return framebuffer;
    }

    /**
     * Draw a text run into a 160x144 ARGB framebuffer while preserving the
     * specification's 0/3 logical indices via caller-provided display colors.
     * Every glyph writes all 64 pixels, so source Android font pixels underneath
     * are replaced rather than blended.
     */
    public static boolean drawArgbText(
            int[] argb,
            int width,
            int height,
            CharSequence text,
            int lineOriginX,
            int startTileY,
            int backgroundArgb,
            int foregroundArgb
    ) {
        if (argb == null || width != SCREEN_WIDTH || height != SCREEN_HEIGHT
                || argb.length < SCREEN_WIDTH * SCREEN_HEIGHT || text == null) {
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
            drawArgbGlyph(argb, tileIndex, tileX, tileY, backgroundArgb, foregroundArgb);
            tileX++;
        }
        return true;
    }

    public static boolean verifyReferenceVector() {
        byte[] frame = renderLogicalFrame(strictAscii(REFERENCE_TEXT), 1, 1);
        int foreground = 0;
        for (byte value : frame) {
            if ((value & 0xFF) == FOREGROUND_INDEX) {
                foreground++;
            } else if ((value & 0xFF) != BACKGROUND_INDEX) {
                return false;
            }
        }
        return foreground == EXPECTED_REFERENCE_FOREGROUND_PIXELS
                && EXPECTED_REFERENCE_SHA256.equals(sha256(frame));
    }

    private static void validate(byte[] input, int lineOriginX, int startTileY) {
        if (input == null) {
            throw new IllegalArgumentException("input is null");
        }
        if (lineOriginX < 0 || lineOriginX >= VISIBLE_TILE_WIDTH) {
            throw new IllegalArgumentException("line_origin_x out of range");
        }
        if (startTileY < 0 || startTileY >= VISIBLE_TILE_HEIGHT) {
            throw new IllegalArgumentException("start_tile_y out of range");
        }

        int tileX = lineOriginX;
        int tileY = startTileY;
        for (byte value : input) {
            int unsigned = value & 0xFF;
            if (unsigned >= 0x80) {
                throw new IllegalArgumentException("input byte >= 0x80");
            }
            if (unsigned == 0x0A) {
                tileX = lineOriginX;
                tileY++;
                continue;
            }
            if (tileX < 0 || tileX >= VISIBLE_TILE_WIDTH) {
                throw new IllegalArgumentException("tile_x out of range");
            }
            if (tileY < 0 || tileY >= VISIBLE_TILE_HEIGHT) {
                throw new IllegalArgumentException("tile_y out of range");
            }
            tileX++;
        }
    }

    private static void drawLogicalGlyph(byte[] framebuffer, int tileIndex, int tileX, int tileY) {
        int glyphBase = tileIndex * 8;
        int pixelX = tileX * TILE_SIZE;
        int pixelY = tileY * TILE_SIZE;
        for (int row = 0; row < 8; row++) {
            int bits = GLYPHS[glyphBase + row] & 0xFF;
            int offset = (pixelY + row) * SCREEN_WIDTH + pixelX;
            for (int col = 0; col < 8; col++) {
                framebuffer[offset + col] = (byte) ((bits & (0x80 >> col)) != 0
                        ? FOREGROUND_INDEX
                        : BACKGROUND_INDEX);
            }
        }
    }

    private static void drawArgbGlyph(
            int[] argb,
            int tileIndex,
            int tileX,
            int tileY,
            int backgroundArgb,
            int foregroundArgb
    ) {
        int glyphBase = tileIndex * 8;
        int pixelX = tileX * TILE_SIZE;
        int pixelY = tileY * TILE_SIZE;
        for (int row = 0; row < 8; row++) {
            int bits = GLYPHS[glyphBase + row] & 0xFF;
            int offset = (pixelY + row) * SCREEN_WIDTH + pixelX;
            for (int col = 0; col < 8; col++) {
                argb[offset + col] = (bits & (0x80 >> col)) != 0
                        ? foregroundArgb
                        : backgroundArgb;
            }
        }
    }

    private static byte[] strictAscii(CharSequence text) {
        if (text == null) {
            return null;
        }
        byte[] bytes = new byte[text.length()];
        for (int i = 0; i < text.length(); i++) {
            char value = text.charAt(i);
            if (value > 0x7F) {
                return null;
            }
            bytes[i] = (byte) value;
        }
        return bytes;
    }

    private static byte[] decodeHex(String hex, int expectedBytes) {
        if (hex.length() != expectedBytes * 2) {
            throw new IllegalStateException("font_min hex length mismatch");
        }
        byte[] result = new byte[expectedBytes];
        for (int i = 0; i < expectedBytes; i++) {
            int hi = Character.digit(hex.charAt(i * 2), 16);
            int lo = Character.digit(hex.charAt(i * 2 + 1), 16);
            if (hi < 0 || lo < 0) {
                throw new IllegalStateException("invalid font_min hex");
            }
            result[i] = (byte) ((hi << 4) | lo);
        }
        return result;
    }

    private static String sha256(byte[] data) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(data);
            StringBuilder builder = new StringBuilder(hash.length * 2);
            for (byte value : hash) {
                builder.append(String.format("%02x", value & 0xFF));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }
}
