package com.sktpj.gbmoder;

import android.content.res.Resources;
import android.graphics.Bitmap;
import android.graphics.Color;

import java.util.Arrays;

public final class GameBoyFilter {
    public static final String MODE_GB = "gb";
    public static final String MODE_DS = "ds";
    public static final String MODE_GBC = "gbc";
    public static final String MODE_GBA = "gba";

    private static final int GB_WIDTH = 160;
    private static final int GB_HEIGHT = 144;
    private static final int GBC_COLOR_LIMIT = 56;
    private static final float DITHER_PROTECT_DARK = 32.0f;
    private static final float DITHER_PROTECT_LIGHT = 223.0f;

    private static final int[][] GB_PALETTE = {
            {155, 188, 15},
            {139, 172, 15},
            {48, 98, 48},
            {15, 56, 15}
    };

    private static final int[][] BAYER_4X4 = {
            {0, 8, 2, 10},
            {12, 4, 14, 6},
            {3, 11, 1, 9},
            {15, 7, 13, 5}
    };

    private GameBoyFilter() {
    }

    public static int getBaseWidth(String mode) {
        if (MODE_GB.equals(mode)) {
            return GB_WIDTH;
        }
        int displayWidth = Resources.getSystem().getDisplayMetrics().widthPixels;
        return Math.max(1, displayWidth);
    }

    public static int getBaseHeight(String mode, int sourceWidth, int sourceHeight) {
        if (MODE_GB.equals(mode)) {
            return GB_HEIGHT;
        }
        int targetWidth = getBaseWidth(mode);
        return Math.max(
                1,
                Math.round(targetWidth * (sourceHeight / (float) Math.max(1, sourceWidth)))
        );
    }

    public static void apply(Bitmap bitmap, String mode, int brightness, int contrastValue, boolean dither) {
        int width = bitmap.getWidth();
        int height = bitmap.getHeight();
        int[] pixels = new int[width * height];
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height);
        float contrast = contrastValue / 100.0f;

        if (MODE_GB.equals(mode)) {
            applyGameBoy(pixels, width, height, brightness, contrast, dither);
        } else if (MODE_DS.equals(mode)) {
            applyRgb666(pixels, width, height, brightness, contrast, dither);
        } else {
            applyRgb555(pixels, width, height, brightness, contrast, dither);
            if (MODE_GBC.equals(mode)) {
                reduceToVisibleColorLimit(pixels, GBC_COLOR_LIMIT);
            }
        }

