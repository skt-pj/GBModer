#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_console_frame_v044.py <generated_src_root>")

root = Path(sys.argv[1]).resolve() / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# Photo conversion and CPU video fallback share the Canvas frame renderer.
converter_path = root / "MediaFileConverter.java"
converter = converter_path.read_text()
converter = replace_once(
    converter,
    "            converted = prepareFilteredBitmap(sourceBitmap, options, true);\n",
    "            converted = prepareFilteredBitmap(sourceBitmap, options, true);\n"
    "            if (ConsoleFrameRenderer.isFixedResolution(options.resolution)) {\n"
    "                Bitmap framed = ConsoleFrameRenderer.compose(converted, options.resolution);\n"
    "                if (framed != converted) {\n"
    "                    converted.recycle();\n"
    "                    converted = framed;\n"
    "                }\n"
    "            }\n",
    "photo console frame",
)

cpu_target_marker = '''            int targetHeight = makeEven(GameBoyFilter.getVideoTargetHeight(
                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()
            ));
'''
converter = replace_once(
    converter,
    cpu_target_marker,
    cpu_target_marker
    + '''            ConsoleFrameRenderer.FrameSpec cpuFrameSpec = ConsoleFrameRenderer.getSpec(
                    options.resolution, targetWidth, targetHeight
            );
            boolean cpuConsoleFrame = ConsoleFrameRenderer.isFixedResolution(options.resolution);
            int encodedWidth = cpuConsoleFrame ? cpuFrameSpec.outputWidth : targetWidth;
            int encodedHeight = cpuConsoleFrame ? cpuFrameSpec.outputHeight : targetHeight;
''',
    "CPU video framed output dimensions",
)
converter = replace_once(
    converter,
    "            MediaFormat videoFormat = MediaFormat.createVideoFormat(VIDEO_MIME, targetWidth, targetHeight);\n",
    "            MediaFormat videoFormat = MediaFormat.createVideoFormat(VIDEO_MIME, encodedWidth, encodedHeight);\n",
    "CPU video encoder dimensions",
)
converter = replace_once(
    converter,
    "                    Math.max(300_000, Math.min(12_000_000, targetWidth * targetHeight * fps * 2))\n",
    "                    Math.max(300_000, Math.min(12_000_000, encodedWidth * encodedHeight * fps * 2))\n",
    "CPU video bitrate dimensions",
)
converter = replace_once(
    converter,
    "                    filtered = prepareFilteredBitmap(sourceFrame, options, false, targetWidth, targetHeight);\n"
    "                    byte[] yuv = bitmapToYuv420(filtered, colorFormat);\n",
    "                    filtered = prepareFilteredBitmap(sourceFrame, options, false, targetWidth, targetHeight);\n"
    "                    if (cpuConsoleFrame) {\n"
    "                        Bitmap framed = ConsoleFrameRenderer.compose(filtered, options.resolution);\n"
    "                        if (framed != filtered) {\n"
    "                            filtered.recycle();\n"
    "                            filtered = framed;\n"
    "                        }\n"
    "                    }\n"
    "                    byte[] yuv = bitmapToYuv420(filtered, colorFormat);\n",
    "CPU video frame composition",
)
converter_path.write_text(converter)


# Accessibility screenshot route: fixed presets use the small CPU target so the stylized frame
# can be composed once per frame. Phone/native keep the existing GPU path.
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()
access = replace_once(
    access,
    "        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU\n"
    "                && !gpuWindowPathDisabled\n"
    "                && !GameBoyFilter.MODE_GBC.equals(windowFilterMode);\n",
    "        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU\n"
    "                && !gpuWindowPathDisabled\n"
    "                && !ConsoleFrameRenderer.isFixedResolution(windowFilterResolution)\n"
    "                && !GameBoyFilter.MODE_GBC.equals(windowFilterMode);\n",
    "fixed resolution live route uses framed CPU output",
)
access = replace_once(
    access,
    "            Bitmap frame = lowResolutionBitmap;\n"
    "            lowResolutionBitmap = null;\n",
    "            Bitmap frame = lowResolutionBitmap;\n"
    "            if (ConsoleFrameRenderer.isFixedResolution(windowFilterResolution)) {\n"
    "                Bitmap framed = ConsoleFrameRenderer.compose(frame, windowFilterResolution);\n"
    "                if (framed != frame) {\n"
    "                    frame.recycle();\n"
    "                    frame = framed;\n"
    "                }\n"
    "            }\n"
    "            lowResolutionBitmap = null;\n",
    "accessibility console frame composition",
)
access_path.write_text(access)


