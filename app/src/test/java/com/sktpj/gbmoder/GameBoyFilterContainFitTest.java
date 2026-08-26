package com.sktpj.gbmoder;

import static org.junit.Assert.assertArrayEquals;

import org.junit.Test;

public class GameBoyFilterContainFitTest {
    @Test
    public void portraitSourceFitsInsideGbResolutionWithoutCropping() {
        assertArrayEquals(
                new int[]{39, 0, 120, 144},
                GameBoyFilter.getContainFitBounds(1080, 1920, 160, 144)
        );
    }

    @Test
    public void wideSourceFitsInsideGbResolutionWithoutCropping() {
        assertArrayEquals(
                new int[]{0, 27, 160, 117},
                GameBoyFilter.getContainFitBounds(1920, 1080, 160, 144)
        );
    }

    @Test
    public void matchingAspectUsesWholeTarget() {
        assertArrayEquals(
                new int[]{0, 0, 160, 144},
                GameBoyFilter.getContainFitBounds(1600, 1440, 160, 144)
        );
    }
}
