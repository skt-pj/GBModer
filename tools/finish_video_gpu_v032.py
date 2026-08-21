#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_video_gpu_v032.py <generated_src_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"
converter_path = root / "MediaFileConverter.java"
converter = converter_path.read_text()

signature = '''    public static void convertVideo(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
'''
count = converter.count(signature)
if count != 1:
    raise SystemExit(f"convertVideo signature: expected exactly one match, got {count}")

fallback_signature = '''    private static void convertVideoCpuFallback(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
'''

converter = converter.replace(signature, fallback_signature, 1)

wrapper = r'''    public static void convertVideo(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
        try {
            VideoGpuConverter.convert(context, source, output, options, progress);
            return;
        } catch (VideoGpuConverter.GpuUnavailableException unavailable) {
            PerformanceLog.log(
                    "video_gpu_unavailable"
                            + " fallback=cpu"
                            + " error=" + unavailable.getClass().getSimpleName()
                            + " message=" + String.valueOf(unavailable.getMessage()).replace(' ', '_')
            );
            notifyProgress(
                    progress,
                    1,
                    "GPU経路を利用できないため互換CPU経路へ切り替えます"
            );
        }
        convertVideoCpuFallback(context, source, output, options, progress);
    }

'''

marker = fallback_signature
if marker not in converter:
    raise SystemExit("CPU fallback marker missing after rename")
converter = converter.replace(marker, wrapper + marker, 1)
converter_path.write_text(converter)

gpu_path = root / "VideoGpuConverter.java"
gpu = gpu_path.read_text()
old = '''        } catch (Throwable error) {
            try {
                encoder.release();
            } catch (Throwable ignored) {
            }
            throw error;
        }
'''
new = '''        } catch (Throwable error) {
            try {
                encoder.release();
            } catch (Throwable ignored) {
            }
            if (error instanceof Exception) {
                throw (Exception) error;
            }
            throw new RuntimeException(error);
        }
'''
if gpu.count(old) != 1:
    raise SystemExit("GPU encoder error bridge marker mismatch")
gpu = gpu.replace(old, new, 1)
gpu_path.write_text(gpu)

print("v0.1.32 video conversion defaults to decoder Surface -> OpenGL ES -> encoder Surface")
