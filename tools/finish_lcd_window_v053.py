#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_lcd_window_v053.py <generated_src_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# Live/game GPU + CPU paths use the source window aspect and fit it inside the real LCD.
# Resolution remains the pixel-grid density; it no longer changes the window geometry.
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()

old_cpu_target = r'''            int targetWidth = GameBoyFilter.getTargetWidth(
                    windowFilterResolution,
                    source.getWidth()
            );
            int targetHeight = GameBoyFilter.getTargetHeight(
                    windowFilterResolution,
                    source.getHeight()
            );
'''
new_cpu_target = r'''            int requestedTargetWidth = GameBoyFilter.getTargetWidth(
                    windowFilterResolution,
                    source.getWidth()
            );
            int requestedTargetHeight = GameBoyFilter.getTargetHeight(
                    windowFilterResolution,
                    source.getHeight()
            );
            int[] preservedGrid = ConsoleFrameRenderer.fitPixelGrid(
                    source.getWidth(),
                    source.getHeight(),
                    requestedTargetWidth,
                    requestedTargetHeight
            );
            int targetWidth = preservedGrid[0];
            int targetHeight = preservedGrid[1];
'''
access = replace_once(access, old_cpu_target, new_cpu_target, "CPU preserved pixel grid")

old_gpu_target = r'''                            int targetWidth = GameBoyFilter.getTargetWidth(
                                    windowFilterResolution,
                                    hardwareBitmap.getWidth()
                            );
                            int targetHeight = GameBoyFilter.getTargetHeight(
                                    windowFilterResolution,
                                    hardwareBitmap.getHeight()
                            );
'''
new_gpu_target = r'''                            int requestedTargetWidth = GameBoyFilter.getTargetWidth(
                                    windowFilterResolution,
                                    hardwareBitmap.getWidth()
                            );
                            int requestedTargetHeight = GameBoyFilter.getTargetHeight(
                                    windowFilterResolution,
                                    hardwareBitmap.getHeight()
                            );
                            int[] preservedGrid = ConsoleFrameRenderer.fitPixelGrid(
                                    hardwareBitmap.getWidth(),
                                    hardwareBitmap.getHeight(),
                                    requestedTargetWidth,
                                    requestedTargetHeight
                            );
                            int targetWidth = preservedGrid[0];
                            int targetHeight = preservedGrid[1];
'''
access = replace_once(access, old_gpu_target, new_gpu_target, "GPU preserved pixel grid")

old_cpu_crop = r'''            int[] crop = GameBoyFilter.getCenterCropBounds(windowFilterResolution, source.getWidth(), source.getHeight());
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    source,
                    new Rect(crop[0], crop[1], crop[2], crop[3]),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
'''
new_cpu_crop = r'''            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    source,
                    new Rect(0, 0, source.getWidth(), source.getHeight()),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
'''
access = replace_once(access, old_cpu_crop, new_cpu_crop, "CPU preserve full source aspect")

old_cpu_lcd = r'''            int[] chassisScreen = ConsoleFrameRenderer.getScreenRect(
                    service.windowFilterMode,
                    viewWidth,
                    viewHeight
            );
            left = chassisScreen[0];
            top = chassisScreen[1];
            drawWidth = chassisScreen[2];
            drawHeight = chassisScreen[3];
'''
new_cpu_lcd = r'''            int[] lcdContent = ConsoleFrameRenderer.getContentRect(
                    service.windowFilterMode,
                    viewWidth,
                    viewHeight,
                    current.getWidth(),
                    current.getHeight()
            );
            left = lcdContent[0];
            top = lcdContent[1];
            drawWidth = lcdContent[2];
            drawHeight = lcdContent[3];
'''
access = replace_once(access, old_cpu_lcd, new_cpu_lcd, "CPU physical LCD content window")
access_path.write_text(access)