# MediaProjection route uses the same frame renderer before handing the frame to the overlay.
capture_path = root / "FilterCaptureService.java"
capture = capture_path.read_text()
capture = replace_once(
    capture,
    "            long frameCopyStartedNs = SystemClock.elapsedRealtimeNanos();\n"
    "            Bitmap frameForOverlay = lowResolutionBitmap.copy(Bitmap.Config.ARGB_8888, false);\n"
    "            long frameCopyFinishedNs = SystemClock.elapsedRealtimeNanos();\n",
    "            long frameCopyStartedNs = SystemClock.elapsedRealtimeNanos();\n"
    "            Bitmap frameForOverlay = ConsoleFrameRenderer.isFixedResolution(resolution)\n"
    "                    ? ConsoleFrameRenderer.compose(lowResolutionBitmap, resolution)\n"
    "                    : lowResolutionBitmap.copy(Bitmap.Config.ARGB_8888, false);\n"
    "            long frameCopyFinishedNs = SystemClock.elapsedRealtimeNanos();\n",
    "projection console frame composition",
)
capture_path.write_text(capture)


# GPU video route keeps the Surface pipeline. The filtered screen is rendered into a console-style
# output canvas with GLES scissor rectangles, preserving source PTS and avoiding CPU RGBA/YUV work.
video_path = root / "VideoGpuConverter.java"
video = video_path.read_text()
video_target_marker = '''            int targetHeight = makeEven(GameBoyFilter.getVideoTargetHeight(
                    options.resolution, displayWidth, displayHeight
            ));
'''
video = replace_once(
    video,
    video_target_marker,
    video_target_marker
    + '''            boolean consoleFrame = ConsoleFrameRenderer.isFixedResolution(options.resolution);
            ConsoleFrameRenderer.FrameSpec frameSpec = ConsoleFrameRenderer.getSpec(
                    options.resolution, targetWidth, targetHeight
            );
            int outputWidth = consoleFrame ? frameSpec.outputWidth : targetWidth;
            int outputHeight = consoleFrame ? frameSpec.outputHeight : targetHeight;
''',
    "GPU framed output dimensions",
)
video = replace_once(
    video,
    "            encoder = createSurfaceEncoder(targetWidth, targetHeight, nominalFps);\n",
    "            encoder = createSurfaceEncoder(outputWidth, outputHeight, nominalFps);\n",
    "GPU encoder framed dimensions",
)
video = replace_once(
    video,
    '''                    targetWidth,
                    targetHeight,
                    rotation,
                    options
''',
    '''                    targetWidth,
                    targetHeight,
                    outputWidth,
                    outputHeight,
                    rotation,
                    options
''',
    "GpuPipe framed dimensions",
)
video = replace_once(
    video,
    '                            + " target=" + targetWidth + "x" + targetHeight\n',
    '                            + " target=" + outputWidth + "x" + outputHeight\n'
    '                            + " screen=" + targetWidth + "x" + targetHeight\n'
    '                            + " console_frame=" + consoleFrame\n',
    "GPU framed diagnostics",
)

video = replace_once(
    video,
    '''                int targetWidth,
                int targetHeight,
                int rotation,
                MediaFileConverter.Options options
''',
    '''                int targetWidth,
                int targetHeight,
                int outputWidth,
                int outputHeight,
                int rotation,
                MediaFileConverter.Options options
''',
    "GpuPipe constructor signature",
)
video = replace_once(
    video,
    "                renderer = new FrameRenderer(targetWidth, targetHeight, rotation, options);\n",
    "                renderer = new FrameRenderer(\n"
    "                        targetWidth, targetHeight, outputWidth, outputHeight, rotation, options\n"
    "                );\n",
    "FrameRenderer framed constructor call",
)

