package com.sktpj.gbmoder;

import android.content.Context;
import android.net.Uri;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.io.OutputStream;
import java.util.Locale;

public final class PerformanceLog {
    private static final String TAG = "GBModerPerf";
    private static final Object LOCK = new Object();
    private static final String FILE_NAME = "gbmoder-performance.log";
    private static final Handler MAIN_HANDLER = new Handler(Looper.getMainLooper());

    private static HandlerThread logThread;
    private static Handler logHandler;
    private static File logFile;

    private PerformanceLog() {
    }

    public interface SyncCallback {
        void onComplete(boolean success, String errorMessage);
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
        logFile = resolveLogFile(context);

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
        writeAsync(line, false);
    }

    public static String formatMs(long nanos) {
        return String.format(Locale.US, "%.3f", nanos / 1_000_000.0);
    }

    public static String getLogPath() {
        File file = logFile;
        return file == null ? "" : file.getAbsolutePath();
    }

    public static boolean hasLog(Context context) {
        if (context == null) {
            return false;
        }
        File file = resolveLogFile(context);
        return file.isFile() && file.length() > 0L;
    }

    public static void syncToUri(Context context, Uri destination, SyncCallback callback) {
        if (context == null || destination == null) {
            dispatchSyncResult(callback, false, "同期先がありません");
            return;
        }

        ensureThread();
        Handler handler = logHandler;
        if (handler == null) {
            dispatchSyncResult(callback, false, "ログ処理を開始できません");
            return;
        }

        handler.post(() -> {
            File file = resolveLogFile(context);
            if (!file.isFile() || file.length() <= 0L) {
                dispatchSyncResult(callback, false, "同期するログがありません");
                return;
            }

            try (FileInputStream input = new FileInputStream(file);
                 OutputStream output = context.getContentResolver().openOutputStream(destination, "wt")) {
                if (output == null) {
                    dispatchSyncResult(callback, false, "同期先を開けません");
                    return;
                }

                byte[] buffer = new byte[8192];
                int read;
                while ((read = input.read(buffer)) >= 0) {
                    if (read > 0) {
                        output.write(buffer, 0, read);
                    }
                }
                output.flush();
                Log.i(TAG, "Performance log synced to selected document");
                dispatchSyncResult(callback, true, "");
            } catch (IOException error) {
                Log.e(TAG, "Failed to sync performance log", error);
                dispatchSyncResult(callback, false, error.getClass().getSimpleName());
            }
        });
    }

    private static File resolveLogFile(Context context) {
        File file = logFile;
        if (file != null) {
            return file;
        }

        File root = context.getExternalFilesDir(null);
        if (root == null) {
            root = context.getFilesDir();
        }
        file = new File(root, FILE_NAME);
        logFile = file;
        return file;
    }

    private static void dispatchSyncResult(
            SyncCallback callback,
            boolean success,
            String errorMessage
    ) {
        if (callback == null) {
            return;
        }
        MAIN_HANDLER.post(() -> callback.onComplete(success, errorMessage));
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
