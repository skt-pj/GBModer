package com.sktpj.gbmoder;

import android.accessibilityservice.AccessibilityService;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorSpace;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.hardware.HardwareBuffer;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;

import java.util.List;

public class FilterAccessibilityService extends AccessibilityService {
    private static final String TAG = "GBModerAccessibility";
    private static final String SYSTEM_UI_PACKAGE = "com.android.systemui";
    private static final String CHANNEL_ID = "gbmoder_filter";
    private static final int NOTIFICATION_ID = 4101;
    private static final long WINDOW_CAPTURE_INTERVAL_MS = 350L;

    private static final int PROBE_TOP_LEFT = Color.rgb(255, 0, 255);
    private static final int PROBE_TOP_RIGHT = Color.rgb(0, 255, 255);
    private static final int PROBE_BOTTOM_LEFT = Color.rgb(255, 255, 0);
    private static final int PROBE_BOTTOM_RIGHT = Color.rgb(0, 255, 0);
    private static final int PROBE_TOLERANCE = 18;

    private static volatile FilterAccessibilityService instance;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final Runnable captureRunnable = this::captureActiveWindow;

    private WindowManager windowManager;
    private FilterOverlayView overlayView;
    private WindowManager.LayoutParams overlayParams;
    private final Rect overlayBounds = new Rect();
    private boolean captureVisible = true;
    private boolean systemUiForeground = false;

    private HandlerThread filterThread;
    private Handler filterHandler;
    private boolean windowFilterRunning = false;
    private boolean screenshotInFlight = false;
    private String windowFilterMode = GameBoyFilter.MODE_GB;
    private int windowFilterBrightness = 6;
    private int windowFilterContrast = 122;
    private boolean windowFilterDither = true;

    public static FilterAccessibilityService getInstance() {
        return instance;
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        createNotificationChannel();
        Log.i(TAG, "Accessibility overlay service connected");
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        updateSystemUiVisibility();
        if (overlayView != null && !windowFilterRunning) {
            updateOverlayBoundsIfNeeded();
        }
    }

    @Override
    public void onInterrupt() {
    }

