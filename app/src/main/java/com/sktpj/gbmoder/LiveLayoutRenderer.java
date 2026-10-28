package com.sktpj.gbmoder;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;

/**
 * Layout of a live, filtered screen. Decorations never include fixed game artwork.
 * The source bitmap is provided by the active capture route.
 */
final class LiveLayoutRenderer {
    static final int FULLSCREEN = 0;
    static final int CHASSIS = 1;
    static final int SUPER_GAME_BOY = 2;
    private static volatile int currentLayout = CHASSIS;

    private LiveLayoutRenderer() {}

    static int safeMode(int requested) {
        return requested == FULLSCREEN || requested == CHASSIS || requested == SUPER_GAME_BOY
                ? requested : CHASSIS;
    }

    static void setLayoutMode(int requested) {
        currentLayout = safeMode(requested);
    }

    static int getLayoutMode() {
        return currentLayout;
    }

    static int[] getContentRect(
            String consoleMode, int width, int height, int sourceWidth, int sourceHeight) {
        if (currentLayout == CHASSIS) {
            return ConsoleFrameRenderer.getContentRect(
                    consoleMode, width, height, sourceWidth, sourceHeight);
        }
        int w = Math.max(1, width);
        int h = Math.max(1, height);
        if (currentLayout == FULLSCREEN) {
            return contain(0, 0, w, h, sourceWidth, sourceHeight);
        }
        // SGB-style TV surround: the actual game/app screen remains dynamic.
        int marginX = Math.max(3, Math.round(w * 0.075f));
        int marginY = Math.max(3, Math.round(h * (w > h ? 0.15f : 0.10f)));
        int panelLeft = marginX;
        int panelTop = marginY;
        int panelWidth = Math.max(1, w - marginX * 2);
        int panelHeight = Math.max(1, h - marginY * 2);
        int insetX = Math.max(2, Math.round(panelWidth * 0.055f));
        int insetY = Math.max(2, Math.round(panelHeight * 0.09f));
        return contain(
                panelLeft + insetX,
                panelTop + insetY,
                Math.max(1, panelWidth - insetX * 2),
                Math.max(1, panelHeight - insetY * 2),
                sourceWidth, sourceHeight);
    }

    private static int[] contain(
            int x, int y, int availableWidth, int availableHeight,
            int sourceWidth, int sourceHeight) {
        float aspect = Math.max(1, sourceWidth) / (float) Math.max(1, sourceHeight);
        int targetWidth = Math.max(1, availableWidth);
        int targetHeight = Math.max(1, Math.round(targetWidth / aspect));
        if (targetHeight > availableHeight) {
            targetHeight = Math.max(1, availableHeight);
            targetWidth = Math.max(1, Math.round(targetHeight * aspect));
        }
        return new int[]{
                x + (availableWidth - targetWidth) / 2,
                y + (availableHeight - targetHeight) / 2,
                targetWidth, targetHeight
        };
    }

    static int[] getSourceRectForWidthFit(
            String consoleMode, int width, int height, int sourceWidth, int sourceHeight) {
        if (currentLayout == CHASSIS) {
            return ConsoleFrameRenderer.getSourceRectForWidthFit(
                    consoleMode, width, height, sourceWidth, sourceHeight);
        }
        return new int[]{0, 0, Math.max(1, sourceWidth), Math.max(1, sourceHeight)};
    }

    static float[] getSourceCropForWidthFit(
            String consoleMode, int width, int height, int sourceWidth, int sourceHeight) {
        if (currentLayout == CHASSIS) {
            return ConsoleFrameRenderer.getSourceCropForWidthFit(
                    consoleMode, width, height, sourceWidth, sourceHeight);
        }
        return new float[]{0f, 0f, 1f, 1f};
    }

    static void draw(
            Canvas canvas, String mode, int viewWidth, int viewHeight,
            int unusedLeft, int unusedTop, int unusedWidth, int unusedHeight) {
        draw(canvas, mode, viewWidth, viewHeight);
    }

    static void draw(Canvas canvas, String consoleMode, int width, int height) {
        if (currentLayout == CHASSIS) {
            ConsoleFrameRenderer.draw(canvas, consoleMode, width, height);
            return;
        }
        canvas.drawColor(Color.BLACK);
        if (currentLayout == FULLSCREEN) {
            return;
        }
        drawSgbSurround(canvas, Math.max(1, width), Math.max(1, height));
    }

    private static void drawSgbSurround(Canvas canvas, int w, int h) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setColor(Color.rgb(169, 150, 221));
        canvas.drawRect(0, 0, w, h, p);
        float left = w * 0.075f;
        float top = h * (w > h ? 0.15f : 0.10f);
        float right = w - left;
        float bottom = h - top;
        float r = Math.min(w, h) * 0.04f;
        p.setColor(Color.rgb(18, 15, 53));
        canvas.drawRoundRect(new RectF(left, top, right, bottom), r, r, p);
        p.setStyle(Paint.Style.STROKE);
        p.setStrokeWidth(Math.max(2f, Math.min(w, h) * 0.01f));
        p.setColor(Color.rgb(71, 55, 145));
        canvas.drawRoundRect(new RectF(left + 5, top + 5, right - 5, bottom - 5),
                r, r, p);
        p.setStyle(Paint.Style.FILL);
        float x1 = left + (right - left) * 0.04f;
        float x2 = right - (right - left) * 0.04f;
        float y1 = top + Math.max(4f, (bottom - top) * 0.045f);
        float stripe = Math.max(2f, Math.min(w, h) * 0.006f);
        p.setColor(Color.rgb(219, 65, 99));
        canvas.drawRect(x1, y1, x2, y1 + stripe, p);
        p.setColor(Color.rgb(71, 65, 223));
        canvas.drawRect(x1, y1 + stripe * 2f, x2, y1 + stripe * 3f, p);
        float centerY = bottom + (h - bottom) * 0.50f;
        p.setColor(Color.rgb(37, 33, 105));
        p.setTextAlign(Paint.Align.CENTER);
        p.setFakeBoldText(true);
        p.setTextSize(Math.max(12f, Math.min(w * 0.078f, (h - bottom) * 0.32f)));
        canvas.drawText("SUPER GAME BOY", w * 0.5f, Math.min(h - 4, centerY), p);
    }
}
