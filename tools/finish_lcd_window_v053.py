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


# Live/game: preserve the captured window aspect. Resolution controls pixel density only.
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()

access = replace_once(
    access,
    r'''            int targetWidth = GameBoyFilter.getTargetWidth(
                    windowFilterResolution,
                    source.getWidth()
            );
            int targetHeight = GameBoyFilter.getTargetHeight(
                    windowFilterResolution,
                    source.getHeight()
            );
''',
    r'''            int requestedTargetWidth = GameBoyFilter.getTargetWidth(
                    windowFilterResolution,
                    source.getWidth()
            );
            int requestedTargetHeight = GameBoyFilter.getTargetHeight(
                    windowFilterResolution,
                    source.getHeight()
            );
            int[] preservedGrid = ConsoleFrameRenderer.fitPixelGrid(
                    source.getWidth(), source.getHeight(),
                    requestedTargetWidth, requestedTargetHeight
            );
            int targetWidth = preservedGrid[0];
            int targetHeight = preservedGrid[1];
''',
    "CPU preserved pixel grid",
)

access = replace_once(
    access,
    r'''                            int targetWidth = GameBoyFilter.getTargetWidth(
                                    windowFilterResolution,
                                    hardwareBitmap.getWidth()
                            );
                            int targetHeight = GameBoyFilter.getTargetHeight(
                                    windowFilterResolution,
                                    hardwareBitmap.getHeight()
                            );
''',
    r'''                            int requestedTargetWidth = GameBoyFilter.getTargetWidth(
                                    windowFilterResolution,
                                    hardwareBitmap.getWidth()
                            );
                            int requestedTargetHeight = GameBoyFilter.getTargetHeight(
                                    windowFilterResolution,
                                    hardwareBitmap.getHeight()
                            );
                            int[] preservedGrid = ConsoleFrameRenderer.fitPixelGrid(
                                    hardwareBitmap.getWidth(), hardwareBitmap.getHeight(),
                                    requestedTargetWidth, requestedTargetHeight
                            );
                            int targetWidth = preservedGrid[0];
                            int targetHeight = preservedGrid[1];
''',
    "GPU preserved pixel grid",
)

access = replace_once(
    access,
    r'''            int[] chassisScreen = ConsoleFrameRenderer.getScreenRect(
                    service.windowFilterMode,
                    viewWidth,
                    viewHeight
            );
            left = chassisScreen[0];
            top = chassisScreen[1];
            drawWidth = chassisScreen[2];
            drawHeight = chassisScreen[3];
''',
    r'''            int[] lcdContent = ConsoleFrameRenderer.getContentRect(
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
''',
    "CPU physical LCD content window",
)
access_path.write_text(access)


gpu_path = root / "GpuFilterRenderer.java"
gpu = gpu_path.read_text()
gpu = replace_once(
    gpu,
    r'''        int[] chassisScreen = ConsoleFrameRenderer.getScreenRect(
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
''',
    r'''        int[] lcdContent = ConsoleFrameRenderer.getContentRect(
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
''',
    "GPU physical LCD content window",
)
gpu_path.write_text(gpu)


# Video: preserve the source aspect through filtering, then fit it inside the physical LCD.
converter_path = root / "MediaFileConverter.java"
converter = converter_path.read_text()

converter = replace_once(
    converter,
    r'''            int contentTargetWidth = makeEven(GameBoyFilter.getVideoTargetWidth(
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
''',
    r'''            int contentTargetWidth = makeEven(GameBoyFilter.getVideoTargetWidth(
                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()
            ));
            int contentTargetHeight = makeEven(GameBoyFilter.getVideoTargetHeight(
                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()
            ));
            boolean chassisVideo = GameBoyFilter.isFixedAspectResolution(options.resolution);
            if (chassisVideo) {
                int[] preservedGrid = ConsoleFrameRenderer.fitPixelGrid(
                        firstFrame.getWidth(), firstFrame.getHeight(),
                        contentTargetWidth, contentTargetHeight
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
''',
    "video source-aspect pixel grid",
)

converter = replace_once(
    converter,
    "            boolean ignored,\n            int targetWidth,\n            int targetHeight\n    ) {\n",
    "            boolean preserveSourceAspect,\n            int targetWidth,\n            int targetHeight\n    ) {\n",
    "video preserve-aspect parameter",
)

converter = replace_once(
    converter,
    r'''        int[] crop = GameBoyFilter.getCenterCropBoundsForTarget(
                options.resolution,
                source.getWidth(),
                source.getHeight(),
                width,
                height
        );
''',
    r'''        int[] crop = preserveSourceAspect
                ? new int[]{0, 0, source.getWidth(), source.getHeight()}
                : GameBoyFilter.getCenterCropBoundsForTarget(
                        options.resolution,
                        source.getWidth(),
                        source.getHeight(),
                        width,
                        height
                );
''',
    "video full-source aspect preservation",
)

converter = replace_once(
    converter,
    r'''                        filtered = prepareFilteredBitmap(
                                sourceFrame,
                                options,
                                false,
                                contentTargetWidth,
                                contentTargetHeight
                        );
''',
    r'''                        filtered = prepareFilteredBitmap(
                                sourceFrame,
                                options,
                                chassisVideo,
                                contentTargetWidth,
                                contentTargetHeight
                        );
''',
    "video preserve source aspect call",
)

converter = replace_once(
    converter,
    '                            + " chassis_background=" + chassisVideo\n',
    '                            + " chassis_background=" + chassisVideo\n'
    '                            + " source_aspect_preserved=" + chassisVideo\n',
    "video aspect performance evidence",
)
converter_path.write_text(converter)

print("v0.1.53 physical LCD window mapping with source aspect preservation applied", flush=True)
