package com.sktpj.gbmoder;

import android.accessibilityservice.AccessibilityService;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.os.Build;
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

    private static final int PROBE_TOP_LEFT = Color.rgb(255, 0, 255);
    private static final int PROBE_TOP_RIGHT = Color.rgb(0, 255, 255);
    private static final int PROBE_BOTTOM_LEFT = Color.rgb(255, 255, 0);
    private static final int PROBE_BOTTOM_RIGHT = Color.rgb(0, 255, 0);
    private static final int PROBE_TOLERANCE = 18;

    private static volatile FilterAccessibilityService instance;

    private WindowManager windowManager;
    private FilterOverlayView overlayView;
    private WindowManager.LayoutParams overlayParams;
    private Rect overlayBounds = new Rect();
    private boolean captureVisible = true;
    private boolean systemUiForeground = false;

    public static FilterAccessibilityService getInstance() {
        return instance;
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        Log.i(TAG, "Accessibility overlay service connected");
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (overlayView == null) {
            return;
        }
        updateSystemUiVisibility();
        updateOverlayBoundsIfNeeded();
    }

    @Override
    public void onInterrupt() {
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
        Log.i(TAG, "Opaque trusted overlay added alpha=1.0 bounds=" + overlayBounds);
    }

    private void updateOverlayBoundsIfNeeded() {
        if (overlayView == null || overlayParams == null || windowManager == null) {
            return;
        }

        Rect newBounds = resolveActiveApplicationBounds();
        synchronized (this) {
            if (overlayBounds.equals(newBounds)) {
                return;
            }
        }

        applyBounds(newBounds);
        try {
            windowManager.updateViewLayout(overlayView, overlayParams);
            Log.i(TAG, "Overlay bounds updated=" + newBounds);
        } catch (Throwable error) {
            Log.e(TAG, "Failed to update overlay bounds", error);
        }
    }

    private void applyBounds(Rect bounds) {
        Rect safeBounds = new Rect(bounds);
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

        synchronized (this) {
            overlayBounds.set(safeBounds);
        }
        overlayParams.width = Math.max(1, safeBounds.width());
        overlayParams.height = Math.max(1, safeBounds.height());
        overlayParams.x = safeBounds.left;
        overlayParams.y = safeBounds.top;
    }

    private Rect resolveActiveApplicationBounds() {
        List<AccessibilityWindowInfo> windows = getWindows();
        if (windows != null) {
            for (AccessibilityWindowInfo window : windows) {
                if (window == null || window.getType() != AccessibilityWindowInfo.TYPE_APPLICATION) {
                    continue;
                }
                if (!window.isActive() && !window.isFocused()) {
                    continue;
                }

                AccessibilityNodeInfo root = null;
                try {
                    root = window.getRoot();
                    CharSequence packageName = root == null ? null : root.getPackageName();
                    if (packageName != null
                            && (getPackageName().contentEquals(packageName)
                            || SYSTEM_UI_PACKAGE.contentEquals(packageName))) {
                        continue;
                    }

                    Rect bounds = new Rect();
                    window.getBoundsInScreen(bounds);
                    if (!bounds.isEmpty()) {
                        return bounds;
                    }
                } finally {
                    if (root != null) {
                        root.recycle();
                    }
                }
            }
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

    private void runOnMain(Runnable action) {
        if (getMainLooper().isCurrentThread()) {
            action.run();
        } else {
            getMainExecutor().execute(action);
        }
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
        removeOverlayInternal();
        if (instance == this) {
            instance = null;
        }
        Log.i(TAG, "Accessibility overlay service destroyed");
        super.onDestroy();
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
