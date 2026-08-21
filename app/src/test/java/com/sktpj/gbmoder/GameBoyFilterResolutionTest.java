package com.sktpj.gbmoder;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class GameBoyFilterResolutionTest {
    @Test
    public void phoneResolutionUsesFivePercentSteps() {
        assertEquals("phone_5", GameBoyFilter.phoneResolution(5));
        assertEquals("phone_20", GameBoyFilter.phoneResolution(20));
        assertEquals("phone_95", GameBoyFilter.phoneResolution(95));
        assertEquals(GameBoyFilter.RESOLUTION_NATIVE, GameBoyFilter.phoneResolution(100));
        assertEquals(GameBoyFilter.RESOLUTION_PHONE_20, GameBoyFilter.phoneResolution(22));
    }

    @Test
    public void targetDimensionsScaleFromSourceDimensions() {
        assertEquals(50, GameBoyFilter.getTargetWidth("phone_5", 1000));
        assertEquals(100, GameBoyFilter.getTargetHeight("phone_5", 2000));
        assertEquals(200, GameBoyFilter.getTargetWidth("phone_20", 1000));
        assertEquals(400, GameBoyFilter.getTargetHeight("phone_20", 2000));
        assertEquals(950, GameBoyFilter.getTargetWidth("phone_95", 1000));
        assertEquals(1900, GameBoyFilter.getTargetHeight("phone_95", 2000));
        assertEquals(1000, GameBoyFilter.getTargetWidth(GameBoyFilter.RESOLUTION_NATIVE, 1000));
        assertEquals(2000, GameBoyFilter.getTargetHeight(GameBoyFilter.RESOLUTION_NATIVE, 2000));
    }

    @Test
    public void legacyThirdAndTwoThirdScalesRemainReadable() {
        assertEquals(330, GameBoyFilter.getTargetWidth(GameBoyFilter.RESOLUTION_PHONE_33, 1000));
        assertEquals(1340, GameBoyFilter.getTargetHeight(GameBoyFilter.RESOLUTION_PHONE_67, 2000));
    }
}
