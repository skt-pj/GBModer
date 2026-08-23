#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_aspect_crop_v033.py <generated_src_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# Shared center-crop geometry for fixed GB/GBC/GBA/DS output resolutions.
filter_path = root / "GameBoyFilter.java"
filter_text = filter_path.read_text()
marker = "    private static float getPhoneScale(String resolution) {\n"
helpers = r'''    public static boolean isFixedAspectResolution(String resolution) {
        String safe = safeResolution(resolution);
        return RESOLUTION_GB.equals(safe)
                || RESOLUTION_GBC.equals(safe)
                || RESOLUTION_GBA.equals(safe)
                || RESOLUTION_DS.equals(safe);
    }

    public static int[] getCenterCropBounds(
            String resolution,
            int sourceWidth,
            int sourceHeight
    ) {
        int width = Math.max(1, sourceWidth);
        int height = Math.max(1, sourceHeight);
        if (!isFixedAspectResolution(resolution)) {
            return new int[]{0, 0, width, height};
        }

        int targetWidth = Math.max(1, getTargetWidth(resolution, width));
        int targetHeight = Math.max(1, getTargetHeight(resolution, height));
        long sourceCross = (long) width * targetHeight;
        long targetCross = (long) height * targetWidth;

        int cropWidth = width;
        int cropHeight = height;
        if (sourceCross > targetCross) {
            cropWidth = Math.max(
                    1,
                    Math.min(width, (int) Math.round(height * (targetWidth / (double) targetHeight)))
            );
        } else if (sourceCross < targetCross) {
            cropHeight = Math.max(
                    1,
                    Math.min(height, (int) Math.round(width * (targetHeight / (double) targetWidth)))
            );
        }

        int left = Math.max(0, (width - cropWidth) / 2);
        int top = Math.max(0, (height - cropHeight) / 2);
        return new int[]{left, top, left + cropWidth, top + cropHeight};
    }

    public static int getCenterCropWorkingWidth(
            String resolution,
            int sourceWidth,
            int sourceHeight,
            int targetWidth,
            int targetHeight
    ) {
        int width = Math.max(1, sourceWidth);
        int height = Math.max(1, sourceHeight);
        int[] crop = getCenterCropBounds(resolution, width, height);
        int cropWidth = Math.max(1, crop[2] - crop[0]);
        int cropHeight = Math.max(1, crop[3] - crop[1]);
        double scale = Math.max(
                Math.max(1, targetWidth) / (double) cropWidth,
                Math.max(1, targetHeight) / (double) cropHeight
        );
        return Math.max(Math.max(1, targetWidth), (int) Math.round(width * scale));
    }

    public static int getCenterCropWorkingHeight(
            String resolution,
            int sourceWidth,
            int sourceHeight,
            int targetWidth,
            int targetHeight
    ) {
        int width = Math.max(1, sourceWidth);
        int height = Math.max(1, sourceHeight);
        int[] crop = getCenterCropBounds(resolution, width, height);
        int cropWidth = Math.max(1, crop[2] - crop[0]);
        int cropHeight = Math.max(1, crop[3] - crop[1]);
        double scale = Math.max(
                Math.max(1, targetWidth) / (double) cropWidth,
                Math.max(1, targetHeight) / (double) cropHeight
        );
        return Math.max(Math.max(1, targetHeight), (int) Math.round(height * scale));
    }

'''
filter_text = replace_once(filter_text, marker, helpers + marker, "aspect helper insertion")
filter_path.write_text(filter_text)


