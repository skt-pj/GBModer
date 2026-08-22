package com.sktpj.gbmoder;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;

final class ConsoleFrameRenderer {
    static final int STYLE_GB = 0;
    static final int STYLE_GBC = 1;
    static final int STYLE_GBA = 2;
    static final int STYLE_DS = 3;

    static final class FrameSpec {
        final int outputWidth;
        final int outputHeight;
        final int screenLeft;
        final int screenTop;
        final int screenWidth;
        final int screenHeight;
        final int style;

        FrameSpec(
                int outputWidth,
                int outputHeight,
                int screenLeft,
                int screenTop,
                int screenWidth,
                int screenHeight,
                int style
        ) {
            this.outputWidth = outputWidth;
            this.outputHeight = outputHeight;
            this.screenLeft = screenLeft;
            this.screenTop = screenTop;
            this.screenWidth = screenWidth;
            this.screenHeight = screenHeight;
            this.style = style;
        }
    }

    private ConsoleFrameRenderer() {
    }

    static boolean isFixedResolution(String resolution) {
        String safe = GameBoyFilter.safeResolution(resolution);
        return GameBoyFilter.RESOLUTION_GB.equals(safe)
                || GameBoyFilter.RESOLUTION_GBC.equals(safe)
                || GameBoyFilter.RESOLUTION_GBA.equals(safe)
                || GameBoyFilter.RESOLUTION_DS.equals(safe);
    }

    static FrameSpec getSpec(String resolution, int screenWidth, int screenHeight) {
        int width = Math.max(2, screenWidth);
        int height = Math.max(2, screenHeight);
        String safe = GameBoyFilter.safeResolution(resolution);

        if (GameBoyFilter.RESOLUTION_GBC.equals(safe)) {
            int side = 30;
            int top = 32;
            int bottom = 96;
            return new FrameSpec(
                    even(width + side * 2),
                    even(height + top + bottom),
                    side,
                    top,
                    width,
                    height,
                    STYLE_GBC
            );
        }

        if (GameBoyFilter.RESOLUTION_GBA.equals(safe)) {
            boolean portraitScreen = height > width;
            int side = portraitScreen ? 52 : 68;
            int top = portraitScreen ? 42 : 28;
            int bottom = portraitScreen ? 42 : 28;
            return new FrameSpec(
                    even(width + side * 2),
                    even(height + top + bottom),
                    side,
                    top,
                    width,
                    height,
                    STYLE_GBA
            );
        }

        if (GameBoyFilter.RESOLUTION_DS.equals(safe)) {
            int side = 28;
            int top = 26;
            int hingeAndGap = 48;
            int lowerPanel = Math.max(118, height);
            return new FrameSpec(
                    even(width + side * 2),
                    even(top + height + hingeAndGap + lowerPanel + 34),
                    side,
                    top,
                    width,
                    height,
                    STYLE_DS
            );
        }

        int side = 32;
        int top = 36;
        int bottom = 112;
        return new FrameSpec(
                even(width + side * 2),
                even(height + top + bottom),
                side,
                top,
                width,
                height,
                STYLE_GB
        );
    }

    static Bitmap compose(Bitmap screen, String resolution) {
        if (screen == null || screen.isRecycled() || !isFixedResolution(resolution)) {
            return screen;
        }

        FrameSpec spec = getSpec(resolution, screen.getWidth(), screen.getHeight());
        Bitmap output = Bitmap.createBitmap(
                spec.outputWidth,
                spec.outputHeight,
                Bitmap.Config.ARGB_8888
        );
        Canvas canvas = new Canvas(output);
        drawBody(canvas, spec);

        Paint screenPaint = new Paint();
        screenPaint.setAntiAlias(false);
        screenPaint.setFilterBitmap(false);
        canvas.drawBitmap(
                screen,
                null,
                new Rect(
                        spec.screenLeft,
                        spec.screenTop,
                        spec.screenLeft + spec.screenWidth,
                        spec.screenTop + spec.screenHeight
                ),
                screenPaint
        );
        return output;
    }

