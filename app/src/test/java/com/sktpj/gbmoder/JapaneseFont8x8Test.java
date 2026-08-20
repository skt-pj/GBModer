package com.sktpj.gbmoder;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class JapaneseFont8x8Test {
    @Test
    public void commonJapaneseGlyphsAreAvailable() {
        assertTrue(JapaneseFont8x8.supports('日'));
        assertTrue(JapaneseFont8x8.supports('本'));
        assertTrue(JapaneseFont8x8.supports('語'));
        assertTrue(JapaneseFont8x8.supports('あ'));
        assertTrue(JapaneseFont8x8.supports('ア'));
        assertTrue(JapaneseFont8x8.supports('。'));
    }

    @Test
    public void mixedJapaneseAndAsciiRendersIntoCanonicalTilePlane() {
        byte[] frame = new byte[FontMinRenderer.SCREEN_WIDTH * FontMinRenderer.SCREEN_HEIGHT];
        String text = "日本語GAMEBOY";

        assertEquals(10, MixedGbTextRenderer.getTextTileWidth(text));
        assertEquals(1, MixedGbTextRenderer.getTextTileHeight(text));
        assertTrue(MixedGbTextRenderer.canRenderText(text, 1, 1));
        assertTrue(MixedGbTextRenderer.drawLogicalText(frame, text, 1, 1));

        int foreground = 0;
        for (byte value : frame) {
            int index = value & 0xFF;
            assertTrue(index == FontMinRenderer.BACKGROUND_INDEX
                    || index == FontMinRenderer.FOREGROUND_INDEX);
            if (index == FontMinRenderer.FOREGROUND_INDEX) {
                foreground++;
            }
        }
        assertTrue(foreground > 0);
    }

    @Test
    public void unsupportedUnicodeUsesVisibleReplacementGlyph() {
        byte[] frame = new byte[FontMinRenderer.SCREEN_WIDTH * FontMinRenderer.SCREEN_HEIGHT];
        String emoji = new String(Character.toChars(0x1F600));

        assertFalse(JapaneseFont8x8.supports(0x1F600));
        assertTrue(MixedGbTextRenderer.drawLogicalText(frame, emoji, 0, 0));

        int foreground = 0;
        for (byte value : frame) {
            if ((value & 0xFF) == FontMinRenderer.FOREGROUND_INDEX) {
                foreground++;
            }
        }
        assertTrue(foreground > 0);
    }

    @Test
    public void canonicalAsciiReferenceStillPasses() {
        assertTrue(FontMinRenderer.verifyReferenceVector());
    }
}
