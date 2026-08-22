#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: run_console_frame_v044.py <generated_src_root>")

repo = Path(__file__).resolve().parents[1]
script = repo / "tools/finish_console_frame_v044.py"
source = script.read_text()

helper_old = '''def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)
'''
helper_new = '''def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count < 1:
        raise SystemExit(f"{label}: expected at least one match, got {count}")
    return text.replace(old, new, 1)
'''
if source.count(helper_old) != 1:
    raise SystemExit("v0.1.44 finalizer replacement helper shape changed")
source = source.replace(helper_old, helper_new, 1)

# v0.1.33 made the GPU renderer crop-aware by adding sourceWidth/sourceHeight to
# GpuPipe and FrameRenderer. Adapt the v0.1.44 finalizer to that current shape
# instead of the pre-v0.1.33 constructor signatures it was originally written for.
gpupipe_old = '''video = replace_once(
    video,
    ''' + "'''" + '''                int targetWidth,
                int targetHeight,
                int rotation,
                MediaFileConverter.Options options
''' + "'''" + ''',
    ''' + "'''" + '''                int targetWidth,
                int targetHeight,
                int outputWidth,
                int outputHeight,
                int rotation,
                MediaFileConverter.Options options
''' + "'''" + ''',
    "GpuPipe constructor signature",
)
'''
gpupipe_new = '''video = replace_once(
    video,
    ''' + "'''" + '''                int sourceWidth,
                int sourceHeight,
                int targetWidth,
                int targetHeight,
                int rotation,
                MediaFileConverter.Options options
''' + "'''" + ''',
    ''' + "'''" + '''                int sourceWidth,
                int sourceHeight,
                int targetWidth,
                int targetHeight,
                int outputWidth,
                int outputHeight,
                int rotation,
                MediaFileConverter.Options options
''' + "'''" + ''',
    "GpuPipe constructor signature",
)
'''
if source.count(gpupipe_old) != 1:
    raise SystemExit("v0.1.44 GpuPipe source-aware patch marker changed")
source = source.replace(gpupipe_old, gpupipe_new, 1)

frame_call_old = '''video = replace_once(
    video,
    "                renderer = new FrameRenderer(targetWidth, targetHeight, rotation, options);\\n",
    "                renderer = new FrameRenderer(\\n"
    "                        targetWidth, targetHeight, outputWidth, outputHeight, rotation, options\\n"
    "                );\\n",
    "FrameRenderer framed constructor call",
)
'''
frame_call_new = '''video = replace_once(
    video,
    "                renderer = new FrameRenderer(\\n"
    "                        sourceWidth,\\n"
    "                        sourceHeight,\\n"
    "                        targetWidth,\\n"
    "                        targetHeight,\\n"
    "                        rotation,\\n"
    "                        options\\n"
    "                );\\n",
    "                renderer = new FrameRenderer(\\n"
    "                        sourceWidth,\\n"
    "                        sourceHeight,\\n"
    "                        targetWidth,\\n"
    "                        targetHeight,\\n"
    "                        outputWidth,\\n"
    "                        outputHeight,\\n"
    "                        rotation,\\n"
    "                        options\\n"
    "                );\\n",
    "FrameRenderer framed constructor call",
)
'''
if source.count(frame_call_old) != 1:
    raise SystemExit("v0.1.44 FrameRenderer call patch marker changed")
source = source.replace(frame_call_old, frame_call_new, 1)

frame_ctor_old = '''video = replace_once(
    video,
    ''' + "'''" + '''                int targetWidth,
                int targetHeight,
                int rotation,
                MediaFileConverter.Options options
        ) {
            this.targetWidth = targetWidth;
            this.targetHeight = targetHeight;
            this.options = options;
''' + "'''" + ''',
    ''' + "'''" + '''                int targetWidth,
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
''' + "'''" + ''',
    "FrameRenderer frame constructor",
)
'''
frame_ctor_new = '''video = replace_once(
    video,
    ''' + "'''" + '''                int sourceWidth,
                int sourceHeight,
                int targetWidth,
                int targetHeight,
                int rotation,
                MediaFileConverter.Options options
        ) {
            this.targetWidth = targetWidth;
            this.targetHeight = targetHeight;
            this.options = options;
''' + "'''" + ''',
    ''' + "'''" + '''                int sourceWidth,
                int sourceHeight,
                int targetWidth,
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
''' + "'''" + ''',
    "FrameRenderer frame constructor",
)
'''
if source.count(frame_ctor_old) != 1:
    raise SystemExit("v0.1.44 FrameRenderer constructor patch marker changed")
source = source.replace(frame_ctor_old, frame_ctor_new, 1)

sys.argv = [str(script), sys.argv[1]]
exec(compile(source, str(script), "exec"), {"__name__": "__main__", "__file__": str(script)})
