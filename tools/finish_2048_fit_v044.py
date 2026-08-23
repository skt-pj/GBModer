#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_2048_fit_v044.py <generated_java_root>")

root = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# Geometry shared by the embedded 2048TD CPU/GPU paths. The source is kept whole
# and centered inside the selected output resolution instead of center-cropping.
filter_path = root / "GameBoyFilter.java"
filter_text = filter_path.read_text()
marker = "    private static float getPhoneScale(String resolution) {\n"
contain_helper = r'''    public static int[] getContainFitBounds(
            int sourceWidth,
            int sourceHeight,
            int targetWidth,
            int targetHeight
    ) {
        int safeSourceWidth = Math.max(1, sourceWidth);
        int safeSourceHeight = Math.max(1, sourceHeight);
        int safeTargetWidth = Math.max(1, targetWidth);
        int safeTargetHeight = Math.max(1, targetHeight);

        int drawWidth = safeTargetWidth;
        int drawHeight = Math.max(
                1,
                (int) Math.round(drawWidth * (safeSourceHeight / (double) safeSourceWidth))
        );
        if (drawHeight > safeTargetHeight) {
            drawHeight = safeTargetHeight;
            drawWidth = Math.max(
                    1,
                    (int) Math.round(drawHeight * (safeSourceWidth / (double) safeSourceHeight))
            );
        }

        int left = (safeTargetWidth - drawWidth) / 2;
        int top = (safeTargetHeight - drawHeight) / 2;
        return new int[]{left, top, left + drawWidth, top + drawHeight};
    }

'''
filter_text = replace_once(
    filter_text,
    marker,
    contain_helper + marker,
    "contain-fit helper insertion",
)
filter_path.write_text(filter_text)


access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()

access = replace_once(
    access,
    "    private boolean allowOwnPackageWindow = false;\n",
    "    private boolean allowOwnPackageWindow = false;\n"
    "    private boolean embeddedContentFit = false;\n",
    "embedded fit state",
)

access = replace_once(
    access,
    "        allowOwnPackageWindow = false;\n        windowFilterMode = safeMode(mode);\n",
    "        allowOwnPackageWindow = false;\n"
    "        embeddedContentFit = false;\n"
    "        windowFilterMode = safeMode(mode);\n",
    "normal filter fit reset",
)

old_embedded_start = r'''    public void startEmbeddedContentFilter(
            String mode,
            String resolution,
            int brightness,
            int contrast,
            boolean dither
    ) {
        startWindowFilter(mode, resolution, brightness, contrast, dither, false);
        allowOwnPackageWindow = true;
        Log.i(TAG, "Embedded content filter enabled for own package");
    }
'''
new_embedded_start = r'''    public void startEmbeddedContentFilter(
            String mode,
            String resolution,
            int brightness,
            int contrast,
            boolean dither
    ) {
        startWindowFilter(mode, resolution, brightness, contrast, dither);
        allowOwnPackageWindow = true;
        embeddedContentFit = true;
        Log.i(TAG, "Embedded content filter enabled for own package layout=contain");
    }
'''
access = replace_once(
    access,
    old_embedded_start,
    new_embedded_start,
    "embedded start contain mode",
)

access = replace_once(
    access,
    "        allowOwnPackageWindow = false;\n        screenshotInFlight = false;\n",
    "        allowOwnPackageWindow = false;\n"
    "        embeddedContentFit = false;\n"
    "        screenshotInFlight = false;\n",
    "embedded fit stop reset",
)

