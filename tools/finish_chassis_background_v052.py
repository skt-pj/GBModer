#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_chassis_background_v052.py <generated_src_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# Live/accessibility GPU: move the shader viewport from the old centered full-aspect
# rectangle into the physical LCD rectangle of the selected chassis image.
gpu_path = root / "GpuFilterRenderer.java"
gpu = gpu_path.read_text()
old_gpu = r'''        ConsoleFrameRenderer.draw(
                canvas,
                mode,
                safeViewWidth,
                safeViewHeight,
                left,
                top,
                drawWidth,
                drawHeight
        );
        canvas.save();
'''
new_gpu = r'''        int[] chassisScreen = ConsoleFrameRenderer.getScreenRect(
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
                canvas,
                mode,
                safeViewWidth,
                safeViewHeight,
                left,
                top,
                drawWidth,
                drawHeight
        );
        canvas.save();
'''
gpu = replace_once(gpu, old_gpu, new_gpu, "GPU chassis LCD viewport")
gpu_path.write_text(gpu)


# Live + embedded game CPU fallback: use the same physical LCD rectangle.
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()
old_access = r'''            ConsoleFrameRenderer.draw(
                    canvas,
                    service.windowFilterMode,
                    viewWidth,
                    viewHeight,
                    left,
                    top,
                    drawWidth,
                    drawHeight
            );
            canvas.drawBitmap(
'''
new_access = r'''            int[] chassisScreen = ConsoleFrameRenderer.getScreenRect(
                    service.windowFilterMode,
                    viewWidth,
                    viewHeight
            );
            left = chassisScreen[0];
            top = chassisScreen[1];
            drawWidth = chassisScreen[2];
            drawHeight = chassisScreen[3];

            ConsoleFrameRenderer.draw(
                    canvas,
                    service.windowFilterMode,
                    viewWidth,
                    viewHeight,
                    left,
                    top,
                    drawWidth,
                    drawHeight
            );
            canvas.drawBitmap(
'''
access = replace_once(access, old_access, new_access, "CPU chassis LCD viewport")
access_path.write_text(access)


# File-video conversion: for fixed GB/GBC/GBA/DS presets, keep the filtered console
# resolution as the content resolution, then composite each frame into a 512x512 chassis
# image. Route these jobs through the existing CPU fallback so the chassis bitmap can be
# composited deterministically; non-fixed phone/native video keeps the GPU path unchanged.
converter_path = root / "MediaFileConverter.java"
converter = converter_path.read_text()
wrapper_signature = r'''    public static void convertVideo(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
'''
wrapper_replacement = wrapper_signature + r'''        if (GameBoyFilter.isFixedAspectResolution(options.resolution)) {
            notifyProgress(progress, 1, "ゲーム機背景を動画へ合成しています");
            convertVideoCpuFallback(context, source, output, options, progress);
            return;
        }
'''
converter = replace_once(
    converter,
    wrapper_signature,
    wrapper_replacement,
    "fixed-preset chassis video CPU route",
)

old_targets = r'''            int targetWidth = makeEven(GameBoyFilter.getVideoTargetWidth(
                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()
            ));
            int targetHeight = makeEven(GameBoyFilter.getVideoTargetHeight(
                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()
            ));
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
'''
new_targets = r'''            int contentTargetWidth = makeEven(GameBoyFilter.getVideoTargetWidth(
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
            int workingWidth = GameBoyFilter.getCenterCropWorkingWidth(
                    options.resolution,
                    firstFrame.getWidth(),
                    firstFrame.getHeight(),
                    contentTargetWidth,
                    contentTargetHeight
            );
            int workingHeight = GameBoyFilter.getCenterCropWorkingHeight(
                    options.resolution,
                    firstFrame.getWidth(),
                    firstFrame.getHeight(),
                    contentTargetWidth,
                    contentTargetHeight
            );
'''
converter = replace_once(converter, old_targets, new_targets, "CPU chassis video dimensions")

old_prepare = r'''                        filtered = prepareFilteredBitmap(
                                sourceFrame,
                                options,
                                false,
                                targetWidth,
                                targetHeight
                        );
                        byte[] yuv = bitmapToYuv420(filtered, colorFormat);
'''
new_prepare = r'''                        filtered = prepareFilteredBitmap(
                                sourceFrame,
                                options,
                                false,
                                contentTargetWidth,
                                contentTargetHeight
                        );
                        if (chassisVideo) {
                            Bitmap content = filtered;
                            filtered = ConsoleFrameRenderer.composeVideoFrame(content, options.mode);
                            if (content != sourceFrame && !content.isRecycled()) {
                                content.recycle();
                            }
                        }
                        byte[] yuv = bitmapToYuv420(filtered, colorFormat);
'''
converter = replace_once(converter, old_prepare, new_prepare, "CPU chassis video composition")

converter = replace_once(
    converter,
    '                            + " target=" + targetWidth + "x" + targetHeight\n',
    '                            + " target=" + targetWidth + "x" + targetHeight\n'
    '                            + " chassis_background=" + chassisVideo\n',
    "chassis video performance evidence",
)
converter_path.write_text(converter)

print("v0.1.52 supplied GB/GBC/GBA/DS chassis backgrounds applied to live, game, and video", flush=True)