# Photo + CPU-video fallback: crop the long side first, then resize to the exact preset.
converter_path = root / "MediaFileConverter.java"
converter = converter_path.read_text()
converter = replace_once(
    converter,
    "import android.graphics.BitmapFactory;\n",
    "import android.graphics.BitmapFactory;\nimport android.graphics.Canvas;\nimport android.graphics.Paint;\nimport android.graphics.Rect;\n",
    "converter crop imports",
)
old_prepare = r'''    private static Bitmap prepareFilteredBitmap(
            Bitmap source,
            Options options,
            boolean ignored,
            int targetWidth,
            int targetHeight
    ) {
        Bitmap scaled = Bitmap.createScaledBitmap(
                source,
                Math.max(1, targetWidth),
                Math.max(1, targetHeight),
                false
        );
        if (scaled == source) {
            scaled = source.copy(Bitmap.Config.ARGB_8888, true);
        } else if (scaled.getConfig() != Bitmap.Config.ARGB_8888 || !scaled.isMutable()) {
            Bitmap mutable = scaled.copy(Bitmap.Config.ARGB_8888, true);
            scaled.recycle();
            scaled = mutable;
        }
        if (scaled == null) throw new IllegalStateException("変換用Bitmapを作成できません");
        GameBoyFilter.apply(scaled, options.mode, options.brightness, options.contrast, options.dither);
        return scaled;
    }
'''
new_prepare = r'''    private static Bitmap prepareFilteredBitmap(
            Bitmap source,
            Options options,
            boolean ignored,
            int targetWidth,
            int targetHeight
    ) {
        int width = Math.max(1, targetWidth);
        int height = Math.max(1, targetHeight);
        int[] crop = GameBoyFilter.getCenterCropBounds(
                options.resolution,
                source.getWidth(),
                source.getHeight()
        );

        Bitmap scaled = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
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
        GameBoyFilter.apply(scaled, options.mode, options.brightness, options.contrast, options.dither);
        return scaled;
    }
'''
converter = replace_once(converter, old_prepare, new_prepare, "center crop bitmap conversion")

working_marker = r'''            int targetWidth = makeEven(GameBoyFilter.getTargetWidth(options.resolution, firstFrame.getWidth()));
            int targetHeight = makeEven(GameBoyFilter.getTargetHeight(options.resolution, firstFrame.getHeight()));
            int fps = determineFrameRate(retriever, durationUs);
'''
working_replacement = r'''            int targetWidth = makeEven(GameBoyFilter.getTargetWidth(options.resolution, firstFrame.getWidth()));
            int targetHeight = makeEven(GameBoyFilter.getTargetHeight(options.resolution, firstFrame.getHeight()));
            int workingWidth = GameBoyFilter.getCenterCropWorkingWidth(
                    options.resolution,
                    firstFrame.getWidth(),
                    firstFrame.getHeight(),
                    targetWidth,
                    targetHeight
            );
            int workingHeight = GameBoyFilter.getCenterCropWorkingHeight(
                    options.resolution,
                    firstFrame.getWidth(),
                    firstFrame.getHeight(),
                    targetWidth,
                    targetHeight
            );
            int fps = determineFrameRate(retriever, durationUs);
'''
converter = replace_once(converter, working_marker, working_replacement, "cpu video working size")
converter = replace_once(
    converter,
    r'''                            targetWidth,
                            targetHeight
                    );
''',
    r'''                            workingWidth,
                            workingHeight
                    );
''',
    "cpu video target-first crop-aware decode",
)
converter_path.write_text(converter)


# MediaProjection CPU route: crop source before downsampling instead of stretching it.
capture_path = root / "FilterCaptureService.java"
capture = capture_path.read_text()
old_capture = r'''            Canvas canvas = new Canvas(lowResolutionBitmap);
            Paint downsamplePaint = new Paint();
            downsamplePaint.setFilterBitmap(false);
            downsamplePaint.setAntiAlias(false);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    captureBitmap,
                    new Rect(0, 0, sourceWidth, sourceHeight),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
'''
new_capture = r'''            Canvas canvas = new Canvas(lowResolutionBitmap);
            Paint downsamplePaint = new Paint();
            downsamplePaint.setFilterBitmap(false);
            downsamplePaint.setAntiAlias(false);
            int[] crop = GameBoyFilter.getCenterCropBounds(resolution, sourceWidth, sourceHeight);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    captureBitmap,
                    new Rect(crop[0], crop[1], crop[2], crop[3]),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
'''
capture = replace_once(capture, old_capture, new_capture, "projection center crop")
capture_path.write_text(capture)


