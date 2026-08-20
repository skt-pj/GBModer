#!/usr/bin/env python3
from pathlib import Path
import base64
import hashlib
import re
import sys
import time
import urllib.request
import zlib

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_japanese_font_source_v019.py <generated_src_root>")

root = Path(sys.argv[1])
package = root / "com/sktpj/gbmoder"

MISAKI_COMMIT = "44f702b209233175663050cbd0b6b58a531ebacb"
MISAKI_HPP_BLOB_SHA = "b480a5c48b31092937731f6293e9bfad384c9aca"
MISAKI_URL = (
    "https://raw.githubusercontent.com/aloseed/misaki/"
    + MISAKI_COMMIT
    + "/src/misaki.hpp"
)
REPLACEMENT_CODE_POINT = 0x25A1  # WHITE SQUARE


def read(path_name: str) -> str:
    return (package / path_name).read_text()


def write(path_name: str, text: str) -> None:
    (package / path_name).write_text(text)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def download_pinned_source() -> bytes:
    last_error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                MISAKI_URL,
                headers={"User-Agent": "GBModer-build/0.1.19"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
            git_blob = hashlib.sha1(
                b"blob " + str(len(data)).encode("ascii") + b"\0" + data
            ).hexdigest()
            if git_blob != MISAKI_HPP_BLOB_SHA:
                raise SystemExit(
                    f"Misaki source blob mismatch: expected {MISAKI_HPP_BLOB_SHA}, got {git_blob}"
                )
            return data
        except Exception as error:
            last_error = error
            if attempt < 2:
                time.sleep(1.0 + attempt)
    raise SystemExit(f"failed to download pinned Misaki source: {last_error}")


def extract_block(source: str, declaration: str) -> str:
    start = source.find(declaration)
    if start < 0:
        raise SystemExit(f"missing Misaki declaration: {declaration}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"missing opening brace for {declaration}")
    end = source.find("};", brace)
    if end < 0:
        raise SystemExit(f"missing closing brace for {declaration}")
    return source[brace + 1:end]


def java_chunks(data: bytes, chunk_size: int = 1200) -> str:
    encoded = base64.b64encode(zlib.compress(data, level=9)).decode("ascii")
    chunks = [encoded[i:i + chunk_size] for i in range(0, len(encoded), chunk_size)]
    return ",\n            ".join(f'"{chunk}"' for chunk in chunks)


source_bytes = download_pinned_source()
source = source_bytes.decode("utf-8")

mapping_block = extract_block(source, "const uint16_t misaki_uni[]")
mapping = [int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{4})", mapping_block)]
if len(mapping) != 65536:
    raise SystemExit(f"Misaki Unicode mapping length mismatch: {len(mapping)}")

font_block = extract_block(source, "const uint8_t misaki_data[][8]")
glyph_values = [int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]{2})", font_block)]
if len(glyph_values) % 8 != 0 or not glyph_values:
    raise SystemExit(f"Misaki glyph data length invalid: {len(glyph_values)}")
glyph_count = len(glyph_values) // 8
max_index = max(value for value in mapping if value != 0xFFFF)
if max_index >= glyph_count:
    raise SystemExit(f"Misaki mapping index {max_index} exceeds glyph count {glyph_count}")
if mapping[REPLACEMENT_CODE_POINT] == 0xFFFF:
    raise SystemExit("Misaki replacement square U+25A1 is missing")

mapping_bytes = bytearray()
for value in mapping:
    mapping_bytes.extend(((value >> 8) & 0xFF, value & 0xFF))
glyph_bytes = bytes(glyph_values)

map_chunks = java_chunks(bytes(mapping_bytes))
glyph_chunks = java_chunks(glyph_bytes)

japanese_font = f'''package com.sktpj.gbmoder;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.Base64;
import java.util.zip.InflaterInputStream;

/**
 * 8x8 Japanese bitmap glyph source for live GB text replacement.
 *
 * Data: Misaki font / aloseed/misaki
 * Commit: {MISAKI_COMMIT}
 * Source blob SHA-1: {MISAKI_HPP_BLOB_SHA}
 * Original font copyright (C) 2002-2015 Num Kadoma.
 * The font permits use/copy/distribution with or without modification,
 * commercially or noncommercially, and is provided without warranty.
 *
 * ASCII remains rendered by FontMinRenderer so the canonical GBDK font_min
 * reference vector and SHA-256 are unchanged.
 */
public final class JapaneseFont8x8 {{
    public static final String SOURCE_COMMIT = "{MISAKI_COMMIT}";
    public static final String SOURCE_BLOB_SHA = "{MISAKI_HPP_BLOB_SHA}";
    public static final int REPLACEMENT_CODE_POINT = 0x{REPLACEMENT_CODE_POINT:04X};
    public static final int GLYPH_COUNT = {glyph_count};

    private static final String[] MAP_ZLIB_B64 = {{
            {map_chunks}
    }};
    private static final String[] GLYPHS_ZLIB_B64 = {{
            {glyph_chunks}
    }};

    private static final byte[] UNICODE_TO_GLYPH = inflate(MAP_ZLIB_B64, 65536 * 2);
    private static final byte[] GLYPHS = inflate(GLYPHS_ZLIB_B64, GLYPH_COUNT * 8);
    private static final int REPLACEMENT_INDEX = rawGlyphIndex(REPLACEMENT_CODE_POINT);

    private JapaneseFont8x8() {{
    }}

    public static boolean supports(int codePoint) {{
        return codePoint >= 0 && codePoint <= 0xFFFF && rawGlyphIndex(codePoint) != 0xFFFF;
    }}

    public static int glyphIndexOrReplacement(int codePoint) {{
        if (codePoint >= 0 && codePoint <= 0xFFFF) {{
            int index = rawGlyphIndex(codePoint);
            if (index != 0xFFFF) {{
                return index;
            }}
        }}
        return REPLACEMENT_INDEX;
    }}

    public static boolean drawLogicalGlyph(
            byte[] framebuffer,
            int codePoint,
            int tileX,
            int tileY
    ) {{
        if (framebuffer == null
                || framebuffer.length != FontMinRenderer.SCREEN_WIDTH * FontMinRenderer.SCREEN_HEIGHT
                || tileX < 0 || tileX >= FontMinRenderer.VISIBLE_TILE_WIDTH
                || tileY < 0 || tileY >= FontMinRenderer.VISIBLE_TILE_HEIGHT) {{
            return false;
        }}

        int glyphIndex = glyphIndexOrReplacement(codePoint);
        int glyphBase = glyphIndex * 8;
        int pixelX = tileX * FontMinRenderer.TILE_SIZE;
        int pixelY = tileY * FontMinRenderer.TILE_SIZE;
        for (int row = 0; row < 8; row++) {{
            int bits = GLYPHS[glyphBase + row] & 0xFF;
            int offset = (pixelY + row) * FontMinRenderer.SCREEN_WIDTH + pixelX;
            for (int col = 0; col < 8; col++) {{
                framebuffer[offset + col] = (byte) ((bits & (0x80 >> col)) != 0
                        ? FontMinRenderer.FOREGROUND_INDEX
                        : FontMinRenderer.BACKGROUND_INDEX);
            }}
        }}
        return true;
    }}

    private static int rawGlyphIndex(int codePoint) {{
        int offset = codePoint * 2;
        return ((UNICODE_TO_GLYPH[offset] & 0xFF) << 8)
                | (UNICODE_TO_GLYPH[offset + 1] & 0xFF);
    }}

    private static byte[] inflate(String[] chunks, int expectedLength) {{
        StringBuilder encoded = new StringBuilder();
        for (String chunk : chunks) {{
            encoded.append(chunk);
        }}
        byte[] compressed = Base64.getDecoder().decode(encoded.toString());
        try (InflaterInputStream inflater = new InflaterInputStream(new ByteArrayInputStream(compressed));
             ByteArrayOutputStream output = new ByteArrayOutputStream(expectedLength)) {{
            byte[] buffer = new byte[8192];
            int read;
            while ((read = inflater.read(buffer)) >= 0) {{
                if (read > 0) {{
                    output.write(buffer, 0, read);
                }}
            }}
            byte[] result = output.toByteArray();
            if (result.length != expectedLength) {{
                throw new IllegalStateException(
                        "Misaki payload length mismatch expected=" + expectedLength + " actual=" + result.length
                );
            }}
            return result;
        }} catch (IOException error) {{
            throw new IllegalStateException("Unable to inflate Misaki font payload", error);
        }}
    }}
}}
'''
write("JapaneseFont8x8.java", japanese_font)

renderer = read("FontMinRenderer.java")
ascii_method = r'''    public static boolean drawLogicalAsciiGlyph(
            byte[] framebuffer,
            int ascii,
            int tileX,
            int tileY
    ) {
        if (framebuffer == null || framebuffer.length != SCREEN_WIDTH * SCREEN_HEIGHT
                || ascii < 0 || ascii > 0x7F
                || tileX < 0 || tileX >= VISIBLE_TILE_WIDTH
                || tileY < 0 || tileY >= VISIBLE_TILE_HEIGHT) {
            return false;
        }
        int tileIndex = MAPPING[ascii] & 0xFF;
        drawLogicalGlyph(framebuffer, tileIndex, tileX, tileY);
        return true;
    }

'''
renderer = replace_once(
    renderer,
    "    public static boolean verifyReferenceVector() {\n",
    ascii_method + "    public static boolean verifyReferenceVector() {\n",
    "ASCII glyph API",
)
write("FontMinRenderer.java", renderer)

mixed_renderer = r'''package com.sktpj.gbmoder;

/**
 * Live-screen text renderer: canonical GBDK font_min for ASCII and Misaki 8x8
 * glyphs for Japanese/Unicode. Every visible code point occupies one 8x8 tile;
 * LF is the only layout control. Unsupported code points render as an 8x8 square
 * instead of disappearing.
 */
public final class MixedGbTextRenderer {
    private MixedGbTextRenderer() {
    }

    public static int getTextTileWidth(CharSequence text) {
        if (text == null) {
            return -1;
        }
        int maxWidth = 0;
        int width = 0;
        for (int i = 0; i < text.length();) {
            int codePoint = Character.codePointAt(text, i);
            i += Character.charCount(codePoint);
            if (codePoint == 0x0A) {
                maxWidth = Math.max(maxWidth, width);
                width = 0;
            } else {
                width++;
            }
        }
        return Math.max(maxWidth, width);
    }

    public static int getTextTileHeight(CharSequence text) {
        if (text == null) {
            return -1;
        }
        int rows = 1;
        for (int i = 0; i < text.length();) {
            int codePoint = Character.codePointAt(text, i);
            i += Character.charCount(codePoint);
            if (codePoint == 0x0A) {
                rows++;
            }
        }
        return rows;
    }

    public static boolean canRenderText(CharSequence text, int lineOriginX, int startTileY) {
        if (text == null
                || lineOriginX < 0 || lineOriginX >= FontMinRenderer.VISIBLE_TILE_WIDTH
                || startTileY < 0 || startTileY >= FontMinRenderer.VISIBLE_TILE_HEIGHT) {
            return false;
        }

        int tileX = lineOriginX;
        int tileY = startTileY;
        for (int i = 0; i < text.length();) {
            int codePoint = Character.codePointAt(text, i);
            i += Character.charCount(codePoint);
            if (codePoint == 0x0A) {
                tileX = lineOriginX;
                tileY++;
                continue;
            }
            if (tileX < 0 || tileX >= FontMinRenderer.VISIBLE_TILE_WIDTH
                    || tileY < 0 || tileY >= FontMinRenderer.VISIBLE_TILE_HEIGHT) {
                return false;
            }
            tileX++;
        }
        return true;
    }

    public static boolean drawLogicalText(
            byte[] framebuffer,
            CharSequence text,
            int lineOriginX,
            int startTileY
    ) {
        if (framebuffer == null
                || framebuffer.length != FontMinRenderer.SCREEN_WIDTH * FontMinRenderer.SCREEN_HEIGHT
                || !canRenderText(text, lineOriginX, startTileY)) {
            return false;
        }

        int tileX = lineOriginX;
        int tileY = startTileY;
        for (int i = 0; i < text.length();) {
            int codePoint = Character.codePointAt(text, i);
            i += Character.charCount(codePoint);
            if (codePoint == 0x0A) {
                tileX = lineOriginX;
                tileY++;
                continue;
            }

            boolean drawn;
            if (codePoint >= 0 && codePoint <= 0x7F) {
                drawn = FontMinRenderer.drawLogicalAsciiGlyph(
                        framebuffer, codePoint, tileX, tileY
                );
            } else {
                drawn = JapaneseFont8x8.drawLogicalGlyph(
                        framebuffer, codePoint, tileX, tileY
                );
            }
            if (!drawn) {
                return false;
            }
            tileX++;
        }
        return true;
    }
}
'''
write("MixedGbTextRenderer.java", mixed_renderer)

accessibility = read("FilterAccessibilityService.java")
replacements = {
    "FontMinRenderer.getTextTileWidth(text)": "MixedGbTextRenderer.getTextTileWidth(text)",
    "FontMinRenderer.getTextTileHeight(text)": "MixedGbTextRenderer.getTextTileHeight(text)",
    "FontMinRenderer.canRenderText(text, tileX, tileY)": "MixedGbTextRenderer.canRenderText(text, tileX, tileY)",
    "FontMinRenderer.drawLogicalText(": "MixedGbTextRenderer.drawLogicalText(",
    "visible ASCII Accessibility text": "visible Unicode Accessibility text",
    "font_min is drawn": "font_min/Misaki 8x8 glyphs are drawn",
}
for old, new in replacements.items():
    if old not in accessibility:
        raise SystemExit(f"Japanese integration marker missing: {old}")
    accessibility = accessibility.replace(old, new)
write("FilterAccessibilityService.java", accessibility)

print(
    "Japanese 8x8 integration applied: "
    f"glyphs={glyph_count} source_commit={MISAKI_COMMIT} blob={MISAKI_HPP_BLOB_SHA}"
)
