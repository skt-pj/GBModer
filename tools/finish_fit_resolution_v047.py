#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_fit_resolution_v047.py <generated_java_root>")

root = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# Resolution aliases keep the existing fixed console screen sizes, but select a
# fit-inside policy instead of the existing center-crop policy.
filter_path = root / "GameBoyFilter.java"
filter_text = filter_path.read_text()
filter_text = replace_once(
    filter_text,
    '    public static final String RESOLUTION_DS = "ds";\n',
    '    public static final String RESOLUTION_DS = "ds";\n'
    '    public static final String RESOLUTION_GB_FIT = "gb_fit";\n'
    '    public static final String RESOLUTION_GBC_FIT = "gbc_fit";\n'
    '    public static final String RESOLUTION_GBA_FIT = "gba_fit";\n'
    '    public static final String RESOLUTION_DS_FIT = "ds_fit";\n',
    "fit resolution aliases",
)
filter_text = replace_once(
    filter_text,
    '''        if (RESOLUTION_GBC.equals(requestedResolution)) {
            return RESOLUTION_GBC;
        }
        if (RESOLUTION_GBA.equals(requestedResolution)) {
            return RESOLUTION_GBA;
        }
        if (RESOLUTION_DS.equals(requestedResolution)) {
            return RESOLUTION_DS;
        }
''',
    '''        if (RESOLUTION_GB_FIT.equals(requestedResolution)) {
            return RESOLUTION_GB;
        }
        if (RESOLUTION_GBC.equals(requestedResolution) || RESOLUTION_GBC_FIT.equals(requestedResolution)) {
            return RESOLUTION_GBC;
        }
        if (RESOLUTION_GBA.equals(requestedResolution) || RESOLUTION_GBA_FIT.equals(requestedResolution)) {
            return RESOLUTION_GBA;
        }
        if (RESOLUTION_DS.equals(requestedResolution) || RESOLUTION_DS_FIT.equals(requestedResolution)) {
            return RESOLUTION_DS;
        }
''',
    "fit aliases normalize to console base resolution",
)
fit_helpers = r'''    public static boolean isFitResolution(String resolution) {
        return RESOLUTION_GB_FIT.equals(resolution)
                || RESOLUTION_GBC_FIT.equals(resolution)
                || RESOLUTION_GBA_FIT.equals(resolution)
                || RESOLUTION_DS_FIT.equals(resolution);
    }

    public static int[] getFitDestinationBounds(
            String resolution,
            int sourceWidth,
            int sourceHeight,
            int targetWidth,
            int targetHeight
    ) {
        int sw = Math.max(1, sourceWidth);
        int sh = Math.max(1, sourceHeight);
        int tw = Math.max(1, targetWidth);
        int th = Math.max(1, targetHeight);
        if (!isFitResolution(resolution)) {
            return new int[]{0, 0, tw, th};
        }

        double scale = Math.min(tw / (double) sw, th / (double) sh);
        int width = Math.max(1, Math.min(tw, (int) Math.round(sw * scale)));
        int height = Math.max(1, Math.min(th, (int) Math.round(sh * scale)));
        int left = (tw - width) / 2;
        int top = (th - height) / 2;
        return new int[]{left, top, left + width, top + height};
    }

'''
filter_text = replace_once(
    filter_text,
    "    public static boolean isFixedAspectResolution(String resolution) {\n",
    fit_helpers + "    public static boolean isFixedAspectResolution(String resolution) {\n",
    "fit geometry helpers",
)
filter_text = replace_once(
    filter_text,
    '''        if (!isFixedAspectResolution(resolution)) {
            return new int[]{0, 0, width, height};
        }
''',
    '''        if (isFitResolution(resolution) || !isFixedAspectResolution(resolution)) {
            return new int[]{0, 0, width, height};
        }
''',
    "fit mode disables source crop",
)
filter_path.write_text(filter_text)


