package com.sktpj.gbmoder;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;

/**
 * Draws the device surround behind the filtered screen.
 *
 * This intentionally follows the original HTML supplied for GBModer:
 * gameboy_glb_capture_device_modes_transparent_sheet_fixed_ordered_exports.html
 *
 * HTML reference colors:
 * body/page      #8b956d
 * .device        #d4d7c8 -> #b5b8aa
 * .screen-frame  #4b4f40
 * .screen-label  #cfd5bc
 * .lcd-wrapper   #6f7d56
 * .lcd-display   #9bbc0f (the live filtered bitmap is painted over this area)
 */
final class ConsoleFrameRenderer {
    private static final int PAGE_COLOR = Color.rgb(139, 149, 109);      // #8b956d
    private static final int DEVICE_LIGHT = Color.rgb(212, 215, 200);    // #d4d7c8
    private static final int DEVICE_DARK = Color.rgb(181, 184, 170);     // #b5b8aa
    private static final int SCREEN_FRAME = Color.rgb(75, 79, 64);       // #4b4f40
    private static final int SCREEN_LABEL = Color.rgb(207, 213, 188);    // #cfd5bc
    private static final int LCD_WRAPPER = Color.rgb(111, 125, 86);      // #6f7d56
    private static final int LCD_DISPLAY = Color.rgb(155, 188, 15);      // #9bbc0f

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
        final int width = Math.max(1, viewWidth);
        final int height = Math.max(1, viewHeight);
        final int right = screenLeft + Math.max(1, screenWidth);
        final int bottom = screenTop + Math.max(1, screenHeight);
        final float unit = Math.max(3.0f, Math.min(width, height) * 0.0125f);

        final float topSpace = Math.max(0.0f, screenTop);
        final float bottomSpace = Math.max(0.0f, height - bottom);
        final float leftSpace = Math.max(0.0f, screenLeft);
        final float rightSpace = Math.max(0.0f, width - right);

        final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setStyle(Paint.Style.FILL);

        // Original HTML body background.
        canvas.drawColor(PAGE_COLOR);

        // Original .device: rounded light gray shell with a subtle diagonal gradient.
        final float deviceInset = Math.max(1.0f, unit * 0.45f);
        final RectF device = new RectF(
                deviceInset,
                deviceInset,
                width - deviceInset,
                height - deviceInset
        );
        paint.setShader(new LinearGradient(
                device.left,
                device.top,
                device.right,
                device.bottom,
                DEVICE_LIGHT,
                DEVICE_DARK,
                Shader.TileMode.CLAMP
        ));
        canvas.drawRoundRect(device, unit * 1.35f, unit * 1.35f, paint);
        paint.setShader(null);

        // Keep the two nested screen surrounds from the HTML. The actual filtered frame is
        // drawn after this method, so only the parts outside the content remain visible.
        final float availablePad = Math.max(
                0.0f,
                Math.max(Math.max(topSpace, bottomSpace), Math.max(leftSpace, rightSpace))
        );
        final float framePad = Math.max(unit * 0.85f, Math.min(unit * 3.2f, availablePad * 0.46f));
        final float lcdPad = Math.max(unit * 0.42f, framePad * 0.48f);

        final RectF screenFrame = clippedExpandedRect(
                screenLeft,
                screenTop,
                right,
                bottom,
                framePad,
                width,
                height,
                deviceInset
        );
        paint.setColor(SCREEN_FRAME);
        canvas.drawRoundRect(screenFrame, unit * 0.95f, unit * 0.95f, paint);

        final RectF lcdWrapper = clippedExpandedRect(
                screenLeft,
                screenTop,
                right,
                bottom,
                lcdPad,
                width,
                height,
                deviceInset
        );
        paint.setColor(LCD_WRAPPER);
        canvas.drawRoundRect(lcdWrapper, unit * 0.52f, unit * 0.52f, paint);

        // Match the HTML LCD backing. It is normally completely covered by the live bitmap;
        // it only prevents a black seam if integer viewport rounding leaves a pixel exposed.
        paint.setColor(LCD_DISPLAY);
        canvas.drawRect(screenLeft, screenTop, right, bottom, paint);

        drawScreenLabel(
                canvas,
                paint,
                modeLabel(mode),
                width,
                height,
                screenLeft,
                screenTop,
                right,
                bottom,
                topSpace,
                bottomSpace,
                leftSpace,
                rightSpace,
                framePad,
                unit
        );
    }

    private static RectF clippedExpandedRect(
            int left,
            int top,
            int right,
            int bottom,
            float pad,
            int width,
            int height,
            float inset
    ) {
        return new RectF(
                Math.max(inset, left - pad),
                Math.max(inset, top - pad),
                Math.min(width - inset, right + pad),
                Math.min(height - inset, bottom + pad)
        );
    }

    private static String modeLabel(String mode) {
        if (GameBoyFilter.MODE_GBC.equals(mode)) {
            return "DOT MATRIX DISPLAY / 160 x 144 / 15-BIT COLOR";
        }
        if (GameBoyFilter.MODE_GBA.equals(mode)) {
            return "DOT MATRIX DISPLAY / 240 x 160 / 15-BIT COLOR";
        }
        if (GameBoyFilter.MODE_DS.equals(mode)) {
            return "DOT MATRIX DISPLAY / 256 x 192 / DS";
        }
        return "DOT MATRIX DISPLAY / 160 x 144 / 4 SHADES";
    }

    private static void drawScreenLabel(
            Canvas canvas,
            Paint paint,
            String label,
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
            float framePad,
            float unit
    ) {
        final float minLabelSpace = Math.max(unit * 2.2f, 22.0f);
        paint.setShader(null);
        paint.setColor(SCREEN_LABEL);
        paint.setTypeface(Typeface.create(Typeface.MONOSPACE, Typeface.NORMAL));
        paint.setTextAlign(Paint.Align.CENTER);
        paint.setTextSize(Math.max(10.0f, Math.min(16.0f, unit * 1.08f)));

        // The HTML label sits above the LCD. Prefer the same location. On rotations where the
        // top gap is too small, move it to the largest available excess area instead of
        // inventing buttons or handheld controls.
        if (topSpace >= minLabelSpace) {
            final float y = Math.max(unit * 1.35f, top - Math.max(unit * 0.78f, framePad * 0.54f));
            canvas.drawText(label, width * 0.5f, y, paint);
            return;
        }
        if (bottomSpace >= minLabelSpace) {
            final float y = Math.min(height - unit * 0.75f,
                    bottom + Math.max(unit * 1.35f, framePad * 0.88f));
            canvas.drawText(label, width * 0.5f, y, paint);
            return;
        }

        if (leftSpace >= minLabelSpace && leftSpace >= rightSpace) {
            final float x = Math.max(unit * 1.25f, left - Math.max(unit, framePad * 0.72f));
            canvas.save();
            canvas.rotate(-90.0f, x, height * 0.5f);
            canvas.drawText(label, x, height * 0.5f, paint);
            canvas.restore();
            return;
        }
        if (rightSpace >= minLabelSpace) {
            final float x = Math.min(width - unit * 1.25f,
                    right + Math.max(unit, framePad * 0.72f));
            canvas.save();
            canvas.rotate(90.0f, x, height * 0.5f);
            canvas.drawText(label, x, height * 0.5f, paint);
            canvas.restore();
        }
    }
}