old_cpu_downsample = r'''            Canvas canvas = new Canvas(lowResolutionBitmap);
            Paint downsamplePaint = new Paint();
            downsamplePaint.setFilterBitmap(false);
            downsamplePaint.setAntiAlias(false);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    source,
                    new Rect(0, 0, source.getWidth(), source.getHeight()),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
'''
new_cpu_downsample = r'''            Canvas canvas = new Canvas(lowResolutionBitmap);
            Paint downsamplePaint = new Paint();
            downsamplePaint.setFilterBitmap(false);
            downsamplePaint.setAntiAlias(false);
            Rect destination = new Rect(0, 0, targetWidth, targetHeight);
            if (embeddedContentFit) {
                int[] fit = GameBoyFilter.getContainFitBounds(
                        source.getWidth(),
                        source.getHeight(),
                        targetWidth,
                        targetHeight
                );
                destination.set(fit[0], fit[1], fit[2], fit[3]);
            }
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    source,
                    new Rect(0, 0, source.getWidth(), source.getHeight()),
                    destination,
                    downsamplePaint
            );
'''
access = replace_once(
    access,
    old_cpu_downsample,
    new_cpu_downsample,
    "embedded CPU contain fit",
)

old_gpu_call = r'''                    gpuRenderer.draw(
                            canvas,
                            current,
                            getWidth(),
                            getHeight(),
                            gpuTargetWidth,
                            gpuTargetHeight,
                            gpuMode,
                            gpuBrightness,
                            gpuContrast,
                            gpuDither
                    );
'''
new_gpu_call = r'''                    gpuRenderer.draw(
                            canvas,
                            current,
                            getWidth(),
                            getHeight(),
                            gpuTargetWidth,
                            gpuTargetHeight,
                            gpuMode,
                            gpuBrightness,
                            gpuContrast,
                            gpuDither,
                            service.embeddedContentFit
                    );
'''
access = replace_once(
    access,
    old_gpu_call,
    new_gpu_call,
    "embedded GPU contain flag",
)
access_path.write_text(access)


gpu_path = root / "GpuFilterRenderer.java"
gpu = gpu_path.read_text()

old_signature = r'''    void draw(
            Canvas canvas,
            Bitmap source,
            int viewWidth,
            int viewHeight,
            int targetWidth,
            int targetHeight,
            String mode,
            int brightness,
            int contrast,
            boolean dither
    ) {
'''
new_signature = r'''    void draw(
            Canvas canvas,
            Bitmap source,
            int viewWidth,
            int viewHeight,
            int targetWidth,
            int targetHeight,
            String mode,
            int brightness,
            int contrast,
            boolean dither,
            boolean fitSource
    ) {
'''
gpu = replace_once(gpu, old_signature, new_signature, "GPU contain-fit parameter")

old_geometry = r'''        int safeViewWidth = Math.max(1, viewWidth);
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
new_geometry = r'''        int safeViewWidth = Math.max(1, viewWidth);
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
        int renderLeft = left;
        int renderTop = top;
        int renderWidth = drawWidth;
        int renderHeight = drawHeight;

        if (fitSource) {
            int[] fit = GameBoyFilter.getContainFitBounds(
                    source.getWidth(),
                    source.getHeight(),
                    drawWidth,
                    drawHeight
            );
            renderLeft = left + fit[0];
            renderTop = top + fit[1];
            renderWidth = Math.max(1, fit[2] - fit[0]);
            renderHeight = Math.max(1, fit[3] - fit[1]);
        } else if (sourceAspect > targetAspect) {
            cropWidth = targetAspect / sourceAspect;
            cropX = (1.0f - cropWidth) * 0.5f;
        } else if (sourceAspect < targetAspect) {
            cropHeight = sourceAspect / targetAspect;
            cropY = (1.0f - cropHeight) * 0.5f;
        }

        runtimeShader.setInputShader("image", image);
        runtimeShader.setFloatUniform("viewSize", renderWidth, renderHeight);
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
        canvas.translate(renderLeft, renderTop);
        canvas.clipRect(0, 0, renderWidth, renderHeight);
        canvas.drawRect(0, 0, renderWidth, renderHeight, paint);
        canvas.restore();
'''
gpu = replace_once(gpu, old_geometry, new_geometry, "GPU contain-fit geometry")
gpu_path.write_text(gpu)

print("v0.1.44 embedded 2048TD contain-fit rendering prepared", flush=True)