# Photo conversion and CPU video fallback render the complete source into the
# largest rectangle that fits inside the selected console screen.
converter_path = root / "MediaFileConverter.java"
converter = converter_path.read_text()
converter = replace_once(
    converter,
    '''        Bitmap scaled = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(scaled);
        Paint paint = new Paint();
        paint.setFilterBitmap(false);
        paint.setAntiAlias(false);
        canvas.drawBitmap(
                source,
                new Rect(crop[0], crop[1], crop[2], crop[3]),
                new Rect(0, 0, width, height),
                paint
        );
''',
    '''        Bitmap scaled = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(scaled);
        Paint paint = new Paint();
        paint.setFilterBitmap(false);
        paint.setAntiAlias(false);
        int[] destination = GameBoyFilter.getFitDestinationBounds(
                options.resolution,
                crop[2] - crop[0],
                crop[3] - crop[1],
                width,
                height
        );
        canvas.drawColor(android.graphics.Color.BLACK);
        canvas.drawBitmap(
                source,
                new Rect(crop[0], crop[1], crop[2], crop[3]),
                new Rect(destination[0], destination[1], destination[2], destination[3]),
                paint
        );
''',
    "CPU conversion fit-inside destination",
)
converter_path.write_text(converter)


# MediaProjection live route uses the same fit geometry before filtering and
# before composing the handheld body.
capture_path = root / "FilterCaptureService.java"
capture = capture_path.read_text()
capture = replace_once(
    capture,
    '''            int[] crop = GameBoyFilter.getCenterCropBounds(resolution, sourceWidth, sourceHeight);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    captureBitmap,
                    new Rect(crop[0], crop[1], crop[2], crop[3]),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
''',
    '''            int[] crop = GameBoyFilter.getCenterCropBounds(resolution, sourceWidth, sourceHeight);
            int[] destination = GameBoyFilter.getFitDestinationBounds(
                    resolution,
                    crop[2] - crop[0],
                    crop[3] - crop[1],
                    targetWidth,
                    targetHeight
            );
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    captureBitmap,
                    new Rect(crop[0], crop[1], crop[2], crop[3]),
                    new Rect(destination[0], destination[1], destination[2], destination[3]),
                    downsamplePaint
            );
''',
    "MediaProjection fit-inside destination",
)
capture_path.write_text(capture)


# Android 14+ accessibility screenshot live route mirrors MediaProjection.
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()
access = replace_once(
    access,
    '''            int[] crop = GameBoyFilter.getCenterCropBounds(
                    windowFilterResolution,
                    source.getWidth(),
                    source.getHeight()
            );
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    source,
                    new Rect(crop[0], crop[1], crop[2], crop[3]),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
''',
    '''            int[] crop = GameBoyFilter.getCenterCropBounds(
                    windowFilterResolution,
                    source.getWidth(),
                    source.getHeight()
            );
            int[] destination = GameBoyFilter.getFitDestinationBounds(
                    windowFilterResolution,
                    crop[2] - crop[0],
                    crop[3] - crop[1],
                    targetWidth,
                    targetHeight
            );
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    source,
                    new Rect(crop[0], crop[1], crop[2], crop[3]),
                    new Rect(destination[0], destination[1], destination[2], destination[3]),
                    downsamplePaint
            );
''',
    "accessibility fit-inside destination",
)
access_path.write_text(access)


