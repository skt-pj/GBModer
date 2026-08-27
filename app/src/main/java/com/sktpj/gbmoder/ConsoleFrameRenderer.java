package com.sktpj.gbmoder;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Typeface;

/** Draws the selected handheld identity only in the area outside the filtered screen. */
final class ConsoleFrameRenderer {
    private ConsoleFrameRenderer() {
    }

    static void draw(
            Canvas canvas,
            String mode,
            int viewWidth,
            int viewHeight,
            int screenLeft,
            int screenTop,
            int screenWidth,
            int screenHeight
    ) {
        int width = Math.max(1, viewWidth);
        int height = Math.max(1, viewHeight);
        int right = screenLeft + Math.max(1, screenWidth);
        int bottom = screenTop + Math.max(1, screenHeight);
        float unit = Math.max(4.0f, Math.min(width, height) * 0.018f);

        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        int bodyColor;
        int bezelColor;
        int accentColor;
        String label;

        if (GameBoyFilter.MODE_GBC.equals(mode)) {
            bodyColor = Color.rgb(103, 73, 154);
            bezelColor = Color.rgb(35, 29, 52);
            accentColor = Color.rgb(217, 91, 151);
            label = "GBC";
        } else if (GameBoyFilter.MODE_GBA.equals(mode)) {
            bodyColor = Color.rgb(77, 70, 142);
            bezelColor = Color.rgb(31, 31, 48);
            accentColor = Color.rgb(178, 176, 223);
            label = "GBA";
        } else if (GameBoyFilter.MODE_DS.equals(mode)) {
            bodyColor = Color.rgb(190, 193, 196);
            bezelColor = Color.rgb(43, 45, 48);
            accentColor = Color.rgb(100, 104, 108);
            label = "DS";
        } else {
            bodyColor = Color.rgb(204, 202, 193);
            bezelColor = Color.rgb(31, 38, 61);
            accentColor = Color.rgb(182, 42, 65);
            label = "GB";
        }

        canvas.drawColor(bodyColor);

        // The filtered frame is painted after this method. Drawing the bezel first makes
        // only the portion outside the screen remain visible, so game content is never covered.
        float bezelPad = unit * 1.9f;
        RectF bezel = new RectF(
                screenLeft - bezelPad,
                screenTop - bezelPad,
                right + bezelPad,
                bottom + bezelPad
        );
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(bezelColor);
        canvas.drawRoundRect(bezel, unit * 1.4f, unit * 1.4f, paint);

        float topSpace = Math.max(0, screenTop);
        float bottomSpace = Math.max(0, height - bottom);
        float leftSpace = Math.max(0, screenLeft);
        float rightSpace = Math.max(0, width - right);

        if (GameBoyFilter.MODE_GB.equals(mode)) {
            drawGbDetails(canvas, paint, width, height, screenLeft, screenTop, right, bottom,
                    topSpace, bottomSpace, leftSpace, unit);
        } else if (GameBoyFilter.MODE_GBC.equals(mode)) {
            drawGbcDetails(canvas, paint, width, height, screenLeft, screenTop, right, bottom,
                    bottomSpace, unit);
        } else if (GameBoyFilter.MODE_GBA.equals(mode)) {
            drawGbaDetails(canvas, paint, width, height, screenLeft, screenTop, right, bottom,
                    bottomSpace, unit);
        } else {
            drawDsDetails(canvas, paint, width, height, screenLeft, screenTop, right, bottom,
                    topSpace, bottomSpace, unit);
        }

        drawModeLabel(canvas, paint, label, accentColor, width, height,
                screenLeft, screenTop, right, bottom,
                topSpace, bottomSpace, leftSpace, rightSpace, unit);
    }

    private static void drawGbDetails(
            Canvas canvas,
            Paint paint,
            int width,
            int height,
            int left,
            int top,
            int right,
            int bottom,
            float topSpace,
            float bottomSpace,
            float leftSpace,
            float unit
    ) {
        if (topSpace > unit * 3.0f) {
            float y = Math.max(unit, top - unit * 1.15f);
            paint.setStrokeWidth(Math.max(2.0f, unit * 0.22f));
            paint.setColor(Color.rgb(190, 49, 74));
            canvas.drawLine(unit * 1.5f, y, width - unit * 1.5f, y, paint);
            paint.setColor(Color.rgb(69, 83, 181));
            canvas.drawLine(unit * 1.5f, y + unit * 0.55f, width - unit * 1.5f, y + unit * 0.55f, paint);
        }

        if (leftSpace > unit * 2.8f) {
            paint.setColor(Color.rgb(210, 47, 43));
            canvas.drawCircle(Math.max(unit * 1.5f, left - unit * 1.15f),
                    top + ((bottom - top) * 0.5f), unit * 0.48f, paint);
        }

        if (bottomSpace > unit * 5.0f) {
            float cy = bottom + Math.min(bottomSpace * 0.52f, unit * 5.8f);
            paint.setColor(Color.rgb(55, 56, 61));
            canvas.drawCircle(width * 0.72f, cy, unit * 1.55f, paint);
            canvas.drawCircle(width * 0.83f, cy - unit * 0.45f, unit * 1.55f, paint);
            paint.setStrokeWidth(unit * 0.8f);
            canvas.drawLine(width * 0.19f, cy, width * 0.31f, cy, paint);
            canvas.drawLine(width * 0.25f, cy - unit * 1.6f, width * 0.25f, cy + unit * 1.6f, paint);
        }
    }