    public void startWindowFilter(String mode, int brightness, int contrast, boolean dither) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            Log.w(TAG, "Window screenshot filter requires Android 14+");
            return;
        }

        windowFilterMode = safeMode(mode);
        windowFilterBrightness = brightness;
        windowFilterContrast = contrast;
        windowFilterDither = dither;
        windowFilterRunning = true;
        screenshotInFlight = false;
        captureVisible = true;

        ensureFilterThread();
        showFilterNotification();
        mainHandler.removeCallbacks(captureRunnable);
        mainHandler.post(captureRunnable);

        Log.i(TAG, "Window filter started mode=" + windowFilterMode
                + " brightness=" + windowFilterBrightness
                + " contrast=" + windowFilterContrast
                + " dither=" + windowFilterDither
                + " source=takeScreenshotOfWindow");
    }

    public void stopWindowFilter() {
        windowFilterRunning = false;
        screenshotInFlight = false;
        mainHandler.removeCallbacks(captureRunnable);
        removeOverlayInternal();
        cancelFilterNotification();
        Log.i(TAG, "Window filter stopped");
    }

    public boolean isWindowFilterRunning() {
        return windowFilterRunning;
    }

    private void captureActiveWindow() {
        if (!windowFilterRunning || Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            return;
        }
        if (screenshotInFlight) {
            scheduleNextWindowCapture(WINDOW_CAPTURE_INTERVAL_MS);
            return;
        }

        updateSystemUiVisibility();
        if (systemUiForeground) {
            setCaptureVisible(false);
            scheduleNextWindowCapture(WINDOW_CAPTURE_INTERVAL_MS);
            return;
        }

        TargetWindow target = resolveActiveApplicationWindow();
        if (target == null) {
            setCaptureVisible(false);
            scheduleNextWindowCapture(WINDOW_CAPTURE_INTERVAL_MS);
            return;
        }

        screenshotInFlight = true;
        long requestStartedAt = System.currentTimeMillis();
        Log.d(TAG, "Window screenshot requested id=" + target.windowId
                + " package=" + target.packageName
                + " bounds=" + target.bounds);

        takeScreenshotOfWindow(
                target.windowId,
                getMainExecutor(),
                new TakeScreenshotCallback() {
                    @Override
                    public void onSuccess(ScreenshotResult screenshot) {
                        screenshotInFlight = false;
                        Bitmap softwareBitmap = copyScreenshotToSoftwareBitmap(screenshot);
                        if (softwareBitmap == null) {
                            Log.e(TAG, "Window screenshot returned no bitmap package=" + target.packageName);
                            scheduleNextWindowCapture(WINDOW_CAPTURE_INTERVAL_MS);
                            return;
                        }

                        ensureFilterThread();
                        Handler handler = filterHandler;
                        if (handler == null) {
                            softwareBitmap.recycle();
                            scheduleNextWindowCapture(WINDOW_CAPTURE_INTERVAL_MS);
                            return;
                        }

                        handler.post(() -> processWindowScreenshot(
                                softwareBitmap,
                                target,
                                requestStartedAt
                        ));
                    }

                    @Override
                    public void onFailure(int errorCode) {
                        screenshotInFlight = false;
                        Log.w(TAG, "Window screenshot failed code=" + errorCode
                                + " package=" + target.packageName);
                        setCaptureVisible(false);
                        long retryDelay = errorCode == ERROR_TAKE_SCREENSHOT_INTERVAL_TIME_SHORT
                                ? 120L
                                : WINDOW_CAPTURE_INTERVAL_MS;
                        scheduleNextWindowCapture(retryDelay);
                    }
                }
        );
    }

    private Bitmap copyScreenshotToSoftwareBitmap(ScreenshotResult screenshot) {
        if (screenshot == null) {
            return null;
        }

        HardwareBuffer hardwareBuffer = screenshot.getHardwareBuffer();
        if (hardwareBuffer == null) {
            return null;
        }

        try {
            ColorSpace colorSpace = screenshot.getColorSpace();
            if (colorSpace == null) {
                colorSpace = ColorSpace.get(ColorSpace.Named.SRGB);
            }
            Bitmap hardwareBitmap = Bitmap.wrapHardwareBuffer(hardwareBuffer, colorSpace);
            if (hardwareBitmap == null) {
                return null;
            }
            return hardwareBitmap.copy(Bitmap.Config.ARGB_8888, false);
        } finally {
            hardwareBuffer.close();
        }
    }

    private void processWindowScreenshot(Bitmap source, TargetWindow target, long requestStartedAt) {
        Bitmap lowResolutionBitmap = null;
        try {
            int targetWidth = GameBoyFilter.getBaseWidth(windowFilterMode);
            int targetHeight = GameBoyFilter.getBaseHeight(
                    windowFilterMode,
                    source.getWidth(),
                    source.getHeight()
            );

            lowResolutionBitmap = Bitmap.createBitmap(
                    targetWidth,
                    targetHeight,
                    Bitmap.Config.ARGB_8888
            );

            Canvas canvas = new Canvas(lowResolutionBitmap);
            Paint downsamplePaint = new Paint();
            downsamplePaint.setFilterBitmap(false);
            downsamplePaint.setAntiAlias(false);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    source,
                    new Rect(0, 0, source.getWidth(), source.getHeight()),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );

            GameBoyFilter.apply(
                    lowResolutionBitmap,
                    windowFilterMode,
                    windowFilterBrightness,
                    windowFilterContrast,
                    windowFilterDither
            );

            Bitmap frame = lowResolutionBitmap;
            lowResolutionBitmap = null;
            mainHandler.post(() -> {
                if (!windowFilterRunning) {
                    frame.recycle();
                    return;
                }
                showFrame(frame, target.bounds);
                long elapsed = System.currentTimeMillis() - requestStartedAt;
                long delay = Math.max(0L, WINDOW_CAPTURE_INTERVAL_MS - elapsed);
                scheduleNextWindowCapture(delay);
            });
        } catch (Throwable error) {
            Log.e(TAG, "Window frame processing failed", error);
            scheduleNextWindowCapture(WINDOW_CAPTURE_INTERVAL_MS);
        } finally {
            source.recycle();
            if (lowResolutionBitmap != null && !lowResolutionBitmap.isRecycled()) {
                lowResolutionBitmap.recycle();
            }
        }
    }

    private void scheduleNextWindowCapture(long delayMs) {
        if (!windowFilterRunning) {
            return;
        }
        mainHandler.removeCallbacks(captureRunnable);
        mainHandler.postDelayed(captureRunnable, Math.max(0L, delayMs));
    }

    private void ensureFilterThread() {
        if (filterThread != null && filterThread.isAlive() && filterHandler != null) {
            return;
        }
        filterThread = new HandlerThread("GBModerWindowFilterThread");
        filterThread.start();
        filterHandler = new Handler(filterThread.getLooper());
    }

    private TargetWindow resolveActiveApplicationWindow() {
        List<AccessibilityWindowInfo> windows = getWindows();
        if (windows == null) {
            return null;
        }

        TargetWindow fallback = null;
        for (AccessibilityWindowInfo window : windows) {
            if (window == null || window.getType() != AccessibilityWindowInfo.TYPE_APPLICATION) {
                continue;
            }

            AccessibilityNodeInfo root = null;
            try {
                root = window.getRoot();
                CharSequence packageNameSequence = root == null ? null : root.getPackageName();
                String packageName = packageNameSequence == null
                        ? null
                        : packageNameSequence.toString();

                if (getPackageName().equals(packageName) || SYSTEM_UI_PACKAGE.equals(packageName)) {
                    continue;
                }

                Rect bounds = new Rect();
                window.getBoundsInScreen(bounds);
                if (bounds.isEmpty()) {
                    continue;
                }

                TargetWindow candidate = new TargetWindow(
                        window.getId(),
                        bounds,
                        packageName == null ? "unknown" : packageName
                );

                if (window.isActive() || window.isFocused()) {
                    return candidate;
                }
                if (fallback == null) {
                    fallback = candidate;
                }
            } finally {
                if (root != null) {
                    root.recycle();
                }
            }
        }
        return fallback;
    }

    public void prepareProbe() {
        runOnMain(() -> {
            ensureOverlay();
            updateOverlayBoundsIfNeeded();
            captureVisible = true;
            overlayView.showProbe();
            updateOverlayVisibility();
            Log.i(TAG, "Projection probe overlay prepared bounds=" + overlayBounds);
        });
    }

    public void showFrame(Bitmap frame) {
        runOnMain(() -> {
            ensureOverlay();
            updateOverlayBoundsIfNeeded();
            overlayView.setFrame(frame);
            updateOverlayVisibility();
        });
    }

    private void showFrame(Bitmap frame, Rect bounds) {
        runOnMain(() -> {
            ensureOverlay();
            applyBoundsAndUpdateIfNeeded(bounds);
            captureVisible = true;
            overlayView.setFrame(frame);
            updateSystemUiVisibility();
            updateOverlayVisibility();
        });
    }

    public void setCaptureVisible(boolean visible) {
        runOnMain(() -> {
            captureVisible = visible;
            updateOverlayVisibility();
        });
    }

    public void clearOverlay() {
        runOnMain(this::removeOverlayInternal);
    }

    public boolean isProbeFrame(Bitmap capturedBitmap, int contentWidth, int contentHeight) {
        if (capturedBitmap == null || capturedBitmap.isRecycled()) {
            return false;
        }

        Rect bounds;
        synchronized (this) {
            bounds = new Rect(overlayBounds);
        }
        if (bounds.isEmpty()) {
            return false;
        }

        Rect displayBounds;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            displayBounds = windowManager.getMaximumWindowMetrics().getBounds();
        } else {
            displayBounds = new Rect(0, 0, contentWidth, contentHeight);
        }

        int displayWidth = Math.max(1, displayBounds.width());
        int displayHeight = Math.max(1, displayBounds.height());
        float scaleX = contentWidth / (float) displayWidth;
        float scaleY = contentHeight / (float) displayHeight;

        int left = clamp(Math.round((bounds.left - displayBounds.left) * scaleX), 0, contentWidth - 1);
        int top = clamp(Math.round((bounds.top - displayBounds.top) * scaleY), 0, contentHeight - 1);
        int right = clamp(Math.round((bounds.right - displayBounds.left) * scaleX), left + 1, contentWidth);
        int bottom = clamp(Math.round((bounds.bottom - displayBounds.top) * scaleY), top + 1, contentHeight);

        int quarterX1 = left + Math.max(1, (right - left) / 4);
        int quarterX3 = left + Math.max(1, ((right - left) * 3) / 4);
        int quarterY1 = top + Math.max(1, (bottom - top) / 4);
        int quarterY3 = top + Math.max(1, ((bottom - top) * 3) / 4);

        return matches(capturedBitmap.getPixel(quarterX1, quarterY1), PROBE_TOP_LEFT)
                && matches(capturedBitmap.getPixel(quarterX3, quarterY1), PROBE_TOP_RIGHT)
                && matches(capturedBitmap.getPixel(quarterX1, quarterY3), PROBE_BOTTOM_LEFT)
                && matches(capturedBitmap.getPixel(quarterX3, quarterY3), PROBE_BOTTOM_RIGHT);
    }

    private void ensureOverlay() {
        if (overlayView != null) {
            return;
        }

        if (windowManager == null) {
            windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        }

        overlayView = new FilterOverlayView(this);
        overlayParams = new WindowManager.LayoutParams(
                1,
                1,
                WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                        | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                PixelFormat.OPAQUE
        );
        overlayParams.gravity = Gravity.TOP | Gravity.START;
        overlayParams.alpha = 1.0f;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            overlayParams.layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }

        Rect initialBounds = resolveActiveApplicationBounds();
        applyBounds(initialBounds);
        windowManager.addView(overlayView, overlayParams);
        updateSystemUiVisibility();
        updateOverlayVisibility();
        Log.i(TAG, "Opaque accessibility overlay added alpha=1.0 bounds=" + overlayBounds);
    }

    private void updateOverlayBoundsIfNeeded() {
        if (overlayView == null || overlayParams == null || windowManager == null) {
            return;
        }
        applyBoundsAndUpdateIfNeeded(resolveActiveApplicationBounds());
    }

    private void applyBoundsAndUpdateIfNeeded(Rect newBounds) {
        if (overlayView == null || overlayParams == null || windowManager == null) {
            return;
        }

        Rect safeBounds = sanitizeBounds(newBounds);
        synchronized (this) {
            if (overlayBounds.equals(safeBounds)) {
                return;
            }
        }

        applyBounds(safeBounds);
        try {
            windowManager.updateViewLayout(overlayView, overlayParams);
            Log.i(TAG, "Overlay bounds updated=" + safeBounds);
        } catch (Throwable error) {
            Log.e(TAG, "Failed to update overlay bounds", error);
        }
    }

    private void applyBounds(Rect bounds) {
        Rect safeBounds = sanitizeBounds(bounds);
        synchronized (this) {
            overlayBounds.set(safeBounds);
        }
        overlayParams.width = Math.max(1, safeBounds.width());
        overlayParams.height = Math.max(1, safeBounds.height());
        overlayParams.x = safeBounds.left;
        overlayParams.y = safeBounds.top;
    }

    private Rect sanitizeBounds(Rect bounds) {
        Rect safeBounds = bounds == null ? new Rect() : new Rect(bounds);
        if (safeBounds.isEmpty()) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                safeBounds = windowManager.getMaximumWindowMetrics().getBounds();
            } else {
                safeBounds = new Rect(
                        0,
                        0,
                        getResources().getDisplayMetrics().widthPixels,
                        getResources().getDisplayMetrics().heightPixels
                );
            }
        }
        return safeBounds;
    }

    private Rect resolveActiveApplicationBounds() {
        TargetWindow target = resolveActiveApplicationWindow();
        if (target != null) {
            return new Rect(target.bounds);
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            return new Rect(windowManager.getMaximumWindowMetrics().getBounds());
        }
        return new Rect(
                0,
                0,
                getResources().getDisplayMetrics().widthPixels,
                getResources().getDisplayMetrics().heightPixels
        );
    }

    private void updateSystemUiVisibility() {
        boolean foundSystemUiForeground = false;
        List<AccessibilityWindowInfo> windows = getWindows();
        if (windows != null) {
            for (AccessibilityWindowInfo window : windows) {
                if (window == null || (!window.isActive() && !window.isFocused())) {
                    continue;
                }
                AccessibilityNodeInfo root = null;
                try {
                    root = window.getRoot();
                    CharSequence packageName = root == null ? null : root.getPackageName();
                    if (packageName != null && SYSTEM_UI_PACKAGE.contentEquals(packageName)) {
                        foundSystemUiForeground = true;
                        break;
                    }
                } finally {
                    if (root != null) {
                        root.recycle();
                    }
                }
            }
        }
        systemUiForeground = foundSystemUiForeground;
        updateOverlayVisibility();
    }

    private void updateOverlayVisibility() {
        if (overlayView == null) {
            return;
        }
        overlayView.setVisibility(captureVisible && !systemUiForeground ? View.VISIBLE : View.INVISIBLE);
    }

    private void removeOverlayInternal() {
        if (overlayView == null) {
            return;
        }
        try {
            windowManager.removeView(overlayView);
        } catch (Throwable error) {
            Log.w(TAG, "Overlay remove failed", error);
        }
        overlayView.release();
        overlayView = null;
        overlayParams = null;
        synchronized (this) {
            overlayBounds.setEmpty();
        }
        Log.i(TAG, "Accessibility overlay removed");
    }

    private void createNotificationChannel() {
        NotificationManager manager = getSystemService(NotificationManager.class);
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "GBModer filter",
                NotificationManager.IMPORTANCE_LOW
        );
        channel.setDescription("GBModer screen filter controls");
        manager.createNotificationChannel(channel);
    }

    private void showFilterNotification() {
        Intent openApp = new Intent(this, MainActivity.class);
        PendingIntent contentIntent = PendingIntent.getActivity(
                this,
                0,
                openApp,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Intent stopIntent = new Intent(this, FilterControlReceiver.class);
        stopIntent.setAction(FilterControlReceiver.ACTION_STOP);
        PendingIntent stopPendingIntent = PendingIntent.getBroadcast(
                this,
                1,
                stopIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Notification notification = new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("GBModer")
                .setContentText("他アプリの画面をGame Boy風に変換中")
                .setSmallIcon(android.R.drawable.ic_menu_view)
                .setContentIntent(contentIntent)
                .setOngoing(true)
                .addAction(
                        android.R.drawable.ic_menu_close_clear_cancel,
                        "解除",
                        stopPendingIntent
                )
                .build();

        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.notify(NOTIFICATION_ID, notification);
    }

    private void cancelFilterNotification() {
        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.cancel(NOTIFICATION_ID);
    }

    private void runOnMain(Runnable action) {
        if (getMainLooper().isCurrentThread()) {
            action.run();
        } else {
            getMainExecutor().execute(action);
        }
    }

    private String safeMode(String requestedMode) {
        if (GameBoyFilter.MODE_GBC.equals(requestedMode)) {
            return GameBoyFilter.MODE_GBC;
        }
        if (GameBoyFilter.MODE_GBA.equals(requestedMode)) {
            return GameBoyFilter.MODE_GBA;
        }
        if (GameBoyFilter.MODE_DS.equals(requestedMode)) {
            return GameBoyFilter.MODE_DS;
        }
        return GameBoyFilter.MODE_GB;
    }

    private static boolean matches(int actual, int expected) {
        return Math.abs(Color.red(actual) - Color.red(expected)) <= PROBE_TOLERANCE
                && Math.abs(Color.green(actual) - Color.green(expected)) <= PROBE_TOLERANCE
                && Math.abs(Color.blue(actual) - Color.blue(expected)) <= PROBE_TOLERANCE;
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    @Override
    public void onDestroy() {
        windowFilterRunning = false;
        screenshotInFlight = false;
        mainHandler.removeCallbacks(captureRunnable);
        cancelFilterNotification();
        removeOverlayInternal();
        if (filterThread != null) {
            filterThread.quitSafely();
            filterThread = null;
            filterHandler = null;
        }
        if (instance == this) {
            instance = null;
        }
        Log.i(TAG, "Accessibility overlay service destroyed");
        super.onDestroy();
    }

    private static final class TargetWindow {
        final int windowId;
        final Rect bounds;
        final String packageName;

        TargetWindow(int windowId, Rect bounds, String packageName) {
            this.windowId = windowId;
            this.bounds = new Rect(bounds);
            this.packageName = packageName;
        }
    }

    private static final class FilterOverlayView extends View {
        private final Paint paint = new Paint();
        private Bitmap frame;
        private boolean probeMode = false;

        FilterOverlayView(FilterAccessibilityService context) {
            super(context);
            paint.setFilterBitmap(false);
            paint.setAntiAlias(false);
            setBackgroundColor(Color.BLACK);
        }

        void showProbe() {
            probeMode = true;
            Bitmap oldFrame = frame;
            frame = null;
            if (oldFrame != null && !oldFrame.isRecycled()) {
                oldFrame.recycle();
            }
            invalidate();
        }

        void setFrame(Bitmap newFrame) {
            probeMode = false;
            Bitmap oldFrame = frame;
            frame = newFrame;
            if (oldFrame != null && oldFrame != newFrame && !oldFrame.isRecycled()) {
                oldFrame.recycle();
            }
            invalidate();
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            if (probeMode) {
                int halfWidth = getWidth() / 2;
                int halfHeight = getHeight() / 2;
                paint.setColor(PROBE_TOP_LEFT);
                canvas.drawRect(0, 0, halfWidth, halfHeight, paint);
                paint.setColor(PROBE_TOP_RIGHT);
                canvas.drawRect(halfWidth, 0, getWidth(), halfHeight, paint);
                paint.setColor(PROBE_BOTTOM_LEFT);
                canvas.drawRect(0, halfHeight, halfWidth, getHeight(), paint);
                paint.setColor(PROBE_BOTTOM_RIGHT);
                canvas.drawRect(halfWidth, halfHeight, getWidth(), getHeight(), paint);
                return;
            }

            Bitmap current = frame;
            if (current == null || current.isRecycled()) {
                return;
            }
            canvas.drawBitmap(
                    current,
                    null,
                    new Rect(0, 0, getWidth(), getHeight()),
                    paint
            );
        }

        void release() {
            Bitmap current = frame;
            frame = null;
            if (current != null && !current.isRecycled()) {
                current.recycle();
            }
        }
    }
}
