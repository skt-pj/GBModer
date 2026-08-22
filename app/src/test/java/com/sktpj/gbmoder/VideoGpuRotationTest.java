package com.sktpj.gbmoder;

import static org.junit.Assert.assertArrayEquals;

import org.junit.Test;

public class VideoGpuRotationTest {
    private static final float EPSILON = 0.0001f;

    @Test
    public void clockwiseNinetyKeepsPortraitTopUpright() {
        assertArrayEquals(
                new float[]{1f, 0f, 1f, 1f, 0f, 0f, 0f, 1f},
                VideoGpuConverter.mapDisplayUvForRotation(90, 0f, 0f, 1f, 1f),
                EPSILON
        );
    }

    @Test
    public void clockwiseTwoSeventyKeepsPortraitTopUpright() {
        assertArrayEquals(
                new float[]{0f, 1f, 0f, 0f, 1f, 1f, 1f, 0f},
                VideoGpuConverter.mapDisplayUvForRotation(270, 0f, 0f, 1f, 1f),
                EPSILON
        );
    }

    @Test
    public void clockwiseNinetyPreservesCroppedRegionOrientation() {
        assertArrayEquals(
                new float[]{0.8f, 0.1f, 0.8f, 0.9f, 0.2f, 0.1f, 0.2f, 0.9f},
                VideoGpuConverter.mapDisplayUvForRotation(90, 0.1f, 0.2f, 0.9f, 0.8f),
                EPSILON
        );
    }

    @Test
    public void zeroAndOneEightyRemainStable() {
        assertArrayEquals(
                new float[]{0f, 0f, 1f, 0f, 0f, 1f, 1f, 1f},
                VideoGpuConverter.mapDisplayUvForRotation(0, 0f, 0f, 1f, 1f),
                EPSILON
        );
        assertArrayEquals(
                new float[]{1f, 1f, 0f, 1f, 1f, 0f, 0f, 0f},
                VideoGpuConverter.mapDisplayUvForRotation(180, 0f, 0f, 1f, 1f),
                EPSILON
        );
    }
}
