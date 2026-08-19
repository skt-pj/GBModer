package com.sktpj.gbmoder;

import android.content.Context;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.SystemClock;
import android.util.Log;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Locale;

public final class PerformanceLog {
    private static final String TAG = "GBModerPerf";
    private static final Object LOCK = new Object();

    private static HandlerThread logThread;
    private static Handler logHandler;
    private static File logFile;

    private PerformanceLog() {
    }

    public static void startSession(
            Context context,
            String pipeline,
            String mode,
            String resolution,
            int brightness,
            int contrast,
            boolean dither,
            long targetIntervalMs
    ) {
        if (context == null) {
            return;
        }

        ensureThread();
        File root = context.getExternalFilesDir(null);
        if (root == null) {
            root = context.getFilesDir();
        }
        logFile = new File(root, "gbmoder-performance.log");

        String header = "session_start"
                + " wall_ms=" + System.currentTimeMillis()
                + " pipeline=" + pipeline
                + " mode=" + mode
                + " resolution=" + resolution
                + " brightness=" + brightness
                + " contrast=" + contrast
                + " dither=" + dither
                + " target_interval_ms=" + targetIntervalMs
                + " file=" + logFile.getAbsolutePath();
        writeAsync(header, true);
    }

    public static void log(String message) {
        String line = "elapsed_ms=" + SystemClock.elapsedRealtime() + " " + message;
        Log.i(TAG, line);
        writeAsync(line, false);
    }

    public static String formatMs(long nanos) {
        return String.format(Locale.US, "%.3f", nanos / 1_000_000.0);
    }

    public static String getLogPath() {
        File file = logFile;
        return file == null ? "" : file.getAbsolutePath();
    }

    private static void ensureThread() {
        synchronized (LOCK) {
            if (logThread != null && logThread.isAlive() && logHandler != null) {
                return;
            }
            logThread = new HandlerThread("GBModerPerformanceLog");
            logThread.start();
            logHandler = new Handler(logThread.getLooper());
        }
    }

    private static void writeAsync(String line, boolean truncate) {
        ensureThread();
        Handler handler = logHandler;
        File file = logFile;
        if (handler == null || file == null) {
            return;
        }

        Log.i(TAG, line);
        handler.post(() -> {
            try (FileWriter writer = new FileWriter(file, !truncate)) {
                writer.write(line);
                writer.write('\n');
            } catch (IOException error) {
                Log.e(TAG, "Failed to write performance log", error);
            }
        });
    }
}
