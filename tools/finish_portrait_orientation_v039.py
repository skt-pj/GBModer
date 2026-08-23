#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_portrait_orientation_v039.py <generated_src_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"
path = root / "VideoGpuConverter.java"
text = path.read_text()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return source.replace(old, new, 1)


# SurfaceTexture's transform matrix already adapts the streamed texture for sampling.
# The display-space rotation passed here must therefore follow Android KEY_ROTATION's
# clockwise convention. The previous v0.1.38 90/270 mapping was reversed, which made
# portrait output appear upside down after decoder auto-rotation was disabled.
marker = "    private static int normalizeRotation(int rotation) {\n"
helper = r'''    static float[] mapDisplayUvForRotation(
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
                // Android rotation metadata is clockwise. With the quad/SurfaceTexture
                // coordinate convention used here, clockwise 90 maps to the old 270 path.
                mapped[i] = 1.0f - v;
                mapped[i + 1] = u;
            } else if (rotation == 180) {
                mapped[i] = 1.0f - u;
                mapped[i + 1] = 1.0f - v;
            } else if (rotation == 270) {
                mapped[i] = v;
                mapped[i + 1] = 1.0f - u;
            } else {
                mapped[i] = u;
                mapped[i + 1] = v;
            }
        }
        return mapped;
    }

'''
text = replace_once(text, marker, helper + marker, "rotation mapping helper")

text = replace_once(
    text,
    "            textureBuffer = allocateFloatBuffer(textureCoordinates(\n"
    "                    rotation,\n"
    "                    cropLeft,\n"
    "                    cropTop,\n"
    "                    cropRight,\n"
    "                    cropBottom\n"
    "            ));\n"
    "            identityTextureBuffer = allocateFloatBuffer(textureCoordinates(0, 0f, 0f, 1f, 1f));\n",
    "            textureBuffer = allocateFloatBuffer(VideoGpuConverter.mapDisplayUvForRotation(\n"
    "                    rotation,\n"
    "                    cropLeft,\n"
    "                    cropTop,\n"
    "                    cropRight,\n"
    "                    cropBottom\n"
    "            ));\n"
    "            identityTextureBuffer = allocateFloatBuffer(\n"
    "                    VideoGpuConverter.mapDisplayUvForRotation(0, 0f, 0f, 1f, 1f)\n"
    "            );\n",
    "renderer rotation helper use",
)

text = replace_once(
    text,
    '                            + " decoder_rotation=0"\n',
    '                            + " decoder_rotation=0"\n'
    '                            + " rotation_mapping=clockwise_upright"\n',
    "rotation mapping performance evidence",
)

path.write_text(text)
print("v0.1.39 portrait video rotation follows Android clockwise metadata without upside-down output")