gpu_path = root / "GpuFilterRenderer.java"
gpu = gpu_path.read_text()
old_gpu_lcd = r'''        int[] chassisScreen = ConsoleFrameRenderer.getScreenRect(
                mode,
                safeViewWidth,
                safeViewHeight
        );
        left = chassisScreen[0];
        top = chassisScreen[1];
        drawWidth = chassisScreen[2];
        drawHeight = chassisScreen[3];
        runtimeShader.setFloatUniform("viewSize", drawWidth, drawHeight);

        ConsoleFrameRenderer.draw(
'''
new_gpu_lcd = r'''        int[] lcdContent = ConsoleFrameRenderer.getContentRect(
                mode,
                safeViewWidth,
                safeViewHeight,
                source.getWidth(),
                source.getHeight()
        );
        left = lcdContent[0];
        top = lcdContent[1];
        drawWidth = lcdContent[2];
        drawHeight = lcdContent[3];
        runtimeShader.setFloatUniform("viewSize", drawWidth, drawHeight);
        runtimeShader.setFloatUniform("cropOffset", 0.0f, 0.0f);
        runtimeShader.setFloatUniform("cropSize", 1.0f, 1.0f);

        ConsoleFrameRenderer.draw(
'''
gpu = replace_once(gpu, old_gpu_lcd, new_gpu_lcd, "GPU physical LCD content window")
gpu_path.write_text(gpu)


# Fixed-console video: keep the source frame aspect before filtering, then fit the filtered
# frame inside the selected console LCD. The selected resolution controls pixel density only.
converter_path = root / "MediaFileConverter.java"
converter = converter_path.read_text()

old_video_dimensions = r'''            int contentTargetWidth = makeEven(GameBoyFilter.getVideoTargetWidth(
                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()
            ));
            int contentTargetHeight = makeEven(GameBoyFilter.getVideoTargetHeight(
                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()
            ));
            boolean chassisVideo = GameBoyFilter.isFixedAspectResolution(options.resolution);
            int targetWidth = chassisVideo
                    ? ConsoleFrameRenderer.VIDEO_FRAME_SIZE
                    : contentTargetWidth;
            int targetHeight = chassisVideo
                    ? ConsoleFrameRenderer.VIDEO_FRAME_SIZE
                    : contentTargetHeight;
'''
new_video_dimensions = r'''            int contentTargetWidth = makeEven(GameBoyFilter.getVideoTargetWidth(
                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()
            ));
            int contentTargetHeight = makeEven(GameBoyFilter.getVideoTargetHeight(
                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()
            ));
            boolean chassisVideo = GameBoyFilter.isFixedAspectResolution(options.resolution);
            if (chassisVideo) {
                int[] preservedGrid = ConsoleFrameRenderer.fitPixelGrid(
                        firstFrame.getWidth(),
                        firstFrame.getHeight(),
                        contentTargetWidth,
                        contentTargetHeight
                );
                contentTargetWidth = preservedGrid[0];
                contentTargetHeight = preservedGrid[1];
            }
            int targetWidth = chassisVideo
                    ? ConsoleFrameRenderer.VIDEO_FRAME_SIZE
                    : contentTargetWidth;
            int targetHeight = chassisVideo
                    ? ConsoleFrameRenderer.VIDEO_FRAME_SIZE
                    : contentTargetHeight;
'''
converter = replace_once(
    converter,
    old_video_dimensions,
    new_video_dimensions,
    "video source-aspect pixel grid",
)

converter = replace_once(
    converter,
    r'''    private static Bitmap prepareFilteredBitmap(
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
''',
    r'''    private static Bitmap prepareFilteredBitmap(
            Bitmap source,
            Options options,
            boolean preserveSourceAspect,
            int targetWidth,
            int targetHeight
    ) {
        int width = Math.max(1, targetWidth);
        int height = Math.max(1, targetHeight);
        int[] crop = preserveSourceAspect
                ? new int[]{0, 0, source.getWidth(), source.getHeight()}
                : GameBoyFilter.getCenterCropBounds(
                        options.resolution,
                        source.getWidth(),
                        source.getHeight()
                );
''',
    "video prepare preserve aspect flag",
)

old_video_prepare = r'''                        filtered = prepareFilteredBitmap(
                                sourceFrame,
                                options,
                                false,
                                contentTargetWidth,
                                contentTargetHeight
                        );
'''
new_video_prepare = r'''                        filtered = prepareFilteredBitmap(
                                sourceFrame,
                                options,
                                chassisVideo,
                                contentTargetWidth,
                                contentTargetHeight
                        );
'''
converter = replace_once(converter, old_video_prepare, new_video_prepare, "video preserve source aspect call")

converter = replace_once(
    converter,
    '                            + " chassis_background=" + chassisVideo\n',
    '                            + " chassis_background=" + chassisVideo\n'
    '                            + " source_aspect_preserved=" + chassisVideo\n',
    "video aspect performance evidence",
)
converter_path.write_text(converter)

print("v0.1.53 physical LCD window mapping with source aspect preservation applied", flush=True)
