package com.sktpj.gbmoder;

import static org.junit.Assert.assertArrayEquals;
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

    @Test
    public void fixedPresetsCenterCropWideSourcesInsteadOfStretching() {
        assertArrayEquals(
                new int[]{360, 0, 1560, 1080},
                GameBoyFilter.getCenterCropBounds(GameBoyFilter.RESOLUTION_GB, 1920, 1080)
        );
        assertArrayEquals(
                new int[]{150, 0, 1770, 1080},
                GameBoyFilter.getCenterCropBounds(GameBoyFilter.RESOLUTION_GBA, 1920, 1080)
        );
        assertArrayEquals(
                new int[]{240, 0, 1680, 1080},
                GameBoyFilter.getCenterCropBounds(GameBoyFilter.RESOLUTION_DS, 1920, 1080)
        );
    }

    @Test
    public void fixedPresetsCenterCropTallSourcesInsteadOfStretching() {
        assertArrayEquals(
                new int[]{0, 474, 1080, 1446},
                GameBoyFilter.getCenterCropBounds(GameBoyFilter.RESOLUTION_GB, 1080, 1920)
        );
        assertArrayEquals(
                new int[]{0, 600, 1080, 1320},
                GameBoyFilter.getCenterCropBounds(GameBoyFilter.RESOLUTION_GBA, 1080, 1920)
        );
        assertArrayEquals(
                new int[]{0, 555, 1080, 1365},
                GameBoyFilter.getCenterCropBounds(GameBoyFilter.RESOLUTION_DS, 1080, 1920)
        );
    }

    @Test
    public void phoneAndNativeResolutionKeepWholeSourceAspect() {
        assertArrayEquals(
                new int[]{0, 0, 1080, 1920},
                GameBoyFilter.getCenterCropBounds("phone_20", 1080, 1920)
        );
        assertArrayEquals(
                new int[]{0, 0, 1080, 1920},
                GameBoyFilter.getCenterCropBounds(GameBoyFilter.RESOLUTION_NATIVE, 1080, 1920)
        );
    }

    @Test
    public void targetFirstDecodeKeepsSourceAspectUntilCrop() {
        assertEquals(
                256,
                GameBoyFilter.getCenterCropWorkingWidth(
                        GameBoyFilter.RESOLUTION_GB,
                        1920,
                        1080,
                        160,
                        144
                )
        );
        assertEquals(
                144,
                GameBoyFilter.getCenterCropWorkingHeight(
                        GameBoyFilter.RESOLUTION_GB,
                        1920,
                        1080,
                        160,
                        144
                )
        );
        assertEquals(
                160,
                GameBoyFilter.getCenterCropWorkingWidth(
                        GameBoyFilter.RESOLUTION_GB,
                        1080,
                        1920,
                        160,
                        144
                )
        );
        assertEquals(
                284,
                GameBoyFilter.getCenterCropWorkingHeight(
                        GameBoyFilter.RESOLUTION_GB,
                        1080,
                        1920,
                        160,
                        144
                )
        );
    }

    @Test
    public void portraitVideoSwapsFixedPresetDimensions() {
        assertEquals(144, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_GB, 1080, 1920));
        assertEquals(160, GameBoyFilter.getVideoTargetHeight(GameBoyFilter.RESOLUTION_GB, 1080, 1920));
        assertEquals(144, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_GBC, 1080, 1920));
        assertEquals(160, GameBoyFilter.getVideoTargetHeight(GameBoyFilter.RESOLUTION_GBC, 1080, 1920));
        assertEquals(160, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_GBA, 1080, 1920));
        assertEquals(240, GameBoyFilter.getVideoTargetHeight(GameBoyFilter.RESOLUTION_GBA, 1080, 1920));
        assertEquals(192, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_DS, 1080, 1920));
        assertEquals(256, GameBoyFilter.getVideoTargetHeight(GameBoyFilter.RESOLUTION_DS, 1080, 1920));
    }

    @Test
    public void landscapeVideoKeepsFixedPresetDimensions() {
        assertEquals(160, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_GB, 1920, 1080));
        assertEquals(144, GameBoyFilter.getVideoTargetHeight(GameBoyFilter.RESOLUTION_GB, 1920, 1080));
        assertEquals(240, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_GBA, 1920, 1080));
        assertEquals(160, GameBoyFilter.getVideoTargetHeight(GameBoyFilter.RESOLUTION_GBA, 1920, 1080));
        assertEquals(256, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_DS, 1920, 1080));
        assertEquals(192, GameBoyFilter.getVideoTargetHeight(GameBoyFilter.RESOLUTION_DS, 1920, 1080));
    }

    @Test
    public void portraitVideoCropsToRotatedPresetAspect() {
        assertArrayEquals(
                new int[]{0, 360, 1080, 1560},
                GameBoyFilter.getCenterCropBoundsForTarget(
                        GameBoyFilter.RESOLUTION_GB,
                        1080,
                        1920,
                        144,
                        160
                )
        );
        assertArrayEquals(
                new int[]{0, 150, 1080, 1770},
                GameBoyFilter.getCenterCropBoundsForTarget(
                        GameBoyFilter.RESOLUTION_GBA,
                        1080,
                        1920,
                        160,
                        240
                )
        );
        assertArrayEquals(
                new int[]{0, 240, 1080, 1680},
                GameBoyFilter.getCenterCropBoundsForTarget(
                        GameBoyFilter.RESOLUTION_DS,
                        1080,
                        1920,
                        192,
                        256
                )
        );
    }

    @Test
    public void portraitPhoneAndNativeVideoKeepSourceDimensions() {
        assertEquals(216, GameBoyFilter.getVideoTargetWidth("phone_20", 1080, 1920));
        assertEquals(384, GameBoyFilter.getVideoTargetHeight("phone_20", 1080, 1920));
        assertEquals(1080, GameBoyFilter.getVideoTargetWidth(GameBoyFilter.RESOLUTION_NATIVE, 1080, 1920));
        assertEquals(1920, GameBoyFilter.getVideoTargetHeight(GameBoyFilter.RESOLUTION_NATIVE, 1080, 1920));
    }
}
