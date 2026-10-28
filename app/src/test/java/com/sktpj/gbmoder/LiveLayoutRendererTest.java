package com.sktpj.gbmoder;

import org.junit.After;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class LiveLayoutRendererTest {
    @After
    public void restoreChassis() {
        LiveLayoutRenderer.setLayoutMode(LiveLayoutRenderer.CHASSIS);
    }

    @Test
    public void fullscreenUsesEntirePortraitViewportWithoutCropping() {
        LiveLayoutRenderer.setLayoutMode(LiveLayoutRenderer.FULLSCREEN);
        int[] rect = LiveLayoutRenderer.getContentRect("gb", 1080, 2400, 540, 1200);
        assertEquals(0, rect[0]);
        assertEquals(0, rect[1]);
        assertEquals(1080, rect[2]);
        assertEquals(2400, rect[3]);
        int[] crop = LiveLayoutRenderer.getSourceRectForWidthFit("gb", 1080, 2400, 540, 1200);
        assertEquals(1200, crop[3]);
    }

    @Test
    public void sgbFitsLandscapeScreenInsideSurround() {
        LiveLayoutRenderer.setLayoutMode(LiveLayoutRenderer.SUPER_GAME_BOY);
        int[] rect = LiveLayoutRenderer.getContentRect("gb", 2400, 1080, 1600, 900);
        assertTrue(rect[0] > 0 && rect[1] > 0);
        assertTrue(rect[0] + rect[2] < 2400);
        assertTrue(rect[1] + rect[3] < 1080);
        assertEquals(16f / 9f, rect[2] / (float) rect[3], 0.01f);
    }

    @Test
    public void sgbFitsPortraitScreenInsideSurround() {
        LiveLayoutRenderer.setLayoutMode(LiveLayoutRenderer.SUPER_GAME_BOY);
        int[] rect = LiveLayoutRenderer.getContentRect("gb", 1080, 2400, 540, 1200);
        assertTrue(rect[0] > 0 && rect[1] > 0);
        assertTrue(rect[0] + rect[2] < 1080);
        assertTrue(rect[1] + rect[3] < 2400);
        assertEquals(540f / 1200f, rect[2] / (float) rect[3], 0.01f);
    }

    @Test
    public void invalidLayoutDefaultsToChassis() {
        assertEquals(LiveLayoutRenderer.CHASSIS, LiveLayoutRenderer.safeMode(-1));
        assertEquals(LiveLayoutRenderer.CHASSIS, LiveLayoutRenderer.safeMode(99));
    }
}