# Accessibility CPU fallback: show the fixed-aspect frame without stretching it to the phone display.
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()
old_cpu_draw = r'''            canvas.drawBitmap(
                    current,
                    null,
                    new Rect(0, 0, getWidth(), getHeight()),
                    paint
            );
'''
new_cpu_draw = r'''            int viewWidth = Math.max(1, getWidth());
            int viewHeight = Math.max(1, getHeight());
            float frameAspect = current.getWidth() / (float) Math.max(1, current.getHeight());
            int drawWidth = viewWidth;
            int drawHeight = Math.max(1, Math.round(drawWidth / frameAspect));
            if (drawHeight > viewHeight) {
                drawHeight = viewHeight;
                drawWidth = Math.max(1, Math.round(drawHeight * frameAspect));
            }
            int left = (viewWidth - drawWidth) / 2;
            int top = (viewHeight - drawHeight) / 2;
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    current,
                    null,
                    new Rect(left, top, left + drawWidth, top + drawHeight),
                    paint
            );
'''
access = replace_once(access, old_cpu_draw, new_cpu_draw, "accessibility CPU aspect fit")
access_path.write_text(access)


# Accessibility GPU renderer: center crop source to the preset and render into a centered target-aspect viewport.
gpu_renderer_path = root / "GpuFilterRenderer.java"
gpu = gpu_renderer_path.read_text()
gpu = replace_once(
    gpu,
    "import android.graphics.Canvas;\n",
    "import android.graphics.Canvas;\nimport android.graphics.Color;\n",
    "GPU renderer Color import",
)
gpu = replace_once(
    gpu,
    '            "uniform float2 sourceSize;\\n" +\n',
    '            "uniform float2 sourceSize;\\n" +\n'
    '            "uniform float2 cropOffset;\\n" +\n'
    '            "uniform float2 cropSize;\\n" +\n',
    "GPU renderer crop uniforms",
)
gpu = replace_once(
    gpu,
    '            "    float2 samplePos = ((cell + 0.5) / grid) * sourceSize;\\n" +\n',
    '            "    float2 sampleUv = cropOffset + (((cell + 0.5) / grid) * cropSize);\\n" +\n'
    '            "    float2 samplePos = sampleUv * sourceSize;\\n" +\n',
    "GPU renderer cropped sampling",
)
old_gpu_uniforms = r'''        runtimeShader.setInputShader("image", image);
        runtimeShader.setFloatUniform("viewSize", Math.max(1, viewWidth), Math.max(1, viewHeight));
        runtimeShader.setFloatUniform("sourceSize", source.getWidth(), source.getHeight());
        runtimeShader.setFloatUniform("pixelGrid", Math.max(1, targetWidth), Math.max(1, targetHeight));
        runtimeShader.setFloatUniform("brightness", brightness / 255.0f);
        runtimeShader.setFloatUniform("contrast", contrast / 100.0f);
        runtimeShader.setFloatUniform("mode", modeValue(mode));
        runtimeShader.setFloatUniform("ditherEnabled", dither ? 1.0f : 0.0f);

        canvas.drawRect(0, 0, Math.max(1, viewWidth), Math.max(1, viewHeight), paint);
'''
new_gpu_uniforms = r'''        int safeViewWidth = Math.max(1, viewWidth);
        int safeViewHeight = Math.max(1, viewHeight);
        int safeTargetWidth = Math.max(1, targetWidth);
        int safeTargetHeight = Math.max(1, targetHeight);
        float targetAspect = safeTargetWidth / (float) safeTargetHeight;

        int drawWidth = safeViewWidth;
        int drawHeight = Math.max(1, Math.round(drawWidth / targetAspect));
        if (drawHeight > safeViewHeight) {
            drawHeight = safeViewHeight;
            drawWidth = Math.max(1, Math.round(drawHeight * targetAspect));
        }
        int left = (safeViewWidth - drawWidth) / 2;
        int top = (safeViewHeight - drawHeight) / 2;

        float sourceAspect = source.getWidth() / (float) Math.max(1, source.getHeight());
        float cropX = 0.0f;
        float cropY = 0.0f;
        float cropWidth = 1.0f;
        float cropHeight = 1.0f;
        if (sourceAspect > targetAspect) {
            cropWidth = targetAspect / sourceAspect;
            cropX = (1.0f - cropWidth) * 0.5f;
        } else if (sourceAspect < targetAspect) {
            cropHeight = sourceAspect / targetAspect;
            cropY = (1.0f - cropHeight) * 0.5f;
        }

        runtimeShader.setInputShader("image", image);
        runtimeShader.setFloatUniform("viewSize", drawWidth, drawHeight);
        runtimeShader.setFloatUniform("sourceSize", source.getWidth(), source.getHeight());
        runtimeShader.setFloatUniform("cropOffset", cropX, cropY);
        runtimeShader.setFloatUniform("cropSize", cropWidth, cropHeight);
        runtimeShader.setFloatUniform("pixelGrid", safeTargetWidth, safeTargetHeight);
        runtimeShader.setFloatUniform("brightness", brightness / 255.0f);
        runtimeShader.setFloatUniform("contrast", contrast / 100.0f);
        runtimeShader.setFloatUniform("mode", modeValue(mode));
        runtimeShader.setFloatUniform("ditherEnabled", dither ? 1.0f : 0.0f);

        canvas.drawColor(Color.BLACK);
        canvas.save();
        canvas.translate(left, top);
        canvas.clipRect(0, 0, drawWidth, drawHeight);
        canvas.drawRect(0, 0, drawWidth, drawHeight, paint);
        canvas.restore();
'''
gpu = replace_once(gpu, old_gpu_uniforms, new_gpu_uniforms, "GPU renderer viewport aspect fit")
gpu_renderer_path.write_text(gpu)