video = replace_once(
    video,
    '''        private final int targetWidth;
        private final int targetHeight;
        private final MediaFileConverter.Options options;
''',
    '''        private final int targetWidth;
        private final int targetHeight;
        private final int outputWidth;
        private final int outputHeight;
        private final boolean consoleFrame;
        private final ConsoleFrameRenderer.FrameSpec frameSpec;
        private final MediaFileConverter.Options options;
''',
    "FrameRenderer frame fields",
)
video = replace_once(
    video,
    '''                int targetWidth,
                int targetHeight,
                int rotation,
                MediaFileConverter.Options options
        ) {
            this.targetWidth = targetWidth;
            this.targetHeight = targetHeight;
            this.options = options;
''',
    '''                int targetWidth,
                int targetHeight,
                int outputWidth,
                int outputHeight,
                int rotation,
                MediaFileConverter.Options options
        ) {
            this.targetWidth = targetWidth;
            this.targetHeight = targetHeight;
            this.outputWidth = outputWidth;
            this.outputHeight = outputHeight;
            this.consoleFrame = ConsoleFrameRenderer.isFixedResolution(options.resolution);
            this.frameSpec = ConsoleFrameRenderer.getSpec(options.resolution, targetWidth, targetHeight);
            this.options = options;
''',
    "FrameRenderer frame constructor",
)
video = replace_once(
    video,
    '''        void draw(float[] textureMatrix) throws IOException {
            if (gbcMode) {
''',
    '''        void draw(float[] textureMatrix) throws IOException {
            if (consoleFrame) {
                drawConsoleBody();
            }
            if (gbcMode) {
''',
    "GPU draw console body",
)
video = replace_once(
    video,
    "            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, framebuffer);\n"
    "            GLES20.glViewport(0, 0, targetWidth, targetHeight);\n",
    "            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, framebuffer);\n"
    "            if (framebuffer != 0 || !consoleFrame) {\n"
    "                GLES20.glViewport(0, 0, targetWidth, targetHeight);\n"
    "            } else {\n"
    "                GLES20.glViewport(\n"
    "                        frameSpec.screenLeft,\n"
    "                        outputHeight - frameSpec.screenTop - targetHeight,\n"
    "                        targetWidth,\n"
    "                        targetHeight\n"
    "                );\n"
    "            }\n",
    "external screen viewport",
)
video = replace_once(
    video,
    "            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0);\n"
    "            GLES20.glViewport(0, 0, targetWidth, targetHeight);\n"
    "            GLES20.glUseProgram(lookupProgram);\n",
    "            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0);\n"
    "            if (consoleFrame) {\n"
    "                GLES20.glViewport(\n"
    "                        frameSpec.screenLeft,\n"
    "                        outputHeight - frameSpec.screenTop - targetHeight,\n"
    "                        targetWidth,\n"
    "                        targetHeight\n"
    "                );\n"
    "            } else {\n"
    "                GLES20.glViewport(0, 0, targetWidth, targetHeight);\n"
    "            }\n"
    "            GLES20.glUseProgram(lookupProgram);\n",
    "GBC lookup screen viewport",
)