    static Rect fitCenterRect(int contentWidth, int contentHeight, int containerWidth, int containerHeight) {
        int cw = Math.max(1, contentWidth);
        int ch = Math.max(1, contentHeight);
        int vw = Math.max(1, containerWidth);
        int vh = Math.max(1, containerHeight);
        float scale = Math.min(vw / (float) cw, vh / (float) ch);
        int width = Math.max(1, Math.round(cw * scale));
        int height = Math.max(1, Math.round(ch * scale));
        int left = (vw - width) / 2;
        int top = (vh - height) / 2;
        return new Rect(left, top, left + width, top + height);
    }

    private static void drawBody(Canvas canvas, FrameSpec spec) {
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        canvas.drawColor(Color.rgb(18, 18, 20));

        int bodyColor;
        int bezelColor = Color.rgb(45, 47, 52);
        int controlColor = Color.rgb(42, 43, 47);
        int accentColor;

        if (spec.style == STYLE_GBC) {
            bodyColor = Color.rgb(185, 178, 218);
            accentColor = Color.rgb(142, 48, 105);
        } else if (spec.style == STYLE_GBA) {
            bodyColor = Color.rgb(92, 103, 145);
            accentColor = Color.rgb(64, 68, 86);
        } else if (spec.style == STYLE_DS) {
            bodyColor = Color.rgb(112, 115, 122);
            accentColor = Color.rgb(62, 64, 70);
        } else {
            bodyColor = Color.rgb(195, 191, 173);
            accentColor = Color.rgb(126, 46, 91);
        }

        paint.setColor(bodyColor);
        canvas.drawRoundRect(
                new RectF(4, 4, spec.outputWidth - 4, spec.outputHeight - 4),
                22,
                22,
                paint
        );

        if (spec.style == STYLE_DS) {
            drawDsBody(canvas, paint, spec, bezelColor, controlColor, accentColor);
        } else if (spec.style == STYLE_GBA) {
            drawGbaBody(canvas, paint, spec, bezelColor, controlColor, accentColor);
        } else {
            drawVerticalBody(canvas, paint, spec, bezelColor, controlColor, accentColor);
        }
    }

    private static void drawVerticalBody(
            Canvas canvas,
            Paint paint,
            FrameSpec spec,
            int bezelColor,
            int controlColor,
            int accentColor
    ) {
        paint.setColor(bezelColor);
        canvas.drawRoundRect(
                new RectF(
                        spec.screenLeft - 10,
                        spec.screenTop - 10,
                        spec.screenLeft + spec.screenWidth + 10,
                        spec.screenTop + spec.screenHeight + 10
                ),
                12,
                12,
                paint
        );

        int controlsTop = spec.screenTop + spec.screenHeight + 30;
        int dpadX = Math.max(18, spec.outputWidth / 4 - 16);
        int dpadY = controlsTop + 14;
        paint.setColor(controlColor);
        canvas.drawRoundRect(new RectF(dpadX, dpadY + 12, dpadX + 48, dpadY + 28), 5, 5, paint);
        canvas.drawRoundRect(new RectF(dpadX + 16, dpadY, dpadX + 32, dpadY + 40), 5, 5, paint);

        paint.setColor(accentColor);
        float buttonY = dpadY + 14;
        float buttonX = spec.outputWidth * 0.70f;
        canvas.drawCircle(buttonX, buttonY + 8, 12, paint);
        canvas.drawCircle(buttonX + 30, buttonY - 2, 12, paint);

        paint.setColor(Color.rgb(82, 82, 86));
        int barY = Math.min(spec.outputHeight - 26, dpadY + 54);
        canvas.drawRoundRect(new RectF(spec.outputWidth / 2f - 28, barY, spec.outputWidth / 2f - 4, barY + 6), 3, 3, paint);
        canvas.drawRoundRect(new RectF(spec.outputWidth / 2f + 4, barY, spec.outputWidth / 2f + 28, barY + 6), 3, 3, paint);

        int speakerX = spec.outputWidth - 52;
        int speakerY = Math.min(spec.outputHeight - 36, barY + 18);
        paint.setStrokeWidth(3);
        paint.setColor(Color.rgb(116, 112, 106));
        for (int i = 0; i < 4; i++) {
            canvas.drawLine(speakerX + i * 7, speakerY, speakerX - 8 + i * 7, speakerY + 16, paint);
        }
    }