# File-video GPU route: crop display-oriented texture coordinates before SurfaceTexture transform.
video_gpu_path = root / "VideoGpuConverter.java"
video_gpu = video_gpu_path.read_text()
video_gpu = replace_once(
    video_gpu,
    "                renderer = new FrameRenderer(targetWidth, targetHeight, rotation, options);\n",
    "                renderer = new FrameRenderer(\n"
    "                        sourceWidth,\n"
    "                        sourceHeight,\n"
    "                        targetWidth,\n"
    "                        targetHeight,\n"
    "                        rotation,\n"
    "                        options\n"
    "                );\n",
    "video GPU renderer source size",
)
old_constructor = r'''        FrameRenderer(
                int targetWidth,
                int targetHeight,
                int rotation,
                MediaFileConverter.Options options
        ) {
            this.targetWidth = targetWidth;
            this.targetHeight = targetHeight;
            this.options = options;
            this.gbcMode = GameBoyFilter.MODE_GBC.equals(options.mode);

            vertexBuffer = allocateFloatBuffer(VERTICES);
            textureBuffer = allocateFloatBuffer(textureCoordinates(rotation));
            identityTextureBuffer = allocateFloatBuffer(textureCoordinates(0));
'''
new_constructor = r'''        FrameRenderer(
                int sourceWidth,
                int sourceHeight,
                int targetWidth,
                int targetHeight,
                int rotation,
                MediaFileConverter.Options options
        ) {
            this.targetWidth = targetWidth;
            this.targetHeight = targetHeight;
            this.options = options;
            this.gbcMode = GameBoyFilter.MODE_GBC.equals(options.mode);

            int displaySourceWidth = (rotation == 90 || rotation == 270)
                    ? sourceHeight
                    : sourceWidth;
            int displaySourceHeight = (rotation == 90 || rotation == 270)
                    ? sourceWidth
                    : sourceHeight;
            int[] crop = GameBoyFilter.getCenterCropBounds(
                    options.resolution,
                    displaySourceWidth,
                    displaySourceHeight
            );
            float cropLeft = crop[0] / (float) Math.max(1, displaySourceWidth);
            float cropTop = crop[1] / (float) Math.max(1, displaySourceHeight);
            float cropRight = crop[2] / (float) Math.max(1, displaySourceWidth);
            float cropBottom = crop[3] / (float) Math.max(1, displaySourceHeight);

            vertexBuffer = allocateFloatBuffer(VERTICES);
            textureBuffer = allocateFloatBuffer(textureCoordinates(
                    rotation,
                    cropLeft,
                    cropTop,
                    cropRight,
                    cropBottom
            ));
            identityTextureBuffer = allocateFloatBuffer(textureCoordinates(0, 0f, 0f, 1f, 1f));
'''
video_gpu = replace_once(video_gpu, old_constructor, new_constructor, "video GPU center crop constructor")
old_coords = r'''        private static float[] textureCoordinates(int rotation) {
            if (rotation == 90) {
                return new float[]{0f,1f, 0f,0f, 1f,1f, 1f,0f};
            }
            if (rotation == 180) {
                return new float[]{1f,1f, 0f,1f, 1f,0f, 0f,0f};
            }
            if (rotation == 270) {
                return new float[]{1f,0f, 1f,1f, 0f,0f, 0f,1f};
            }
            return new float[]{0f,0f, 1f,0f, 0f,1f, 1f,1f};
        }
'''
new_coords = r'''        private static float[] textureCoordinates(
                int rotation,
                float left,
                float top,
                float right,
                float bottom
        ) {
            float[] display = {
                    left, top,
                    right, top,
                    left, bottom,
                    right, bottom
            };
            float[] mapped = new float[display.length];
            for (int i = 0; i < display.length; i += 2) {
                float u = display[i];
                float v = display[i + 1];
                if (rotation == 90) {
                    mapped[i] = v;
                    mapped[i + 1] = 1.0f - u;
                } else if (rotation == 180) {
                    mapped[i] = 1.0f - u;
                    mapped[i + 1] = 1.0f - v;
                } else if (rotation == 270) {
                    mapped[i] = 1.0f - v;
                    mapped[i + 1] = u;
                } else {
                    mapped[i] = u;
                    mapped[i + 1] = v;
                }
            }
            return mapped;
        }
'''
video_gpu = replace_once(video_gpu, old_coords, new_coords, "video GPU cropped texture coordinates")
video_gpu = replace_once(
    video_gpu,
    '                            + " source_pts=true"\n',
    '                            + " source_pts=true"\n'
    '                            + " center_crop=true"\n',
    "video GPU crop performance evidence",
)
video_gpu_path.write_text(video_gpu)


