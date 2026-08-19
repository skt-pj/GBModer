package com.sktpj.gbmoder;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.WindowManager;
import android.widget.Toast;

import java.nio.ByteBuffer;

public class FilterCaptureService extends Service {
    public static final String ACTION_START = "com.sktpj.gbmoder.action.START";
    public static final String ACTION_STOP = "com.sktpj.gbmoder.action.STOP";
    public static final String EXTRA_RESULT_CODE = "result_code";
    public static final String EXTRA_RESULT_DATA = "result_data";
    public static final String EXTRA_MODE = "mode";
    public static final String EXTRA_RESOLUTION = "resolution";
    public static final String EXTRA_BRIGHTNESS = "brightness";
    public static final String EXTRA_CONTRAST = "contrast";
    public static final String EXTRA_DITHER = "dither";

    private static final String TAG = "GBModerCapture";
    private static final String CHANNEL_ID = "gbmoder_filter";
    private static final int NOTIFICATION_ID = 4101;
    private static final long MIN_FRAME_INTERVAL_NS = 80_000_000L;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private MediaProjection mediaProjection;
    private VirtualDisplay virtualDisplay;
    private ImageReader imageReader;
    private HandlerThread captureThread;
    private Handler captureHandler;
    private Bitmap captureBitmap;
    private Bitmap lowResolutionBitmap;
    private int captureWidth;
    private int captureHeight;
    private int densityDpi;
    private String mode = GameBoyFilter.MODE_GB;
    private String resolution = GameBoyFilter.RESOLUTION_GB;
    private int brightness = 6;
    private int contrast = 122;
    private boolean dither = true;
    private long lastFrameNanos = 0L;
    private long performanceFrameIndex = 0L;
    private boolean cleanedUp = false;
    private boolean projectionProbePending = true;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) {
            stopSelf();
            return START_NOT_STICKY;
        }

        if (ACTION_STOP.equals(intent.getAction())) {
            Log.i(TAG, "Stop requested from app/notification");
            cleanupAndStop();
            return START_NOT_STICKY;
        }

        if (!ACTION_START.equals(intent.getAction())) {
            stopSelf();
            return START_NOT_STICKY;
        }

        FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
        if (accessibilityService == null) {
            Log.e(TAG, "Accessibility overlay service is not connected");
            Toast.makeText(this, "GBModerのユーザー補助サービスを有効にしてください", Toast.LENGTH_LONG).show();
            stopSelf();
            return START_NOT_STICKY;
        }

        cleanedUp = false;
        projectionProbePending = true;
        lastFrameNanos = 0L;
        performanceFrameIndex = 0L;
        mode = safeMode(intent.getStringExtra(EXTRA_MODE));
        resolution = GameBoyFilter.safeResolution(intent.getStringExtra(EXTRA_RESOLUTION));
        brightness = intent.getIntExtra(EXTRA_BRIGHTNESS, 6);
        contrast = intent.getIntExtra(EXTRA_CONTRAST, 122);
        dither = intent.getBooleanExtra(EXTRA_DITHER, true);

        PerformanceLog.startSession(
                this,
                "media_projection",
                mode,
                resolution,
                brightness,
                contrast,
                dither,
                MIN_FRAME_INTERVAL_NS / 1_000_000L
        );

        startProjectionForeground();

        int resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0);
        Intent resultData;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            resultData = intent.getParcelableExtra(EXTRA_RESULT_DATA, Intent.class);
        } else {
            //noinspection deprecation
            resultData = intent.getParcelableExtra(EXTRA_RESULT_DATA);
        }

        if (resultData == null) {
            Log.e(TAG, "MediaProjection result data is missing");
            cleanupAndStop();
            return START_NOT_STICKY;
        }

        try {
            startCapture(resultCode, resultData);
        } catch (Throwable error) {
            Log.e(TAG, "Failed to start capture", error);
            cleanupAndStop();
        }

        return START_NOT_STICKY;
    }

    private void startProjectionForeground() {
        Intent openApp = new Intent(this, MainActivity.class);
        PendingIntent contentIntent = PendingIntent.getActivity(
                this,
                0,
                openApp,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Intent stopIntent = new Intent(this, FilterCaptureService.class);
        stopIntent.setAction(ACTION_STOP);
        PendingIntent stopPendingIntent = PendingIntent.getService(
                this,
                1,
                stopIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Notification.Builder builder = new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("GBModer")
                .setContentText("他アプリの画面をGame Boy風に変換中")
                .setSmallIcon(android.R.drawable.ic_menu_view)
                .setContentIntent(contentIntent)
                .setOngoing(true)
                .addAction(
                        android.R.drawable.ic_menu_close_clear_cancel,
                        "解除",
                        stopPendingIntent
                );

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            builder.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE);
        }

        Notification notification = builder.build();

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                    NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            );
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
    }

    private void startCapture(int resultCode, Intent resultData) {
        resolveCaptureSize();

        FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
        if (accessibilityService == null) {
            throw new IllegalStateException("Accessibility overlay service disconnected");
        }
        accessibilityService.prepareProbe();

        captureThread = new HandlerThread("GBModerCaptureThread");
        captureThread.start();
        captureHandler = new Handler(captureThread.getLooper());

        imageReader = createImageReader(captureWidth, captureHeight);

        MediaProjectionManager manager =
                (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        mediaProjection = manager.getMediaProjection(resultCode, resultData);
        mediaProjection.registerCallback(new MediaProjection.Callback() {
            @Override
            public void onStop() {
                Log.i(TAG, "MediaProjection stopped by system/user");
                mainHandler.post(FilterCaptureService.this::cleanupAndStop);
            }

            @Override
            public void onCapturedContentResize(int width, int height) {
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                    return;
                }
                if (width <= 0 || height <= 0) {
                    return;
                }
                Log.i(TAG, "Captured content resized: " + width + "x" + height);
                Handler handler = captureHandler;
                if (handler != null) {
                    handler.post(() -> resizeCaptureSurface(width, height));
                }
            }

            @Override
            public void onCapturedContentVisibilityChanged(boolean isVisible) {
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                    return;
                }
                Log.i(TAG, "Captured content visibility=" + isVisible);
                FilterAccessibilityService service = FilterAccessibilityService.getInstance();
                if (service != null) {
                    service.setCaptureVisible(isVisible);
                }
            }
        }, mainHandler);

        virtualDisplay = mediaProjection.createVirtualDisplay(
                "GBModerCapture",
                captureWidth,
                captureHeight,
                densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader.getSurface(),
                null,
                captureHandler
        );

        Log.i(TAG, "Capture started: " + captureWidth + "x" + captureHeight
                + " mode=" + mode
                + " resolution=" + resolution
                + " brightness=" + brightness
                + " contrast=" + contrast
                + " dither=" + dither
                + " probe=true");
    }

    private ImageReader createImageReader(int width, int height) {
        ImageReader reader = ImageReader.newInstance(
                Math.max(1, width),
                Math.max(1, height),
                PixelFormat.RGBA_8888,
                2
        );
        reader.setOnImageAvailableListener(this::onImageAvailable, captureHandler);
        return reader;
    }

    private void resizeCaptureSurface(int width, int height) {
        if (cleanedUp || virtualDisplay == null || imageReader == null) {
            return;
        }
        if (captureWidth == width && captureHeight == height) {
            return;
        }

        ImageReader previousReader = imageReader;
        ImageReader replacementReader = createImageReader(width, height);

        try {
            virtualDisplay.resize(width, height, densityDpi);
            virtualDisplay.setSurface(replacementReader.getSurface());
            imageReader = replacementReader;
            captureWidth = width;
            captureHeight = height;

            previousReader.setOnImageAvailableListener(null, null);
            previousReader.close();

            recycleBitmap(captureBitmap);
            captureBitmap = null;
            recycleBitmap(lowResolutionBitmap);
            lowResolutionBitmap = null;

            Log.i(TAG, "Capture surface resized to selected app: " + width + "x" + height);
        } catch (Throwable error) {
            replacementReader.setOnImageAvailableListener(null, null);
            replacementReader.close();
            Log.e(TAG, "Capture surface resize failed", error);
        }
    }

    private void resolveCaptureSize() {
        WindowManager windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
        densityDpi = getResources().getConfiguration().densityDpi;

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Rect bounds = windowManager.getMaximumWindowMetrics().getBounds();
            captureWidth = Math.max(1, bounds.width());
            captureHeight = Math.max(1, bounds.height());
        } else {
            DisplayMetrics metrics = new DisplayMetrics();
            //noinspection deprecation
            windowManager.getDefaultDisplay().getRealMetrics(metrics);
            captureWidth = Math.max(1, metrics.widthPixels);
            captureHeight = Math.max(1, metrics.heightPixels);
            densityDpi = metrics.densityDpi;
        }
    }

    private void onImageAvailable(ImageReader reader) {
        Image image = null;
        try {
            image = reader.acquireLatestImage();
            if (image == null) {
                return;
            }

            long frameStartedNs = SystemClock.elapsedRealtimeNanos();
            long frameIntervalNs = lastFrameNanos == 0L ? 0L : frameStartedNs - lastFrameNanos;
            if (!projectionProbePending
                    && lastFrameNanos != 0L
                    && frameIntervalNs < MIN_FRAME_INTERVAL_NS) {
                return;
            }
            lastFrameNanos = frameStartedNs;

            Image.Plane plane = image.getPlanes()[0];
            ByteBuffer buffer = plane.getBuffer();
            int pixelStride = plane.getPixelStride();
            int rowStride = plane.getRowStride();
            int rowPadding = rowStride - (pixelStride * image.getWidth());
            int paddedWidth = image.getWidth()
                    + Math.max(0, rowPadding / Math.max(1, pixelStride));

            if (captureBitmap == null
                    || captureBitmap.getWidth() != paddedWidth
                    || captureBitmap.getHeight() != image.getHeight()) {
                recycleBitmap(captureBitmap);
                captureBitmap = Bitmap.createBitmap(
                        paddedWidth,
                        image.getHeight(),
                        Bitmap.Config.ARGB_8888
                );
            }

            long bufferCopyStartedNs = SystemClock.elapsedRealtimeNanos();
            buffer.rewind();
            captureBitmap.copyPixelsFromBuffer(buffer);
            long bufferCopyFinishedNs = SystemClock.elapsedRealtimeNanos();

            if (projectionProbePending) {
                FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
                boolean probeCaptured = accessibilityService != null
                        && accessibilityService.isProbeFrame(
                        captureBitmap,
                        image.getWidth(),
                        image.getHeight()
                );
                projectionProbePending = false;
                Log.i(TAG, "Projection probe captured=" + probeCaptured
                        + " frame=" + image.getWidth() + "x" + image.getHeight());

                if (probeCaptured) {
                    mainHandler.post(() -> {
                        FilterAccessibilityService service = FilterAccessibilityService.getInstance();
                        if (service != null) {
                            service.clearOverlay();
                        }
                        Toast.makeText(
                                this,
                                "画面全体共有は使用できません。「1つのアプリ」を選択してください。",
                                Toast.LENGTH_LONG
                        ).show();
                        cleanupAndStop();
                    });
                    return;
                }
            }

            int sourceWidth = image.getWidth();
            int sourceHeight = image.getHeight();
            int targetWidth = GameBoyFilter.getTargetWidth(resolution, sourceWidth);
            int targetHeight = GameBoyFilter.getTargetHeight(resolution, sourceHeight);

            if (lowResolutionBitmap == null
                    || lowResolutionBitmap.getWidth() != targetWidth
                    || lowResolutionBitmap.getHeight() != targetHeight) {
                recycleBitmap(lowResolutionBitmap);
                lowResolutionBitmap = Bitmap.createBitmap(
                        targetWidth,
                        targetHeight,
                        Bitmap.Config.ARGB_8888
                );
            }

            long downsampleStartedNs = SystemClock.elapsedRealtimeNanos();
            Canvas canvas = new Canvas(lowResolutionBitmap);
            Paint downsamplePaint = new Paint();
            downsamplePaint.setFilterBitmap(false);
            downsamplePaint.setAntiAlias(false);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(
                    captureBitmap,
                    new Rect(0, 0, sourceWidth, sourceHeight),
                    new Rect(0, 0, targetWidth, targetHeight),
                    downsamplePaint
            );
            long downsampleFinishedNs = SystemClock.elapsedRealtimeNanos();

            long filterStartedNs = SystemClock.elapsedRealtimeNanos();
            GameBoyFilter.apply(
                    lowResolutionBitmap,
                    mode,
                    brightness,
                    contrast,
                    dither
            );
            long filterFinishedNs = SystemClock.elapsedRealtimeNanos();

            long frameCopyStartedNs = SystemClock.elapsedRealtimeNanos();
            Bitmap frameForOverlay = lowResolutionBitmap.copy(Bitmap.Config.ARGB_8888, false);
            long frameCopyFinishedNs = SystemClock.elapsedRealtimeNanos();
            long postedNs = SystemClock.elapsedRealtimeNanos();
            long frameIndex = ++performanceFrameIndex;
            long bufferCopyNs = bufferCopyFinishedNs - bufferCopyStartedNs;
            long downsampleNs = downsampleFinishedNs - downsampleStartedNs;
            long filterNs = filterFinishedNs - filterStartedNs;
            long frameCopyNs = frameCopyFinishedNs - frameCopyStartedNs;

            mainHandler.post(() -> {
                long mainStartedNs = SystemClock.elapsedRealtimeNanos();
                FilterAccessibilityService service = FilterAccessibilityService.getInstance();
                if (service != null) {
                    service.showFrame(frameForOverlay);
                    long overlayFinishedNs = SystemClock.elapsedRealtimeNanos();
                    long totalNs = overlayFinishedNs - frameStartedNs;
                    long mainQueueNs = mainStartedNs - postedNs;
                    long overlayNs = overlayFinishedNs - mainStartedNs;

                    PerformanceLog.log(
                            "frame=" + frameIndex
                                    + " pipeline=media_projection"
                                    + " mode=" + mode
                                    + " resolution=" + resolution
                                    + " source=" + sourceWidth + "x" + sourceHeight
                                    + " target=" + targetWidth + "x" + targetHeight
                                    + " frame_interval_ms=" + PerformanceLog.formatMs(frameIntervalNs)
                                    + " buffer_copy_ms=" + PerformanceLog.formatMs(bufferCopyNs)
                                    + " downsample_ms=" + PerformanceLog.formatMs(downsampleNs)
                                    + " filter_ms=" + PerformanceLog.formatMs(filterNs)
                                    + " frame_copy_ms=" + PerformanceLog.formatMs(frameCopyNs)
                                    + " main_queue_ms=" + PerformanceLog.formatMs(mainQueueNs)
                                    + " overlay_ms=" + PerformanceLog.formatMs(overlayNs)
                                    + " total_ms=" + PerformanceLog.formatMs(totalNs)
                    );
                } else {
                    frameForOverlay.recycle();
                    Log.e(TAG, "Accessibility service disconnected while rendering");
                    PerformanceLog.log("frame_failure pipeline=media_projection stage=overlay_service_disconnected");
                    cleanupAndStop();
                }
            });
        } catch (Throwable error) {
            Log.e(TAG, "Frame processing failed", error);
            PerformanceLog.log("frame_failure pipeline=media_projection stage=processing error="
                    + error.getClass().getSimpleName());
        } finally {
            if (image != null) {
                image.close();
            }
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

    private void createNotificationChannel() {
        NotificationManager manager = getSystemService(NotificationManager.class);
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "GBModer filter",
                NotificationManager.IMPORTANCE_LOW
        );
        channel.setDescription("MediaProjection screen filter");
        manager.createNotificationChannel(channel);
    }

    private void cleanupAndStop() {
        if (cleanedUp) {
            stopSelf();
            return;
        }
        cleanedUp = true;

        if (imageReader != null) {
            imageReader.setOnImageAvailableListener(null, null);
        }
        if (virtualDisplay != null) {
            virtualDisplay.release();
            virtualDisplay = null;
        }
        if (imageReader != null) {
            imageReader.close();
            imageReader = null;
        }
        if (mediaProjection != null) {
            try {
                mediaProjection.stop();
            } catch (Throwable ignored) {
            }
            mediaProjection = null;
        }

        FilterAccessibilityService accessibilityService = FilterAccessibilityService.getInstance();
        if (accessibilityService != null) {
            accessibilityService.clearOverlay();
        }

        if (captureThread != null) {
            captureThread.quitSafely();
            captureThread = null;
            captureHandler = null;
        }

        recycleBitmap(captureBitmap);
        captureBitmap = null;
        recycleBitmap(lowResolutionBitmap);
        lowResolutionBitmap = null;

        PerformanceLog.log("session_stop pipeline=media_projection frames=" + performanceFrameIndex);
        stopForeground(STOP_FOREGROUND_REMOVE);
        stopSelf();
        Log.i(TAG, "Capture resources released");
    }

    @Override
    public void onDestroy() {
        if (!cleanedUp) {
            cleanupAndStop();
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private static void recycleBitmap(Bitmap bitmap) {
        if (bitmap != null && !bitmap.isRecycled()) {
            bitmap.recycle();
        }
    }
}
