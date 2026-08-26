#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source_gpu = (root / "app/src/main/java/com/sktpj/gbmoder/VideoGpuConverter.java").read_text()
generated_gpu = (root / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/VideoGpuConverter.java").read_text()
generated_converter = (root / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MediaFileConverter.java").read_text()
prepare = (root / "tools/prepare_all_sources_v020.py").read_text()


def need(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r}")
    print(f"PASS {label}")


need(prepare, "finish_video_gpu_v032.py", "GPU finalizer registered")

need(source_gpu, "encoder.createInputSurface()", "H264 encoder Surface input")
need(source_gpu, "decoder.configure(sourceFormat, gpuPipe.getDecoderSurface()", "decoder renders to Surface")
need(source_gpu, "samplerExternalOES", "external OES GPU texture")
need(source_gpu, "EGLExt.eglPresentationTimeANDROID", "source PTS sent to encoder Surface")
need(source_gpu, "EGL14.eglSwapBuffers", "GPU frame submitted to encoder")
need(source_gpu, "GLES20.glDrawArrays", "OpenGL shader draw")
need(source_gpu, "render_path=gpu_surface_shader", "GPU path performance evidence")
need(source_gpu, "rgba_yuv_cpu=false", "CPU RGBA to YUV removed from GPU path")
need(source_gpu, "source_pts=true", "source presentation timestamps retained")
need(source_gpu, "glReadPixels", "GBC histogram readback")
need(source_gpu, "GBC_COLOR_LIMIT = 56", "GBC visible color limit retained")
need(source_gpu, "lookupTextureId", "GBC GPU lookup remap")

for forbidden in ("android.graphics.Bitmap", "getFrameAtTime(", "getScaledFrameAtTime(", "bitmapToYuv420("):
    if forbidden in source_gpu:
        raise SystemExit(f"FAIL GPU path still uses CPU bitmap pipeline: {forbidden}")
print("PASS GPU path has no Bitmap frame extraction or CPU YUV conversion")

need(generated_converter, "VideoGpuConverter.convert(context, source, output, options, progress);", "GPU is default video route")
need(generated_converter, "private static void convertVideoCpuFallback", "CPU path retained only as fallback")
need(generated_converter, "catch (VideoGpuConverter.GpuUnavailableException unavailable)", "fallback limited to unavailable GPU setup")
need(generated_gpu, "throw (Exception) error;", "generated GPU encoder exception bridge")
if "throw error;" in generated_gpu:
    raise SystemExit("FAIL generated GPU source throws raw Throwable")
print("PASS generated GPU source is Java-exception-safe")

print("VIDEO GPU CONVERSION v0.1.32 FEATURE GATE: PASS")