# CPU comparison diagnostics should benchmark the same crop-aware resize that fallback conversion uses.
diag_path = root / "VideoPipelineDiagnostics.java"
diag = diag_path.read_text()
diag = replace_once(
    diag,
    "import android.graphics.Bitmap;\nimport android.graphics.Color;\n",
    "import android.graphics.Bitmap;\nimport android.graphics.Canvas;\nimport android.graphics.Color;\nimport android.graphics.Paint;\nimport android.graphics.Rect;\n",
    "diagnostics crop imports",
)
diag = replace_once(
    diag,
    "                    target = toTargetBitmap(decoded, result.targetWidth, result.targetHeight);\n",
    "                    target = toTargetBitmap(\n"
    "                            decoded,\n"
    "                            options.resolution,\n"
    "                            result.targetWidth,\n"
    "                            result.targetHeight\n"
    "                    );\n",
    "diagnostics crop-aware target bitmap call",
)
old_diag_target = r'''    private static Bitmap toTargetBitmap(Bitmap source, int targetWidth, int targetHeight) {
        Bitmap scaled = Bitmap.createScaledBitmap(
                source,
                Math.max(1, targetWidth),
                Math.max(1, targetHeight),
                false
        );
        if (scaled == source) {
            return source.copy(Bitmap.Config.ARGB_8888, true);
        }
        if (scaled.getConfig() != Bitmap.Config.ARGB_8888 || !scaled.isMutable()) {
            Bitmap mutable = scaled.copy(Bitmap.Config.ARGB_8888, true);
            scaled.recycle();
            return mutable;
        }
        return scaled;
    }
'''
new_diag_target = r'''    private static Bitmap toTargetBitmap(
            Bitmap source,
            String resolution,
            int targetWidth,
            int targetHeight
    ) {
        int width = Math.max(1, targetWidth);
        int height = Math.max(1, targetHeight);
        int[] crop = GameBoyFilter.getCenterCropBounds(
                resolution,
                source.getWidth(),
                source.getHeight()
        );
        Bitmap scaled = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
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
        return scaled;
    }
'''
diag = replace_once(diag, old_diag_target, new_diag_target, "diagnostics crop-aware resize")

# Target-first diagnostics still decode a source-aspect working image, then crop to the preset.
diag = replace_once(
    diag,
    r'''                                result.targetWidth,
                                result.targetHeight
                        );
''',
    r'''                                GameBoyFilter.getCenterCropWorkingWidth(
                                        options.resolution,
                                        result.sourceWidth,
                                        result.sourceHeight,
                                        result.targetWidth,
                                        result.targetHeight
                                ),
                                GameBoyFilter.getCenterCropWorkingHeight(
                                        options.resolution,
                                        result.sourceWidth,
                                        result.sourceHeight,
                                        result.targetWidth,
                                        result.targetHeight
                                )
                        );
''',
    "diagnostics target-first working decode",
)
diag_path.write_text(diag)

print("v0.1.33 fixed-preset center crop and aspect preservation applied")
