#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_gb_bottom_crop_v055.py <generated_src_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# MediaProjection live path: keep the full source aspect at GB width resolution.
capture_path = root / "FilterCaptureService.java"
capture = capture_path.read_text()
capture = replace_once(
    capture,
    r'''            int targetWidth = GameBoyFilter.getTargetWidth(resolution, sourceWidth);
            int targetHeight = GameBoyFilter.getTargetHeight(resolution, sourceHeight);
''',
    r'''            int requestedTargetWidth = GameBoyFilter.getTargetWidth(resolution, sourceWidth);
            int requestedTargetHeight = GameBoyFilter.getTargetHeight(resolution, sourceHeight);
            int targetWidth = requestedTargetWidth;
            int targetHeight = requestedTargetHeight;
            if (GameBoyFilter.MODE_GB.equals(mode)) {
                targetHeight = Math.max(
                        1,
                        Math.round(targetWidth * (sourceHeight / (float) Math.max(1, sourceWidth)))
                );
            }
''',
    "GB MediaProjection target aspect",
)
capture = replace_once(
    capture,
    r'''            int[] crop = GameBoyFilter.getCenterCropBounds(resolution, sourceWidth, sourceHeight);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    captureBitmap,
                    new Rect(crop[0], crop[1], crop[2], crop[3]),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
''',
    r'''            int[] crop = GameBoyFilter.MODE_GB.equals(mode)
                    ? new int[]{0, 0, sourceWidth, sourceHeight}
                    : GameBoyFilter.getCenterCropBounds(resolution, sourceWidth, sourceHeight);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    captureBitmap,
                    new Rect(crop[0], crop[1], crop[2], crop[3]),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
''',
    "GB MediaProjection full-source downsample",
)
capture_path.write_text(capture)


# Accessibility CPU/GPU fallback: preserve source aspect at the requested GB width.
access_path = root / "FilterAccessibilityService.java"
access = access_path.read_text()
access = replace_once(
    access,
    r'''            int[] preservedGrid = ConsoleFrameRenderer.fitPixelGrid(
                    source.getWidth(), source.getHeight(),
                    requestedTargetWidth, requestedTargetHeight
            );
            int targetWidth = preservedGrid[0];
            int targetHeight = preservedGrid[1];
''',
    r'''            int[] preservedGrid = ConsoleFrameRenderer.fitPixelGrid(
                    source.getWidth(), source.getHeight(),
                    requestedTargetWidth, requestedTargetHeight
            );
            int targetWidth = preservedGrid[0];
            int targetHeight = preservedGrid[1];
            if (GameBoyFilter.MODE_GB.equals(windowFilterMode)) {
                targetWidth = requestedTargetWidth;
                targetHeight = Math.max(
                        1,
                        Math.round(targetWidth * (source.getHeight()
                                / (float) Math.max(1, source.getWidth())))
                );
            }
''',
    "GB accessibility CPU target aspect",
)
access = replace_once(
    access,
    r'''                            int[] preservedGrid = ConsoleFrameRenderer.fitPixelGrid(
                                    hardwareBitmap.getWidth(), hardwareBitmap.getHeight(),
                                    requestedTargetWidth, requestedTargetHeight
                            );
                            int targetWidth = preservedGrid[0];
                            int targetHeight = preservedGrid[1];
''',
    r'''                            int[] preservedGrid = ConsoleFrameRenderer.fitPixelGrid(
                                    hardwareBitmap.getWidth(), hardwareBitmap.getHeight(),
                                    requestedTargetWidth, requestedTargetHeight
                            );
                            int targetWidth = preservedGrid[0];
                            int targetHeight = preservedGrid[1];
                            if (GameBoyFilter.MODE_GB.equals(windowFilterMode)) {
                                targetWidth = requestedTargetWidth;
                                targetHeight = Math.max(
                                        1,
                                        Math.round(targetWidth * (hardwareBitmap.getHeight()
                                                / (float) Math.max(1, hardwareBitmap.getWidth())))
                                );
                            }
''',
    "GB accessibility GPU target aspect",
)

access = replace_once(
    access,
    r'''            canvas.drawBitmap(
                    current,
                    null,
                    new Rect(left, top, left + drawWidth, top + drawHeight),
                    paint
            );
''',
    r'''            int[] sourceRect = ConsoleFrameRenderer.getSourceRectForWidthFit(
                    service.windowFilterMode,
                    viewWidth,
                    viewHeight,
                    current.getWidth(),
                    current.getHeight()
            );
            canvas.drawBitmap(
                    current,
                    new Rect(
                            sourceRect[0],
                            sourceRect[1],
                            sourceRect[2],
                            sourceRect[3]
                    ),
                    new Rect(left, top, left + drawWidth, top + drawHeight),
                    paint
            );
''',
    "GB accessibility bottom crop",
)
access_path.write_text(access)


# GPU overlay: GB samples from the top of the source and trims only the bottom.
gpu_path = root / "GpuFilterRenderer.java"
gpu = gpu_path.read_text()
gpu = replace_once(
    gpu,
    r'''        runtimeShader.setFloatUniform("viewSize", drawWidth, drawHeight);
        runtimeShader.setFloatUniform("cropOffset", 0.0f, 0.0f);
        runtimeShader.setFloatUniform("cropSize", 1.0f, 1.0f);

        ConsoleFrameRenderer.draw(
''',
    r'''        runtimeShader.setFloatUniform("viewSize", drawWidth, drawHeight);
        float[] sourceCrop = ConsoleFrameRenderer.getSourceCropForWidthFit(
                mode,
                safeViewWidth,
                safeViewHeight,
                source.getWidth(),
                source.getHeight()
        );
        runtimeShader.setFloatUniform("cropOffset", sourceCrop[0], sourceCrop[1]);
        runtimeShader.setFloatUniform("cropSize", sourceCrop[2], sourceCrop[3]);

        ConsoleFrameRenderer.draw(
''',
    "GB GPU bottom crop",
)
gpu_path.write_text(gpu)

print("v0.1.55 GB live width fit, bottom crop, centered chassis, opaque outside-LCD background applied", flush=True)