    private static void drawGbaBody(
            Canvas canvas,
            Paint paint,
            FrameSpec spec,
            int bezelColor,
            int controlColor,
            int accentColor
    ) {
        paint.setColor(bezelColor);
        canvas.drawRoundRect(
                new RectF(
                        spec.screenLeft - 9,
                        spec.screenTop - 9,
                        spec.screenLeft + spec.screenWidth + 9,
                        spec.screenTop + spec.screenHeight + 9
                ),
                12,
                12,
                paint
        );

        int centerY = spec.screenTop + spec.screenHeight / 2;
        int dpadX = 18;
        int dpadY = centerY - 20;
        paint.setColor(controlColor);
        canvas.drawRoundRect(new RectF(dpadX, dpadY + 12, dpadX + 44, dpadY + 28), 5, 5, paint);
        canvas.drawRoundRect(new RectF(dpadX + 14, dpadY, dpadX + 30, dpadY + 40), 5, 5, paint);

        paint.setColor(accentColor);
        int buttonX = spec.outputWidth - 50;
        canvas.drawCircle(buttonX - 10, centerY + 9, 11, paint);
        canvas.drawCircle(buttonX + 14, centerY - 8, 11, paint);

        paint.setColor(Color.rgb(55, 58, 74));
        int startY = Math.min(spec.outputHeight - 18, spec.screenTop + spec.screenHeight + 14);
        canvas.drawRoundRect(new RectF(spec.outputWidth / 2f - 25, startY, spec.outputWidth / 2f - 5, startY + 5), 3, 3, paint);
        canvas.drawRoundRect(new RectF(spec.outputWidth / 2f + 5, startY, spec.outputWidth / 2f + 25, startY + 5), 3, 3, paint);
    }

    private static void drawDsBody(
            Canvas canvas,
            Paint paint,
            FrameSpec spec,
            int bezelColor,
            int controlColor,
            int accentColor
    ) {
        paint.setColor(bezelColor);
        canvas.drawRoundRect(
                new RectF(
                        spec.screenLeft - 8,
                        spec.screenTop - 8,
                        spec.screenLeft + spec.screenWidth + 8,
                        spec.screenTop + spec.screenHeight + 8
                ),
                10,
                10,
                paint
        );

        int hingeY = spec.screenTop + spec.screenHeight + 22;
        paint.setColor(Color.rgb(70, 72, 78));
        canvas.drawRoundRect(new RectF(20, hingeY, spec.outputWidth - 20, hingeY + 10), 5, 5, paint);

        int lowerTop = hingeY + 28;
        int lowerBottom = spec.outputHeight - 28;
        int lowerHeight = Math.max(48, lowerBottom - lowerTop);
        int dummyLeft = Math.max(48, spec.outputWidth / 2 - Math.min(spec.screenWidth, 176) / 2);
        int dummyRight = spec.outputWidth - dummyLeft;
        int dummyTop = lowerTop + 16;
        int dummyBottom = Math.min(lowerBottom - 22, dummyTop + Math.min(lowerHeight - 42, 120));
        paint.setColor(Color.rgb(64, 66, 72));
        canvas.drawRoundRect(new RectF(dummyLeft, dummyTop, dummyRight, dummyBottom), 8, 8, paint);
        paint.setColor(Color.rgb(38, 40, 44));
        canvas.drawRoundRect(new RectF(dummyLeft + 7, dummyTop + 7, dummyRight - 7, dummyBottom - 7), 5, 5, paint);

        int controlY = Math.min(lowerBottom - 38, dummyBottom + 16);
        paint.setColor(controlColor);
        canvas.drawRoundRect(new RectF(24, controlY + 10, 62, controlY + 24), 4, 4, paint);
        canvas.drawRoundRect(new RectF(36, controlY, 50, controlY + 34), 4, 4, paint);

        paint.setColor(accentColor);
        canvas.drawCircle(spec.outputWidth - 48, controlY + 18, 9, paint);
        canvas.drawCircle(spec.outputWidth - 28, controlY + 5, 9, paint);
    }

    private static int even(int value) {
        int safe = Math.max(2, value);
        return (safe & 1) == 0 ? safe : safe + 1;
    }
}
