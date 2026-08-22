#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_portrait_video_v038.py <generated_src_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# Fixed console presets keep the same physical aspect when the video is portrait:
# GB/GBC 160x144 -> 144x160, GBA 240x160 -> 160x240, DS 256x192 -> 192x256.
filter_path = root / "GameBoyFilter.java"
filter_text = filter_path.read_text()
marker = "    public static int getCenterCropWorkingWidth(\n"
helpers = r'''    public static int getVideoTargetWidth(
            String resolution,
            int displayWidth,
            int displayHeight
    ) {
        int width = Math.max(1, displayWidth);
        int height = Math.max(1, displayHeight);
        int targetWidth = getTargetWidth(resolution, width);
        int targetHeight = getTargetHeight(resolution, height);
        if (isFixedAspectResolution(resolution) && height > width) {
            return targetHeight;
        }
        return targetWidth;
    }

    public static int getVideoTargetHeight(
            String resolution,
            int displayWidth,
            int displayHeight
    ) {
        int width = Math.max(1, displayWidth);
        int height = Math.max(1, displayHeight);
        int targetWidth = getTargetWidth(resolution, width);
        int targetHeight = getTargetHeight(resolution, height);
        if (isFixedAspectResolution(resolution) && height > width) {
            return targetWidth;
        }
        return targetHeight;
    }

    public static int[] getCenterCropBoundsForTarget(
            String resolution,
            int sourceWidth,
            int sourceHeight,
            int targetWidth,
            int targetHeight
    ) {
        int width = Math.max(1, sourceWidth);
        int height = Math.max(1, sourceHeight);
        if (!isFixedAspectResolution(resolution)) {
            return new int[]{0, 0, width, height};
        }

        int safeTargetWidth = Math.max(1, targetWidth);
        int safeTargetHeight = Math.max(1, targetHeight);
        long sourceCross = (long) width * safeTargetHeight;
        long targetCross = (long) height * safeTargetWidth;

        int cropWidth = width;
        int cropHeight = height;
        if (sourceCross > targetCross) {
            cropWidth = Math.max(
                    1,
                    Math.min(width, (int) Math.round(
                            height * (safeTargetWidth / (double) safeTargetHeight)
                    ))
            );
        } else if (sourceCross < targetCross) {
            cropHeight = Math.max(
                    1,
                    Math.min(height, (int) Math.round(
                            width * (safeTargetHeight / (double) safeTargetWidth)
                    ))
            );
        }

        int left = Math.max(0, (width - cropWidth) / 2);
        int top = Math.max(0, (height - cropHeight) / 2);
        return new int[]{left, top, left + cropWidth, top + cropHeight};
    }

'''
filter_text = replace_once(filter_text, marker, helpers + marker, "portrait video helpers")
old_working_crop = "        int[] crop = getCenterCropBounds(resolution, width, height);\n"
if filter_text.count(old_working_crop) != 2:
    raise SystemExit(
        f"crop-aware working dimensions: expected 2 matches, got {filter_text.count(old_working_crop)}"
    )
filter_text = filter_text.replace(
    old_working_crop,
    "        int[] crop = getCenterCropBoundsForTarget(\n"
    "                resolution, width, height, targetWidth, targetHeight\n"
    "        );\n",
    2,
)
filter_path.write_text(filter_text)


# CPU video fallback uses the actual portrait output dimensions and crops to that rotated aspect.
converter_path = root / "MediaFileConverter.java"
converter = converter_path.read_text()
converter = replace_once(
    converter,
    "            int targetWidth = makeEven(GameBoyFilter.getTargetWidth(options.resolution, firstFrame.getWidth()));\n"
    "            int targetHeight = makeEven(GameBoyFilter.getTargetHeight(options.resolution, firstFrame.getHeight()));\n",
    "            int targetWidth = makeEven(GameBoyFilter.getVideoTargetWidth(\n"
    "                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()\n"
    "            ));\n"
    "            int targetHeight = makeEven(GameBoyFilter.getVideoTargetHeight(\n"
    "                    options.resolution, firstFrame.getWidth(), firstFrame.getHeight()\n"
    "            ));\n",
    "CPU portrait video target",
)
converter = replace_once(
    converter,
    "        int[] crop = GameBoyFilter.getCenterCropBounds(\n"
    "                options.resolution,\n"
    "                source.getWidth(),\n"
    "                source.getHeight()\n"
    "        );\n",
    "        int[] crop = GameBoyFilter.getCenterCropBoundsForTarget(\n"
    "                options.resolution,\n"
    "                source.getWidth(),\n"
    "                source.getHeight(),\n"
    "                width,\n"
    "                height\n"
    "        );\n",
    "CPU target-oriented crop",
)
converter_path.write_text(converter)


# GPU video path: neutralize MediaCodec's automatic Surface rotation because this pipeline
# explicitly maps rotation in texture coordinates. Then choose portrait output dimensions.
video_path = root / "VideoGpuConverter.java"
video = video_path.read_text()
video = replace_once(
    video,
    "            int rotation = normalizeRotation(getInt(sourceFormat, MediaFormat.KEY_ROTATION, 0));\n"
    "            int displayWidth = (rotation == 90 || rotation == 270) ? codedHeight : codedWidth;\n"
    "            int displayHeight = (rotation == 90 || rotation == 270) ? codedWidth : codedHeight;\n"
    "            int targetWidth = makeEven(GameBoyFilter.getTargetWidth(options.resolution, displayWidth));\n"
    "            int targetHeight = makeEven(GameBoyFilter.getTargetHeight(options.resolution, displayHeight));\n",
    "            int rotation = normalizeRotation(getInt(sourceFormat, MediaFormat.KEY_ROTATION, 0));\n"
    "            int displayWidth = (rotation == 90 || rotation == 270) ? codedHeight : codedWidth;\n"
    "            int displayHeight = (rotation == 90 || rotation == 270) ? codedWidth : codedHeight;\n"
    "            int targetWidth = makeEven(GameBoyFilter.getVideoTargetWidth(\n"
    "                    options.resolution, displayWidth, displayHeight\n"
    "            ));\n"
    "            int targetHeight = makeEven(GameBoyFilter.getVideoTargetHeight(\n"
    "                    options.resolution, displayWidth, displayHeight\n"
    "            ));\n"
    "            if (sourceFormat.containsKey(MediaFormat.KEY_ROTATION)) {\n"
    "                sourceFormat.setInteger(MediaFormat.KEY_ROTATION, 0);\n"
    "            }\n",
    "GPU portrait target and decoder rotation ownership",
)
video = replace_once(
    video,
    "            int[] crop = GameBoyFilter.getCenterCropBounds(\n"
    "                    options.resolution,\n"
    "                    displaySourceWidth,\n"
    "                    displaySourceHeight\n"
    "            );\n",
    "            int[] crop = GameBoyFilter.getCenterCropBoundsForTarget(\n"
    "                    options.resolution,\n"
    "                    displaySourceWidth,\n"
    "                    displaySourceHeight,\n"
    "                    targetWidth,\n"
    "                    targetHeight\n"
    "            );\n",
    "GPU portrait target crop",
)
video = replace_once(
    video,
    '                            + " center_crop=true"\n',
    '                            + " center_crop=true"\n'
    '                            + " decoder_rotation=0"\n'
    '                            + " display=" + displayWidth + "x" + displayHeight\n'
    '                            + " portrait_output=" + (targetHeight > targetWidth)\n',
    "portrait video performance evidence",
)
video_path.write_text(video)

print("v0.1.38 portrait video output preserves the rotated fixed-preset aspect")
