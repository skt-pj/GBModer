package com.sktpj.gbmoder;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;

/** Draws the supplied handheld image and maps content into its physical LCD window. */
final class ConsoleFrameRenderer {
    static final int VIDEO_FRAME_SIZE = 512;

    private static final float[] GB_SCREEN = {0.240000f, 0.144681f, 0.760000f, 0.440851f};
    private static final float[] GBC_SCREEN = {0.214286f, 0.138865f, 0.791429f, 0.466376f};
    private static final float[] GBA_SCREEN = {0.300826f, 0.211921f, 0.700000f, 0.667550f};
    private static final float[] DS_SCREEN = {0.275238f, 0.095495f, 0.736190f, 0.423423f};

    private ConsoleFrameRenderer() {
    }

    static void draw(
            Canvas canvas,
            String mode,
            int viewWidth,
            int viewHeight,
            int ignoredScreenLeft,
            int ignoredScreenTop,
            int ignoredScreenWidth,
            int ignoredScreenHeight
    ) {
        draw(canvas, mode, viewWidth, viewHeight);
    }

    static void draw(Canvas canvas, String mode, int viewWidth, int viewHeight) {
        int width = Math.max(1, viewWidth);
        int height = Math.max(1, viewHeight);
        canvas.drawColor(Color.WHITE);

        Bitmap chassis = ChassisImageAssets.get(mode);
        RectF destination = getImageRect(chassis, width, height);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        canvas.drawBitmap(
                chassis,
                new Rect(0, 0, chassis.getWidth(), chassis.getHeight()),
                destination,
                paint
        );
    }

    /** The physical LCD itself. It is never reduced to a mode/resolution aspect ratio. */
    static int[] getScreenRect(String mode, int viewWidth, int viewHeight) {
        Bitmap chassis = ChassisImageAssets.get(mode);
        RectF raw = getRawScreenRect(mode, chassis, Math.max(1, viewWidth), Math.max(1, viewHeight));
        return toIntRect(raw);
    }

    /**
     * Fits a source window inside the physical LCD while preserving the source aspect ratio.
     * This is the only rectangle into which live/game/video content may be drawn.
     */
    static int[] getContentRect(
            String mode,
            int viewWidth,
            int viewHeight,
            int contentWidth,
            int contentHeight
    ) {
        Bitmap chassis = ChassisImageAssets.get(mode);
        RectF raw = getRawScreenRect(mode, chassis, Math.max(1, viewWidth), Math.max(1, viewHeight));
        float contentAspect = Math.max(1, contentWidth) / (float) Math.max(1, contentHeight);
        return toIntRect(fitAspect(raw, contentAspect));
    }

    /** Fits the pixel grid into a requested resolution box without changing source aspect. */
    static int[] fitPixelGrid(
            int sourceWidth,
            int sourceHeight,
            int maxWidth,
            int maxHeight
    ) {
        int srcWidth = Math.max(1, sourceWidth);
        int srcHeight = Math.max(1, sourceHeight);
        int boxWidth = Math.max(1, maxWidth);
        int boxHeight = Math.max(1, maxHeight);
        float sourceAspect = srcWidth / (float) srcHeight;

        int width = boxWidth;
        int height = Math.max(1, Math.round(width / sourceAspect));
        if (height > boxHeight) {
            height = boxHeight;
            width = Math.max(1, Math.round(height * sourceAspect));
        }
        return new int[]{Math.max(1, width), Math.max(1, height)};
    }

    /** Produces a video frame with the source aspect preserved inside the physical LCD. */
    static Bitmap composeVideoFrame(Bitmap content, String mode) {
        Bitmap result = Bitmap.createBitmap(
                VIDEO_FRAME_SIZE,
                VIDEO_FRAME_SIZE,
                Bitmap.Config.ARGB_8888
        );
        Canvas canvas = new Canvas(result);
        draw(canvas, mode, VIDEO_FRAME_SIZE, VIDEO_FRAME_SIZE);

        int[] destination = getContentRect(
                mode,
                VIDEO_FRAME_SIZE,
                VIDEO_FRAME_SIZE,
                content.getWidth(),
                content.getHeight()
        );
        Paint contentPaint = new Paint();
        contentPaint.setAntiAlias(false);
        contentPaint.setFilterBitmap(false);
        canvas.drawBitmap(
                content,
                new Rect(0, 0, content.getWidth(), content.getHeight()),
                new Rect(
                        destination[0],
                        destination[1],
                        destination[0] + destination[2],
                        destination[1] + destination[3]
                ),
                contentPaint
        );
        return result;
    }

    private static RectF getRawScreenRect(
            String mode,
            Bitmap chassis,
            int viewWidth,
            int viewHeight
    ) {
        RectF image = getImageRect(chassis, viewWidth, viewHeight);
        float[] slot = screenSlot(mode);
        return new RectF(
                image.left + image.width() * slot[0],
                image.top + image.height() * slot[1],
                image.left + image.width() * slot[2],
                image.top + image.height() * slot[3]
        );
    }

    private static RectF getImageRect(Bitmap chassis, int viewWidth, int viewHeight) {
        float sourceAspect = chassis.getWidth() / (float) Math.max(1, chassis.getHeight());
        float width = viewWidth;
        float height = width / sourceAspect;
        if (height > viewHeight) {
            height = viewHeight;
            width = height * sourceAspect;
        }
        float left = (viewWidth - width) * 0.5f;
        float top = (viewHeight - height) * 0.5f;
        return new RectF(left, top, left + width, top + height);
    }

    private static RectF fitAspect(RectF slot, float aspect) {
        float safeAspect = Math.max(0.01f, aspect);
        float width = slot.width();
        float height = width / safeAspect;
        if (height > slot.height()) {
            height = slot.height();
            width = height * safeAspect;
        }
        float left = slot.left + (slot.width() - width) * 0.5f;
        float top = slot.top + (slot.height() - height) * 0.5f;
        return new RectF(left, top, left + width, top + height);
    }

    private static int[] toIntRect(RectF rect) {
        return new int[]{
                Math.round(rect.left),
                Math.round(rect.top),
                Math.max(1, Math.round(rect.width())),
                Math.max(1, Math.round(rect.height()))
        };
    }

    private static float[] screenSlot(String mode) {
        if (GameBoyFilter.MODE_GBC.equals(mode)) {
            return GBC_SCREEN;
        }
        if (GameBoyFilter.MODE_GBA.equals(mode)) {
            return GBA_SCREEN;
        }
        if (GameBoyFilter.MODE_DS.equals(mode)) {
            return DS_SCREEN;
        }
        return GB_SCREEN;
    }
}
