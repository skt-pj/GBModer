#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_gpu_source_v015.py <generated_src_root>")

root = Path(sys.argv[1])
path = root / "com/sktpj/gbmoder/FilterAccessibilityService.java"
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    "    private static final long GPU_RETRY_DELAY_MS = 120L;\n",
    "    private static final long GPU_RETRY_DELAY_MS = 350L;\n",
    "device screenshot cadence",
)

replace_once(
    '''        gpuWindowPathDisabled = true;
        Log.e(TAG, "GPU hardware filter disabled; falling back to CPU path", error);
        PerformanceLog.log("gpu_path_disabled pipeline=accessibility_window error="
                + error.getClass().getSimpleName());
''',
    '''        gpuWindowPathDisabled = true;
        Log.e(TAG, "GPU hardware filter disabled; falling back to CPU path", error);
        String errorMessage = error.getMessage();
        if (errorMessage == null) {
            errorMessage = "";
        } else {
            errorMessage = errorMessage.replace('\\n', ' ').replace('\\r', ' ');
        }
        PerformanceLog.log("gpu_path_disabled pipeline=accessibility_window error="
                + error.getClass().getSimpleName()
                + " message=" + errorMessage);
''',
    "gpu disable diagnostics",
)

replace_once(
    '''                                showGpuFrame(
                                        hardwareBitmap,
                                        target.bounds,
                                        targetWidth,
                                        targetHeight,
                                        windowFilterMode,
                                        windowFilterBrightness,
                                        windowFilterContrast,
                                        windowFilterDither
                                );
                                long overlayFinishedNs = SystemClock.elapsedRealtimeNanos();
''',
    '''                                showGpuFrame(
                                        hardwareBitmap,
                                        target.bounds,
                                        targetWidth,
                                        targetHeight,
                                        windowFilterMode,
                                        windowFilterBrightness,
                                        windowFilterContrast,
                                        windowFilterDither
                                );
                                if (!usesGpuWindowPath()) {
                                    scheduleNextWindowCapture(CPU_FALLBACK_CAPTURE_INTERVAL_MS);
                                    return;
                                }
                                long overlayFinishedNs = SystemClock.elapsedRealtimeNanos();
''',
    "gpu init fallback guard",
)

replace_once(
    '''                                scheduleNextWindowCapture(0L);
''',
    '''                                long elapsedMs = totalNs / 1_000_000L;
                                long delay = Math.max(0L, GPU_RETRY_DELAY_MS - elapsedMs);
                                scheduleNextWindowCapture(delay);
''',
    "gpu cadence",
)

replace_once(
    '''        void setGpuFrame(
                Bitmap newFrame,
                int targetWidth,
                int targetHeight,
                String mode,
                int brightness,
                int contrast,
                boolean dither
        ) {
            probeMode = false;
''',
    '''        void setGpuFrame(
                Bitmap newFrame,
                int targetWidth,
                int targetHeight,
                String mode,
                int brightness,
                int contrast,
                boolean dither
        ) {
            if (gpuRenderer == null || service.gpuWindowPathDisabled) {
                if (newFrame != null && !newFrame.isRecycled()) {
                    newFrame.recycle();
                }
                return;
            }
            probeMode = false;
''',
    "do not display unfiltered gpu fallback frame",
)

replace_once(
    '''                } catch (Throwable error) {
                    gpuFrameMode = false;
                    service.disableGpuWindowPath(error);
                }
            }

            canvas.drawBitmap(
''',
    '''                } catch (Throwable error) {
                    gpuFrameMode = false;
                    service.disableGpuWindowPath(error);
                    return;
                }
            }

            canvas.drawBitmap(
''',
    "do not raw-draw after gpu failure",
)

path.write_text(text)