        bitmap.setPixels(pixels, 0, width, 0, 0, width, height);
    }

    private static void applyGameBoy(
            int[] pixels,
            int width,
            int height,
            int brightness,
            float contrast,
            boolean dither
    ) {
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int index = y * width + x;
                int color = pixels[index];
                int r = Color.red(color);
                int g = Color.green(color);
                int b = Color.blue(color);

                float lum = (0.299f * r) + (0.587f * g) + (0.114f * b);
                lum = ((lum - 128.0f) * contrast) + 128.0f + brightness;

                if (dither) {
                    float threshold = (BAYER_4X4[y & 3][x & 3] - 7.5f) * 7.0f;
                    lum += threshold;
                }

                lum = clamp(lum, 0.0f, 255.0f);
                int paletteIndex = clampInt(3 - ((int) Math.floor(lum / 64.0f)), 0, 3);
                int[] p = GB_PALETTE[paletteIndex];
                pixels[index] = Color.rgb(p[0], p[1], p[2]);
            }
        }
    }

    private static void applyRgb555(
            int[] pixels,
            int width,
            int height,
            int brightness,
            float contrast,
            boolean dither
    ) {
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int index = y * width + x;
                int color = pixels[index];
                float r = ((Color.red(color) - 128.0f) * contrast) + 128.0f + brightness;
                float g = ((Color.green(color) - 128.0f) * contrast) + 128.0f + brightness;
                float b = ((Color.blue(color) - 128.0f) * contrast) + 128.0f + brightness;

                float lum = (0.299f * r) + (0.587f * g) + (0.114f * b);
                if (dither && shouldApplyDither(lum)) {
                    float threshold = (BAYER_4X4[y & 3][x & 3] - 7.5f) * 2.5f;
                    r += threshold;
                    g += threshold;
                    b += threshold;
                }

                pixels[index] = Color.rgb(
                        quantizeRgb555(r),
                        quantizeRgb555(g),
                        quantizeRgb555(b)
                );
            }
        }
    }

    private static void applyRgb666(
            int[] pixels,
            int width,
            int height,
            int brightness,
            float contrast,
            boolean dither
    ) {
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int index = y * width + x;
                int color = pixels[index];
                float r = ((Color.red(color) - 128.0f) * contrast) + 128.0f + brightness;
                float g = ((Color.green(color) - 128.0f) * contrast) + 128.0f + brightness;
                float b = ((Color.blue(color) - 128.0f) * contrast) + 128.0f + brightness;

                float lum = (0.299f * r) + (0.587f * g) + (0.114f * b);
                if (dither && shouldApplyDither(lum)) {
                    float threshold = (BAYER_4X4[y & 3][x & 3] - 7.5f) * 2.5f;
                    r += threshold;
                    g += threshold;
                    b += threshold;
                }

                pixels[index] = Color.rgb(
                        quantizeRgb666(r),
                        quantizeRgb666(g),
                        quantizeRgb666(b)
                );
            }
        }
    }

    private static boolean shouldApplyDither(float luminance) {
        return luminance > DITHER_PROTECT_DARK && luminance < DITHER_PROTECT_LIGHT;
    }

    private static int quantizeRgb555(float value) {
        float clamped = clamp(value, 0.0f, 255.0f);
        int fiveBit = Math.round((clamped / 255.0f) * 31.0f);
        return Math.round((fiveBit / 31.0f) * 255.0f);
    }

    private static int quantizeRgb666(float value) {
        float clamped = clamp(value, 0.0f, 255.0f);
        int sixBit = Math.round((clamped / 255.0f) * 63.0f);
        return Math.round((sixBit / 63.0f) * 255.0f);
    }

    private static void reduceToVisibleColorLimit(int[] pixels, int limit) {
        int[] counts = new int[32768];
        for (int pixel : pixels) {
            int key = rgb555Key(pixel);
            counts[key]++;
        }

        int unique = 0;
        for (int count : counts) {
            if (count > 0) unique++;
        }
        if (unique <= limit) {
            return;
        }

        int[] paletteKeys = new int[limit];
        int[] paletteCounts = new int[limit];
        Arrays.fill(paletteKeys, -1);

        for (int key = 0; key < counts.length; key++) {
            int count = counts[key];
            if (count == 0) continue;
            for (int slot = 0; slot < limit; slot++) {
                if (count > paletteCounts[slot]) {
                    for (int shift = limit - 1; shift > slot; shift--) {
                        paletteCounts[shift] = paletteCounts[shift - 1];
                        paletteKeys[shift] = paletteKeys[shift - 1];
                    }
                    paletteCounts[slot] = count;
                    paletteKeys[slot] = key;
                    break;
                }
            }
        }

        int[] mappedKey = new int[32768];
        Arrays.fill(mappedKey, -1);
        for (int key : paletteKeys) {
            if (key >= 0) mappedKey[key] = key;
        }

        for (int key = 0; key < counts.length; key++) {
            if (counts[key] == 0 || mappedKey[key] >= 0) continue;
            mappedKey[key] = nearestPaletteKey(key, paletteKeys);
        }

        for (int i = 0; i < pixels.length; i++) {
            int key = rgb555Key(pixels[i]);
            int mapped = mappedKey[key];
            if (mapped >= 0) {
                pixels[i] = colorFromRgb555Key(mapped);
            }
        }
    }

    private static int nearestPaletteKey(int sourceKey, int[] paletteKeys) {
        int sr = (sourceKey >> 10) & 31;
        int sg = (sourceKey >> 5) & 31;
        int sb = sourceKey & 31;
        int bestKey = paletteKeys[0];
        int bestDistance = Integer.MAX_VALUE;

        for (int key : paletteKeys) {
            if (key < 0) continue;
            int r = (key >> 10) & 31;
            int g = (key >> 5) & 31;
            int b = key & 31;
            int dr = sr - r;
            int dg = sg - g;
            int db = sb - b;
            int distance = (dr * dr) + (dg * dg) + (db * db);
            if (distance < bestDistance) {
                bestDistance = distance;
                bestKey = key;
            }
        }
        return bestKey;
    }

    private static int rgb555Key(int color) {
        int r5 = Math.round((Color.red(color) / 255.0f) * 31.0f);
        int g5 = Math.round((Color.green(color) / 255.0f) * 31.0f);
        int b5 = Math.round((Color.blue(color) / 255.0f) * 31.0f);
        return (r5 << 10) | (g5 << 5) | b5;
    }

    private static int colorFromRgb555Key(int key) {
        int r5 = (key >> 10) & 31;
        int g5 = (key >> 5) & 31;
        int b5 = key & 31;
        int r = Math.round((r5 / 31.0f) * 255.0f);
        int g = Math.round((g5 / 31.0f) * 255.0f);
        int b = Math.round((b5 / 31.0f) * 255.0f);
        return Color.rgb(r, g, b);
    }

    private static float clamp(float value, float min, float max) {
        return Math.max(min, Math.min(max, value));
    }

    private static int clampInt(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }
}