console_methods = r'''        private void drawConsoleBody() {
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0);
            fillRect(0, 0, outputWidth, outputHeight, 18, 18, 20);

            int bodyR = 195;
            int bodyG = 191;
            int bodyB = 173;
            int accentR = 126;
            int accentG = 46;
            int accentB = 91;
            if (frameSpec.style == ConsoleFrameRenderer.STYLE_GBC) {
                bodyR = 185; bodyG = 178; bodyB = 218;
                accentR = 142; accentG = 48; accentB = 105;
            } else if (frameSpec.style == ConsoleFrameRenderer.STYLE_GBA) {
                bodyR = 92; bodyG = 103; bodyB = 145;
                accentR = 64; accentG = 68; accentB = 86;
            } else if (frameSpec.style == ConsoleFrameRenderer.STYLE_DS) {
                bodyR = 112; bodyG = 115; bodyB = 122;
                accentR = 62; accentG = 64; accentB = 70;
            }

            fillRect(4, 4, outputWidth - 8, outputHeight - 8, bodyR, bodyG, bodyB);
            fillRect(
                    frameSpec.screenLeft - 10,
                    frameSpec.screenTop - 10,
                    frameSpec.screenWidth + 20,
                    frameSpec.screenHeight + 20,
                    45, 47, 52
            );

            if (frameSpec.style == ConsoleFrameRenderer.STYLE_GBA) {
                int centerY = frameSpec.screenTop + frameSpec.screenHeight / 2;
                int dpadY = centerY - 20;
                fillRect(18, dpadY + 12, 44, 16, 42, 43, 47);
                fillRect(32, dpadY, 16, 40, 42, 43, 47);
                fillRect(outputWidth - 66, centerY + 1, 18, 18, accentR, accentG, accentB);
                fillRect(outputWidth - 42, centerY - 16, 18, 18, accentR, accentG, accentB);
            } else if (frameSpec.style == ConsoleFrameRenderer.STYLE_DS) {
                int hingeY = frameSpec.screenTop + frameSpec.screenHeight + 22;
                fillRect(20, hingeY, outputWidth - 40, 10, 70, 72, 78);
                int lowerTop = hingeY + 44;
                int lowerWidth = Math.max(80, Math.min(frameSpec.screenWidth - 32, 176));
                int dummyLeft = (outputWidth - lowerWidth) / 2;
                int dummyHeight = Math.max(54, Math.min(frameSpec.screenHeight / 2, 120));
                fillRect(dummyLeft, lowerTop, lowerWidth, dummyHeight, 38, 40, 44);
                int controlY = Math.min(outputHeight - 52, lowerTop + dummyHeight + 14);
                fillRect(24, controlY + 10, 38, 14, 42, 43, 47);
                fillRect(36, controlY, 14, 34, 42, 43, 47);
                fillRect(outputWidth - 58, controlY + 10, 16, 16, accentR, accentG, accentB);
                fillRect(outputWidth - 36, controlY, 16, 16, accentR, accentG, accentB);
            } else {
                int controlsTop = frameSpec.screenTop + frameSpec.screenHeight + 30;
                int dpadX = Math.max(18, outputWidth / 4 - 16);
                int dpadY = controlsTop + 14;
                fillRect(dpadX, dpadY + 12, 48, 16, 42, 43, 47);
                fillRect(dpadX + 16, dpadY, 16, 40, 42, 43, 47);
                int buttonX = Math.round(outputWidth * 0.70f);
                fillRect(buttonX - 10, dpadY + 12, 20, 20, accentR, accentG, accentB);
                fillRect(buttonX + 20, dpadY + 2, 20, 20, accentR, accentG, accentB);
                int barY = Math.min(outputHeight - 26, dpadY + 54);
                fillRect(outputWidth / 2 - 28, barY, 24, 6, 82, 82, 86);
                fillRect(outputWidth / 2 + 4, barY, 24, 6, 82, 82, 86);
                int speakerX = outputWidth - 52;
                int speakerY = Math.min(outputHeight - 36, barY + 18);
                for (int i = 0; i < 4; i++) {
                    fillRect(speakerX + i * 7, speakerY, 3, 16, 116, 112, 106);
                }
            }
        }

        private void fillRect(
                int left,
                int top,
                int width,
                int height,
                int red,
                int green,
                int blue
        ) {
            int safeLeft = Math.max(0, left);
            int safeTop = Math.max(0, top);
            int safeRight = Math.min(outputWidth, left + Math.max(0, width));
            int safeBottom = Math.min(outputHeight, top + Math.max(0, height));
            int safeWidth = safeRight - safeLeft;
            int safeHeight = safeBottom - safeTop;
            if (safeWidth <= 0 || safeHeight <= 0) {
                return;
            }
            GLES20.glEnable(GLES20.GL_SCISSOR_TEST);
            GLES20.glScissor(
                    safeLeft,
                    outputHeight - safeBottom,
                    safeWidth,
                    safeHeight
            );
            GLES20.glClearColor(red / 255.0f, green / 255.0f, blue / 255.0f, 1.0f);
            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT);
            GLES20.glDisable(GLES20.GL_SCISSOR_TEST);
        }

'''
video = replace_once(
    video,
    "        private void setupGbcTargets() {\n",
    console_methods + "        private void setupGbcTargets() {\n",
    "GPU console drawing helpers",
)
video_path.write_text(video)

print("v0.1.44 fixed resolutions render inside handheld-style frames", flush=True)
