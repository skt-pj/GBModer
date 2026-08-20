package com.sktpj.gbmoder;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;

import org.junit.Test;

public class FontMinRendererTest {
    private static final String REFERENCE_TEXT =
            "GAME BOY\n0123456789\nABCDEFGHIJ\nKLMNOPQRST\nUVWXYZ";

    @Test
    public void referenceVectorMatchesSpecification() {
        assertTrue(FontMinRenderer.verifyReferenceVector());

        byte[] frame = FontMinRenderer.renderLogicalFrame(
                REFERENCE_TEXT.getBytes(StandardCharsets.US_ASCII),
                1,
                1
        );
        assertEquals(160 * 144, frame.length);

        int foreground = 0;
        for (byte value : frame) {
            int index = value & 0xFF;
            assertTrue(index == FontMinRenderer.BACKGROUND_INDEX
                    || index == FontMinRenderer.FOREGROUND_INDEX);
            if (index == FontMinRenderer.FOREGROUND_INDEX) {
                foreground++;
            }
        }
        assertEquals(671, foreground);
    }

    @Test
    public void reusableLogicalPlaneMatchesCanonicalRenderer() {
        byte[] expected = FontMinRenderer.renderLogicalFrame(
                REFERENCE_TEXT.getBytes(StandardCharsets.US_ASCII),
                1,
                1
        );
        byte[] actual = new byte[FontMinRenderer.SCREEN_WIDTH * FontMinRenderer.SCREEN_HEIGHT];
        assertTrue(FontMinRenderer.drawLogicalText(actual, REFERENCE_TEXT, 1, 1));
        assertArrayEquals(expected, actual);
    }

    @Test
    public void invalidRunDoesNotMutateFramebuffer() {
        byte[] framebuffer = new byte[FontMinRenderer.SCREEN_WIDTH * FontMinRenderer.SCREEN_HEIGHT];
        Arrays.fill(framebuffer, (byte) FontMinRenderer.FOREGROUND_INDEX);
        byte[] before = framebuffer.clone();

        assertFalse(FontMinRenderer.drawLogicalText(
                framebuffer,
                "ABCDEFGHIJKLMNOPQRSTU",
                0,
                0
        ));
        assertArrayEquals(before, framebuffer);
    }

    @Test
    public void lowercaseUsesSameFontMinTilesAsUppercase() {
        byte[] upper = FontMinRenderer.renderLogicalFrame(
                "GAMEBOY".getBytes(StandardCharsets.US_ASCII),
                0,
                0
        );
        byte[] lower = FontMinRenderer.renderLogicalFrame(
                "gameboy".getBytes(StandardCharsets.US_ASCII),
                0,
                0
        );
        assertArrayEquals(upper, lower);
    }
}
