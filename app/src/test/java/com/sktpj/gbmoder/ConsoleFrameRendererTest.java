package com.sktpj.gbmoder;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class ConsoleFrameRendererTest {
    @Test
    public void onlyFixedResolutionsUseConsoleFrame() {
        assertTrue(ConsoleFrameRenderer.isFixedResolution(GameBoyFilter.RESOLUTION_GB));
        assertTrue(ConsoleFrameRenderer.isFixedResolution(GameBoyFilter.RESOLUTION_GBC));
        assertTrue(ConsoleFrameRenderer.isFixedResolution(GameBoyFilter.RESOLUTION_GBA));
        assertTrue(ConsoleFrameRenderer.isFixedResolution(GameBoyFilter.RESOLUTION_DS));
        assertFalse(ConsoleFrameRenderer.isFixedResolution(GameBoyFilter.RESOLUTION_PHONE_20));
        assertFalse(ConsoleFrameRenderer.isFixedResolution(GameBoyFilter.RESOLUTION_NATIVE));
    }

    @Test
    public void gbFrameKeepsExactScreenInsideBody() {
        ConsoleFrameRenderer.FrameSpec spec = ConsoleFrameRenderer.getSpec(
                GameBoyFilter.RESOLUTION_GB,
                160,
                144
        );
        assertEquals(224, spec.outputWidth);
        assertEquals(292, spec.outputHeight);
        assertEquals(32, spec.screenLeft);
        assertEquals(36, spec.screenTop);
        assertEquals(160, spec.screenWidth);
        assertEquals(144, spec.screenHeight);
        assertEquals(ConsoleFrameRenderer.STYLE_GB, spec.style);
    }

    @Test
    public void gbaFrameSupportsPortraitVideoScreen() {
        ConsoleFrameRenderer.FrameSpec spec = ConsoleFrameRenderer.getSpec(
                GameBoyFilter.RESOLUTION_GBA,
                160,
                240
        );
        assertEquals(264, spec.outputWidth);
        assertEquals(324, spec.outputHeight);
        assertEquals(52, spec.screenLeft);
        assertEquals(42, spec.screenTop);
        assertEquals(160, spec.screenWidth);
        assertEquals(240, spec.screenHeight);
    }

    @Test
    public void dsFrameCreatesClamshellSpace() {
        ConsoleFrameRenderer.FrameSpec spec = ConsoleFrameRenderer.getSpec(
                GameBoyFilter.RESOLUTION_DS,
                256,
                192
        );
        assertEquals(312, spec.outputWidth);
        assertEquals(492, spec.outputHeight);
        assertTrue(spec.outputHeight > spec.screenHeight * 2);
        assertEquals(ConsoleFrameRenderer.STYLE_DS, spec.style);
    }
}