# GPU video keeps the decoder-Surface -> OpenGL -> encoder-Surface pipeline.
# Fit aliases use the full source texture and shrink only the screen viewport;
# crop aliases continue filling the complete fixed-resolution screen.
video_path = root / "VideoGpuConverter.java"
video = video_path.read_text()
video = replace_once(
    video,
    '''        private final boolean consoleFrame;
        private final ConsoleFrameRenderer.FrameSpec frameSpec;
        private final MediaFileConverter.Options options;
''',
    '''        private final boolean consoleFrame;
        private final ConsoleFrameRenderer.FrameSpec frameSpec;
        private final int contentLeft;
        private final int contentTop;
        private final int contentWidth;
        private final int contentHeight;
        private final MediaFileConverter.Options options;
''',
    "GPU fit viewport fields",
)
video = replace_once(
    video,
    '''            int displaySourceHeight = (rotation == 90 || rotation == 270)
                    ? sourceWidth
                    : sourceHeight;
            int[] crop = GameBoyFilter.getCenterCropBounds(
''',
    '''            int displaySourceHeight = (rotation == 90 || rotation == 270)
                    ? sourceWidth
                    : sourceHeight;
            int[] destination = GameBoyFilter.getFitDestinationBounds(
                    options.resolution,
                    displaySourceWidth,
                    displaySourceHeight,
                    targetWidth,
                    targetHeight
            );
            this.contentLeft = destination[0];
            this.contentTop = destination[1];
            this.contentWidth = Math.max(1, destination[2] - destination[0]);
            this.contentHeight = Math.max(1, destination[3] - destination[1]);
            int[] crop = GameBoyFilter.getCenterCropBounds(
''',
    "GPU fit viewport geometry",
)
video = replace_once(
    video,
    '''            if (framebuffer != 0 || !consoleFrame) {
                GLES20.glViewport(0, 0, targetWidth, targetHeight);
            } else {
                GLES20.glViewport(
                        frameSpec.screenLeft,
                        outputHeight - frameSpec.screenTop - targetHeight,
                        targetWidth,
                        targetHeight
                );
            }
''',
    '''            if (framebuffer != 0 || !consoleFrame) {
                GLES20.glViewport(0, 0, targetWidth, targetHeight);
            } else {
                GLES20.glViewport(
                        frameSpec.screenLeft + contentLeft,
                        outputHeight - frameSpec.screenTop - contentTop - contentHeight,
                        contentWidth,
                        contentHeight
                );
            }
''',
    "GPU external fit viewport",
)
video = replace_once(
    video,
    '''            if (consoleFrame) {
                GLES20.glViewport(
                        frameSpec.screenLeft,
                        outputHeight - frameSpec.screenTop - targetHeight,
                        targetWidth,
                        targetHeight
                );
            } else {
''',
    '''            if (consoleFrame) {
                GLES20.glViewport(
                        frameSpec.screenLeft + contentLeft,
                        outputHeight - frameSpec.screenTop - contentTop - contentHeight,
                        contentWidth,
                        contentHeight
                );
            } else {
''',
    "GPU lookup fit viewport",
)
video = replace_once(
    video,
    '''            fillRect(
                    frameSpec.screenLeft - 10,
                    frameSpec.screenTop - 10,
                    frameSpec.screenWidth + 20,
                    frameSpec.screenHeight + 20,
                    45, 47, 52
            );

            if (frameSpec.style == ConsoleFrameRenderer.STYLE_GBA) {
''',
    '''            fillRect(
                    frameSpec.screenLeft - 10,
                    frameSpec.screenTop - 10,
                    frameSpec.screenWidth + 20,
                    frameSpec.screenHeight + 20,
                    45, 47, 52
            );
            if (GameBoyFilter.MODE_GB.equals(options.mode)) {
                fillRect(
                        frameSpec.screenLeft,
                        frameSpec.screenTop,
                        frameSpec.screenWidth,
                        frameSpec.screenHeight,
                        15, 56, 15
                );
            } else {
                fillRect(
                        frameSpec.screenLeft,
                        frameSpec.screenTop,
                        frameSpec.screenWidth,
                        frameSpec.screenHeight,
                        0, 0, 0
                );
            }

            if (frameSpec.style == ConsoleFrameRenderer.STYLE_GBA) {
''',
    "GPU fit letterbox background",
)
video_path.write_text(video)


# Live-mode UI positions 24..27 are the four fit-inside fixed presets.
main_path = root / "MainActivity.java"
main = main_path.read_text()
main = replace_once(
    main,
    '''        if (position == 23) return GameBoyFilter.RESOLUTION_NATIVE;
        return GameBoyFilter.RESOLUTION_GB;
''',
    '''        if (position == 23) return GameBoyFilter.RESOLUTION_NATIVE;
        if (position == 24) return GameBoyFilter.RESOLUTION_GB_FIT;
        if (position == 25) return GameBoyFilter.RESOLUTION_GBC_FIT;
        if (position == 26) return GameBoyFilter.RESOLUTION_GBA_FIT;
        if (position == 27) return GameBoyFilter.RESOLUTION_DS_FIT;
        return GameBoyFilter.RESOLUTION_GB;
''',
    "live fit resolution positions",
)
main_path.write_text(main)

print("v0.1.47 fixed presets now support full-content fit-inside resolution", flush=True)