    private static void drawGbcDetails(
            Canvas canvas,
            Paint paint,
            int width,
            int height,
            int left,
            int top,
            int right,
            int bottom,
            float bottomSpace,
            float unit
    ) {
        if (bottomSpace <= unit * 3.0f) {
            return;
        }
        float y = bottom + Math.min(bottomSpace * 0.55f, unit * 5.5f);
        int[] colors = {
                Color.rgb(80, 180, 86),
                Color.rgb(246, 205, 68),
                Color.rgb(239, 88, 84),
                Color.rgb(94, 142, 224),
                Color.rgb(169, 91, 197)
        };
        float start = width * 0.36f;
        float gap = width * 0.075f;
        for (int i = 0; i < colors.length; i++) {
            paint.setColor(colors[i]);
            canvas.drawCircle(start + (gap * i), y, unit * 0.46f, paint);
        }
        paint.setColor(Color.rgb(47, 40, 63));
        canvas.drawCircle(width * 0.78f, y + unit * 1.8f, unit * 1.35f, paint);
        canvas.drawCircle(width * 0.86f, y + unit * 0.8f, unit * 1.35f, paint);
    }

    private static void drawGbaDetails(
            Canvas canvas,
            Paint paint,
            int width,
            int height,
            int left,
            int top,
            int right,
            int bottom,
            float bottomSpace,
            float unit
    ) {
        if (bottomSpace <= unit * 3.0f) {
            return;
        }
        float y = bottom + Math.min(bottomSpace * 0.48f, unit * 5.0f);
        paint.setColor(Color.rgb(42, 38, 76));
        canvas.drawCircle(width * 0.79f, y, unit * 1.35f, paint);
        canvas.drawCircle(width * 0.87f, y - unit * 0.85f, unit * 1.35f, paint);
        paint.setStrokeWidth(unit * 0.75f);
        canvas.drawLine(width * 0.16f, y, width * 0.28f, y, paint);
        canvas.drawLine(width * 0.22f, y - unit * 1.5f, width * 0.22f, y + unit * 1.5f, paint);
    }

    private static void drawDsDetails(
            Canvas canvas,
            Paint paint,
            int width,
            int height,
            int left,
            int top,
            int right,
            int bottom,
            float topSpace,
            float bottomSpace,
            float unit
    ) {
        paint.setColor(Color.rgb(73, 76, 79));
        if (topSpace > unit * 2.5f) {
            canvas.drawRoundRect(new RectF(width * 0.30f, top - unit * 1.55f,
                    width * 0.70f, top - unit * 0.75f), unit * 0.35f, unit * 0.35f, paint);
        }
        if (bottomSpace > unit * 4.0f) {
            float y = bottom + Math.min(bottomSpace * 0.50f, unit * 5.0f);
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(unit * 0.35f);
            canvas.drawRoundRect(new RectF(width * 0.28f, y - unit * 2.0f,
                    width * 0.72f, y + unit * 2.0f), unit * 0.55f, unit * 0.55f, paint);
            paint.setStyle(Paint.Style.FILL);
            canvas.drawCircle(width * 0.82f, y, unit * 0.75f, paint);
            canvas.drawCircle(width * 0.88f, y, unit * 0.75f, paint);
        }
    }

    private static void drawModeLabel(
            Canvas canvas,
            Paint paint,
            String label,
            int accentColor,
            int width,
            int height,
            int left,
            int top,
            int right,
            int bottom,
            float topSpace,
            float bottomSpace,
            float leftSpace,
            float rightSpace,
            float unit
    ) {
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(accentColor);
        paint.setTypeface(Typeface.create(Typeface.MONOSPACE, Typeface.BOLD));
        paint.setTextAlign(Paint.Align.CENTER);
        paint.setTextSize(Math.max(16.0f, unit * 2.6f));

        if (bottomSpace >= topSpace && bottomSpace >= leftSpace && bottomSpace >= rightSpace
                && bottomSpace > unit * 2.5f) {
            canvas.drawText(label, width * 0.5f,
                    Math.min(height - unit, bottom + Math.max(unit * 3.0f, bottomSpace * 0.78f)), paint);
        } else if (topSpace >= leftSpace && topSpace >= rightSpace && topSpace > unit * 2.5f) {
            canvas.drawText(label, width * 0.5f, Math.max(unit * 2.5f, top * 0.45f), paint);
        } else if (leftSpace >= rightSpace && leftSpace > unit * 3.0f) {
            canvas.save();
            canvas.rotate(-90.0f, left * 0.45f, height * 0.5f);
            canvas.drawText(label, left * 0.45f, height * 0.5f, paint);
            canvas.restore();
        } else if (rightSpace > unit * 3.0f) {
            float x = right + (rightSpace * 0.55f);
            canvas.save();
            canvas.rotate(90.0f, x, height * 0.5f);
            canvas.drawText(label, x, height * 0.5f, paint);
            canvas.restore();
        }
    }
}
