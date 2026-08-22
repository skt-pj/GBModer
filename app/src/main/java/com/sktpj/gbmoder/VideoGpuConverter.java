package com.sktpj.gbmoder;

import android.content.Context;
import android.graphics.SurfaceTexture;
import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.media.MediaMuxer;
import android.net.Uri;
import android.opengl.EGL14;
import android.opengl.EGLConfig;
import android.opengl.EGLContext;
import android.opengl.EGLDisplay;
import android.opengl.EGLExt;
import android.opengl.EGLSurface;
import android.opengl.GLES11Ext;
import android.opengl.GLES20;
import android.os.ParcelFileDescriptor;
import android.util.Log;
import android.view.Surface;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.util.Arrays;

final class VideoGpuConverter {
    private static final String TAG = "GBModerVideoGpu";
    private static final String OUTPUT_MIME = "video/avc";
    private static final long CODEC_TIMEOUT_US = 20_000L;
    private static final long FRAME_WAIT_MS = 5_000L;
    private static final int EGL_RECORDABLE_ANDROID = 0x3142;
    private static final int LOOKUP_WIDTH = 256;
    private static final int LOOKUP_HEIGHT = 128;
    private static final int GBC_COLOR_LIMIT = 56;

    static final class GpuUnavailableException extends Exception {
        GpuUnavailableException(String message) {
            super(message);
        }

        GpuUnavailableException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    private VideoGpuConverter() {
    }

    static void convert(
            Context context,
            Uri source,
            Uri output,
            MediaFileConverter.Options options,
            MediaFileConverter.Progress progress
    ) throws Exception {
        MediaExtractor videoExtractor = null;
        MediaExtractor audioExtractor = null;
        MediaCodec decoder = null;
        MediaCodec encoder = null;
        Surface encoderInputSurface = null;
        GpuPipe gpuPipe = null;
        MediaMuxer muxer = null;
        ParcelFileDescriptor outputFd = null;
        boolean decoderStarted = false;
        boolean encoderStarted = false;
        MuxerState muxerState = null;

        try {
            notifyProgress(progress, 1, "GPU動画変換を準備しています");

            videoExtractor = new MediaExtractor();
            videoExtractor.setDataSource(context, source, null);
            int videoTrack = findVideoTrack(videoExtractor);
            if (videoTrack < 0) {
                throw new IOException("動画トラックを読み取れません");
            }
            MediaFormat sourceFormat = videoExtractor.getTrackFormat(videoTrack);
            String sourceMime = sourceFormat.getString(MediaFormat.KEY_MIME);
            if (sourceMime == null || !sourceMime.startsWith("video/")) {
                throw new IOException("動画コーデックを判定できません");
            }
            videoExtractor.selectTrack(videoTrack);

            int codedWidth = getPositiveInt(sourceFormat, MediaFormat.KEY_WIDTH, 0);
            int codedHeight = getPositiveInt(sourceFormat, MediaFormat.KEY_HEIGHT, 0);
            if (codedWidth <= 0 || codedHeight <= 0) {
                throw new IOException("動画サイズを取得できません");
            }

            int rotation = normalizeRotation(getInt(sourceFormat, MediaFormat.KEY_ROTATION, 0));
            int displayWidth = (rotation == 90 || rotation == 270) ? codedHeight : codedWidth;
            int displayHeight = (rotation == 90 || rotation == 270) ? codedWidth : codedHeight;
            int targetWidth = makeEven(GameBoyFilter.getTargetWidth(options.resolution, displayWidth));
            int targetHeight = makeEven(GameBoyFilter.getTargetHeight(options.resolution, displayHeight));
            int nominalFps = clamp(getInt(sourceFormat, MediaFormat.KEY_FRAME_RATE, 30), 1, 120);
            long durationUs = getLong(sourceFormat, MediaFormat.KEY_DURATION, 0L);

            encoder = createSurfaceEncoder(targetWidth, targetHeight, nominalFps);
            encoderInputSurface = encoder.createInputSurface();

            gpuPipe = new GpuPipe(
                    encoderInputSurface,
                    codedWidth,
                    codedHeight,
                    targetWidth,
                    targetHeight,
                    rotation,
                    options
            );

            decoder = MediaCodec.createDecoderByType(sourceMime);
            decoder.configure(sourceFormat, gpuPipe.getDecoderSurface(), null, 0);

            outputFd = context.getContentResolver().openFileDescriptor(output, "rwt");
            if (outputFd == null) {
                throw new IOException("動画の保存先を開けません");
            }
            muxer = new MediaMuxer(
                    outputFd.getFileDescriptor(),
                    MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4
            );

            audioExtractor = new MediaExtractor();
            audioExtractor.setDataSource(context, source, null);
            int sourceAudioTrack = findAacAudioTrack(audioExtractor);
            muxerState = new MuxerState(muxer);
            if (sourceAudioTrack >= 0) {
                audioExtractor.selectTrack(sourceAudioTrack);
                muxerState.audioTrack = muxer.addTrack(audioExtractor.getTrackFormat(sourceAudioTrack));
            }

            encoder.start();
            encoderStarted = true;
            decoder.start();
            decoderStarted = true;

            MediaCodec.BufferInfo decoderInfo = new MediaCodec.BufferInfo();
            MediaCodec.BufferInfo encoderInfo = new MediaCodec.BufferInfo();
            boolean inputDone = false;
            boolean decoderDone = false;
            boolean encoderDone = false;
            int renderedFrames = 0;
            long lastPresentationUs = -1L;
            long firstPresentationUs = -1L;

            notifyProgress(progress, 3, "GPUで動画を変換しています");

            while (!encoderDone) {
                if (!inputDone) {
                    int inputIndex = decoder.dequeueInputBuffer(CODEC_TIMEOUT_US);
                    if (inputIndex >= 0) {
                        ByteBuffer inputBuffer = decoder.getInputBuffer(inputIndex);
                        if (inputBuffer == null) {
                            throw new IOException("動画デコーダー入力を取得できません");
                        }
                        inputBuffer.clear();
                        int sampleSize = videoExtractor.readSampleData(inputBuffer, 0);
                        long sampleTimeUs = videoExtractor.getSampleTime();
                        if (sampleSize < 0 || sampleTimeUs < 0L) {
                            decoder.queueInputBuffer(
                                    inputIndex,
                                    0,
                                    0,
                                    Math.max(0L, lastPresentationUs + 1L),
                                    MediaCodec.BUFFER_FLAG_END_OF_STREAM
                            );
                            inputDone = true;
                        } else {
                            decoder.queueInputBuffer(
                                    inputIndex,
                                    0,
                                    sampleSize,
                                    sampleTimeUs,
                                    videoExtractor.getSampleFlags()
                            );
                            videoExtractor.advance();
                        }
                    }
                }

                drainEncoder(encoder, encoderInfo, muxerState, false);

                if (!decoderDone) {
                    int outputIndex = decoder.dequeueOutputBuffer(decoderInfo, CODEC_TIMEOUT_US);
                    if (outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                        // Surface output format is informational; rendering is controlled by EGL.
                    } else if (outputIndex >= 0) {
                        boolean render = decoderInfo.size > 0;
                        boolean eos = (decoderInfo.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0;
                        long sourcePtsUs = decoderInfo.presentationTimeUs;
                        decoder.releaseOutputBuffer(outputIndex, render);

                        if (render) {
                            long presentationUs = lastPresentationUs < 0L
                                    ? Math.max(0L, sourcePtsUs)
                                    : Math.max(lastPresentationUs + 1L, sourcePtsUs);
                            if (firstPresentationUs < 0L) {
                                firstPresentationUs = presentationUs;
                            }

                            gpuPipe.awaitNewImage();
                            gpuPipe.drawFrame(presentationUs);
                            renderedFrames++;
                            lastPresentationUs = presentationUs;

                            int percent;
                            if (durationUs > 0L) {
                                percent = 5 + (int) Math.round(
                                        Math.min(1.0, presentationUs / (double) durationUs) * 80.0
                                );
                            } else {
                                percent = Math.min(85, 5 + renderedFrames / 3);
                            }
                            notifyProgress(
                                    progress,
                                    Math.min(85, percent),
                                    "GPUで動画を変換しています " + renderedFrames
                            );
                        }

                        if (eos) {
                            decoderDone = true;
                            encoder.signalEndOfInputStream();
                        }
                    }
                }

                if (decoderDone) {
                    encoderDone = drainEncoder(encoder, encoderInfo, muxerState, true);
                }
            }

            if (!muxerState.started || muxerState.videoTrack < 0 || renderedFrames <= 0) {
                throw new IOException("GPU動画トラックを生成できません");
            }

            if (sourceAudioTrack >= 0 && muxerState.audioTrack >= 0) {
                notifyProgress(progress, 90, "音声を保持しています");
                copyAudioTrack(audioExtractor, muxerState, durationUs);
            }

            PerformanceLog.log(
                    "video_conversion_complete"
                            + " render_path=gpu_surface_shader"
                            + " decoder_surface=true"
                            + " encoder_surface=true"
                            + " rgba_yuv_cpu=false"
                            + " source_pts=true"
                            + " mode=" + options.mode
                            + " gbc_hybrid=" + GameBoyFilter.MODE_GBC.equals(options.mode)
                            + " target=" + targetWidth + "x" + targetHeight
                            + " source=" + codedWidth + "x" + codedHeight
                            + " rotation=" + rotation
                            + " nominal_fps=" + nominalFps
                            + " frames=" + renderedFrames
                            + " first_pts_us=" + firstPresentationUs
                            + " last_pts_us=" + lastPresentationUs
            );
            notifyProgress(progress, 100, "GPU動画を保存しました");
        } catch (GpuUnavailableException unavailable) {
            throw unavailable;
        } catch (IllegalArgumentException | IllegalStateException setupError) {
            if (!decoderStarted && !encoderStarted && (muxerState == null || !muxerState.started)) {
                throw new GpuUnavailableException(
                        "GPU Surface動画経路を初期化できません",
                        setupError
                );
            }
            throw setupError;
        } finally {
            if (decoder != null) {
                if (decoderStarted) {
                    try {
                        decoder.stop();
                    } catch (Throwable ignored) {
                    }
                }
                try {
                    decoder.release();
                } catch (Throwable ignored) {
                }
            }
            if (gpuPipe != null) {
                try {
                    gpuPipe.release();
                } catch (Throwable ignored) {
                }
            }
            if (encoder != null) {
                if (encoderStarted) {
                    try {
                        encoder.stop();
                    } catch (Throwable ignored) {
                    }
                }
                try {
                    encoder.release();
                } catch (Throwable ignored) {
                }
            }
            if (encoderInputSurface != null) {
                try {
                    encoderInputSurface.release();
                } catch (Throwable ignored) {
                }
            }
            if (videoExtractor != null) {
                try {
                    videoExtractor.release();
                } catch (Throwable ignored) {
                }
            }
            if (audioExtractor != null) {
                try {
                    audioExtractor.release();
                } catch (Throwable ignored) {
                }
            }
            if (muxer != null) {
                if (muxerState != null && muxerState.started) {
                    try {
                        muxer.stop();
                    } catch (Throwable ignored) {
                    }
                }
                try {
                    muxer.release();
                } catch (Throwable ignored) {
                }
            }
            if (outputFd != null) {
                try {
                    outputFd.close();
                } catch (Throwable ignored) {
                }
            }
        }
    }

    private static MediaCodec createSurfaceEncoder(
            int width,
            int height,
            int nominalFps
    ) throws Exception {
        MediaCodec encoder = MediaCodec.createEncoderByType(OUTPUT_MIME);
        MediaCodecInfo.CodecCapabilities capabilities =
                encoder.getCodecInfo().getCapabilitiesForType(OUTPUT_MIME);
        boolean supportsSurface = false;
        for (int colorFormat : capabilities.colorFormats) {
            if (colorFormat == MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface) {
                supportsSurface = true;
                break;
            }
        }
        if (!supportsSurface) {
            encoder.release();
            throw new GpuUnavailableException("H.264エンコーダーがSurface入力に対応していません");
        }

        MediaFormat outputFormat = MediaFormat.createVideoFormat(OUTPUT_MIME, width, height);
        outputFormat.setInteger(
                MediaFormat.KEY_COLOR_FORMAT,
                MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface
        );
        outputFormat.setInteger(MediaFormat.KEY_FRAME_RATE, nominalFps);
        outputFormat.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1);
        outputFormat.setInteger(
                MediaFormat.KEY_BIT_RATE,
                Math.max(300_000, Math.min(20_000_000, width * height * nominalFps * 2))
        );
        try {
            encoder.configure(outputFormat, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE);
            return encoder;
        } catch (Throwable error) {
            try {
                encoder.release();
            } catch (Throwable ignored) {
            }
            throw error;
        }
    }

    private static boolean drainEncoder(
            MediaCodec encoder,
            MediaCodec.BufferInfo info,
            MuxerState state,
            boolean waitForEos
    ) throws IOException {
        while (true) {
            int outputIndex = encoder.dequeueOutputBuffer(
                    info,
                    waitForEos ? CODEC_TIMEOUT_US : 0L
            );
            if (outputIndex == MediaCodec.INFO_TRY_AGAIN_LATER) {
                return false;
            }
            if (outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                if (state.videoTrack >= 0) {
                    throw new IOException("動画出力形式が複数回変更されました");
                }
                state.videoTrack = state.muxer.addTrack(encoder.getOutputFormat());
                state.muxer.start();
                state.started = true;
                continue;
            }
            if (outputIndex < 0) {
                continue;
            }

            ByteBuffer outputBuffer = encoder.getOutputBuffer(outputIndex);
            if (outputBuffer == null) {
                throw new IOException("動画エンコーダー出力を取得できません");
            }

            boolean eos = (info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0;
            if ((info.flags & MediaCodec.BUFFER_FLAG_CODEC_CONFIG) != 0) {
                info.size = 0;
            }
            if (info.size > 0) {
                if (!state.started || state.videoTrack < 0) {
                    throw new IOException("動画Muxerが開始されていません");
                }
                outputBuffer.position(info.offset);
                outputBuffer.limit(info.offset + info.size);
                state.muxer.writeSampleData(state.videoTrack, outputBuffer, info);
            }
            encoder.releaseOutputBuffer(outputIndex, false);

            if (eos) {
                return true;
            }
            if (!waitForEos) {
                continue;
            }
        }
    }

    private static void copyAudioTrack(
            MediaExtractor extractor,
            MuxerState state,
            long durationUs
    ) throws IOException {
        MediaFormat format = extractor.getTrackFormat(findSelectedAacTrack(extractor));
        int maxInputSize = getPositiveInt(format, MediaFormat.KEY_MAX_INPUT_SIZE, 256 * 1024);
        ByteBuffer buffer = ByteBuffer.allocateDirect(Math.max(64 * 1024, maxInputSize));
        MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();

        while (true) {
            buffer.clear();
            int size = extractor.readSampleData(buffer, 0);
            long timeUs = extractor.getSampleTime();
            if (size < 0 || timeUs < 0L) {
                break;
            }
            if (durationUs > 0L && timeUs > durationUs) {
                break;
            }

            info.offset = 0;
            info.size = size;
            info.presentationTimeUs = timeUs;
            info.flags = extractor.getSampleFlags();
            buffer.position(0);
            buffer.limit(size);
            state.muxer.writeSampleData(state.audioTrack, buffer, info);

            if (!extractor.advance()) {
                break;
            }
        }
    }

    private static int findSelectedAacTrack(MediaExtractor extractor) throws IOException {
        for (int i = 0; i < extractor.getTrackCount(); i++) {
            MediaFormat format = extractor.getTrackFormat(i);
            String mime = format.getString(MediaFormat.KEY_MIME);
            if ("audio/mp4a-latm".equals(mime)) {
                return i;
            }
        }
        throw new IOException("AAC音声トラックを取得できません");
    }

    private static int findVideoTrack(MediaExtractor extractor) {
        for (int i = 0; i < extractor.getTrackCount(); i++) {
            MediaFormat format = extractor.getTrackFormat(i);
            String mime = format.getString(MediaFormat.KEY_MIME);
            if (mime != null && mime.startsWith("video/")) {
                return i;
            }
        }
        return -1;
    }

    private static int findAacAudioTrack(MediaExtractor extractor) {
        for (int i = 0; i < extractor.getTrackCount(); i++) {
            MediaFormat format = extractor.getTrackFormat(i);
            String mime = format.getString(MediaFormat.KEY_MIME);
            if ("audio/mp4a-latm".equals(mime)) {
                return i;
            }
        }
        return -1;
    }

    private static int getPositiveInt(MediaFormat format, String key, int fallback) {
        int value = getInt(format, key, fallback);
        return value > 0 ? value : fallback;
    }

    private static int getInt(MediaFormat format, String key, int fallback) {
        try {
            return format.containsKey(key) ? format.getInteger(key) : fallback;
        } catch (Throwable ignored) {
            return fallback;
        }
    }

    private static long getLong(MediaFormat format, String key, long fallback) {
        try {
            return format.containsKey(key) ? format.getLong(key) : fallback;
        } catch (Throwable ignored) {
            return fallback;
        }
    }

    private static int makeEven(int value) {
        int safe = Math.max(2, value);
        return (safe & 1) == 0 ? safe : safe + 1;
    }

    private static int normalizeRotation(int rotation) {
        int normalized = ((rotation % 360) + 360) % 360;
        if (normalized == 90 || normalized == 180 || normalized == 270) {
            return normalized;
        }
        return 0;
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    private static void notifyProgress(
            MediaFileConverter.Progress progress,
            int percent,
            String message
    ) {
        if (progress != null) {
            progress.onProgress(percent, message);
        }
    }

    private static final class MuxerState {
        final MediaMuxer muxer;
        int videoTrack = -1;
        int audioTrack = -1;
        boolean started;

        MuxerState(MediaMuxer muxer) {
            this.muxer = muxer;
        }
    }

    private static final class GpuPipe implements SurfaceTexture.OnFrameAvailableListener {
        private final Object frameSync = new Object();
        private boolean frameAvailable;

        private EGLDisplay eglDisplay = EGL14.EGL_NO_DISPLAY;
        private EGLContext eglContext = EGL14.EGL_NO_CONTEXT;
        private EGLSurface eglSurface = EGL14.EGL_NO_SURFACE;
        private final SurfaceTexture decoderTexture;
        private final Surface decoderSurface;
        private final FrameRenderer renderer;
        private final float[] textureMatrix = new float[16];

        GpuPipe(
                Surface encoderSurface,
                int sourceWidth,
                int sourceHeight,
                int targetWidth,
                int targetHeight,
                int rotation,
                MediaFileConverter.Options options
        ) throws GpuUnavailableException {
            try {
                setupEgl(encoderSurface);
                makeCurrent();

                renderer = new FrameRenderer(targetWidth, targetHeight, rotation, options);
                int textureId = renderer.getExternalTextureId();
                decoderTexture = new SurfaceTexture(textureId);
                decoderTexture.setDefaultBufferSize(sourceWidth, sourceHeight);
                decoderTexture.setOnFrameAvailableListener(this);
                decoderSurface = new Surface(decoderTexture);
            } catch (Throwable error) {
                releaseEgl();
                throw new GpuUnavailableException("OpenGL ES動画経路を初期化できません", error);
            }
        }

        Surface getDecoderSurface() {
            return decoderSurface;
        }

        void awaitNewImage() throws IOException {
            long deadline = System.currentTimeMillis() + FRAME_WAIT_MS;
            synchronized (frameSync) {
                while (!frameAvailable) {
                    long remaining = deadline - System.currentTimeMillis();
                    if (remaining <= 0L) {
                        throw new IOException("GPU動画フレームの待機がタイムアウトしました");
                    }
                    try {
                        frameSync.wait(remaining);
                    } catch (InterruptedException interrupted) {
                        Thread.currentThread().interrupt();
                        throw new IOException("GPU動画フレーム待機が中断されました", interrupted);
                    }
                }
                frameAvailable = false;
            }

            makeCurrent();
            decoderTexture.updateTexImage();
            decoderTexture.getTransformMatrix(textureMatrix);
        }

        void drawFrame(long presentationTimeUs) throws IOException {
            makeCurrent();
            renderer.draw(textureMatrix);
            if (!EGLExt.eglPresentationTimeANDROID(
                    eglDisplay,
                    eglSurface,
                    Math.max(0L, presentationTimeUs) * 1000L
            )) {
                throw new IOException("GPU動画PTSを設定できません");
            }
            if (!EGL14.eglSwapBuffers(eglDisplay, eglSurface)) {
                throw new IOException("GPU動画フレームをエンコーダーへ送れません");
            }
        }

        @Override
        public void onFrameAvailable(SurfaceTexture surfaceTexture) {
            synchronized (frameSync) {
                if (frameAvailable) {
                    Log.w(TAG, "FrameAvailable signaled before previous frame was consumed");
                }
                frameAvailable = true;
                frameSync.notifyAll();
            }
        }

        void release() {
            try {
                decoderSurface.release();
            } catch (Throwable ignored) {
            }
            try {
                decoderTexture.release();
            } catch (Throwable ignored) {
            }
            try {
                makeCurrent();
                renderer.release();
            } catch (Throwable ignored) {
            }
            releaseEgl();
        }

        private void setupEgl(Surface windowSurface) {
            eglDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY);
            if (eglDisplay == EGL14.EGL_NO_DISPLAY) {
                throw new IllegalStateException("EGL display unavailable");
            }

            int[] version = new int[2];
            if (!EGL14.eglInitialize(eglDisplay, version, 0, version, 1)) {
                throw new IllegalStateException("EGL initialize failed");
            }

            int[] configAttributes = {
                    EGL14.EGL_RED_SIZE, 8,
                    EGL14.EGL_GREEN_SIZE, 8,
                    EGL14.EGL_BLUE_SIZE, 8,
                    EGL14.EGL_ALPHA_SIZE, 8,
                    EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
                    EGL_RECORDABLE_ANDROID, 1,
                    EGL14.EGL_NONE
            };
            EGLConfig[] configs = new EGLConfig[1];
            int[] count = new int[1];
            if (!EGL14.eglChooseConfig(
                    eglDisplay,
                    configAttributes,
                    0,
                    configs,
                    0,
                    configs.length,
                    count,
                    0
            ) || count[0] <= 0) {
                throw new IllegalStateException("Recordable EGL config unavailable");
            }

            int[] contextAttributes = {
                    EGL14.EGL_CONTEXT_CLIENT_VERSION, 2,
                    EGL14.EGL_NONE
            };
            eglContext = EGL14.eglCreateContext(
                    eglDisplay,
                    configs[0],
                    EGL14.EGL_NO_CONTEXT,
                    contextAttributes,
                    0
            );
            if (eglContext == null || eglContext == EGL14.EGL_NO_CONTEXT) {
                throw new IllegalStateException("EGL context unavailable");
            }

            int[] surfaceAttributes = {EGL14.EGL_NONE};
            eglSurface = EGL14.eglCreateWindowSurface(
                    eglDisplay,
                    configs[0],
                    windowSurface,
                    surfaceAttributes,
                    0
            );
            if (eglSurface == null || eglSurface == EGL14.EGL_NO_SURFACE) {
                throw new IllegalStateException("Encoder EGL surface unavailable");
            }
        }

        private void makeCurrent() {
            if (!EGL14.eglMakeCurrent(
                    eglDisplay,
                    eglSurface,
                    eglSurface,
                    eglContext
            )) {
                throw new IllegalStateException("eglMakeCurrent failed");
            }
        }

        private void releaseEgl() {
            if (eglDisplay != EGL14.EGL_NO_DISPLAY) {
                try {
                    EGL14.eglMakeCurrent(
                            eglDisplay,
                            EGL14.EGL_NO_SURFACE,
                            EGL14.EGL_NO_SURFACE,
                            EGL14.EGL_NO_CONTEXT
                    );
                } catch (Throwable ignored) {
                }
                if (eglSurface != EGL14.EGL_NO_SURFACE) {
                    try {
                        EGL14.eglDestroySurface(eglDisplay, eglSurface);
                    } catch (Throwable ignored) {
                    }
                }
                if (eglContext != EGL14.EGL_NO_CONTEXT) {
                    try {
                        EGL14.eglDestroyContext(eglDisplay, eglContext);
                    } catch (Throwable ignored) {
                    }
                }
                try {
                    EGL14.eglReleaseThread();
                } catch (Throwable ignored) {
                }
                try {
                    EGL14.eglTerminate(eglDisplay);
                } catch (Throwable ignored) {
                }
            }
            eglDisplay = EGL14.EGL_NO_DISPLAY;
            eglContext = EGL14.EGL_NO_CONTEXT;
            eglSurface = EGL14.EGL_NO_SURFACE;
        }
    }

    private static final class FrameRenderer {
        private static final float[] VERTICES = {
                -1f, -1f,
                 1f, -1f,
                -1f,  1f,
                 1f,  1f
        };

        private static final String VERTEX_SHADER =
                "attribute vec4 aPosition;\n"
                        + "attribute vec2 aTexCoord;\n"
                        + "uniform mat4 uTexMatrix;\n"
                        + "varying vec2 vTexCoord;\n"
                        + "void main() {\n"
                        + "  gl_Position = aPosition;\n"
                        + "  vTexCoord = (uTexMatrix * vec4(aTexCoord, 0.0, 1.0)).xy;\n"
                        + "}\n";

        private static final String EXTERNAL_FRAGMENT_SHADER =
                "#extension GL_OES_EGL_image_external : require\n"
                        + "precision highp float;\n"
                        + "uniform samplerExternalOES uTexture;\n"
                        + "uniform float uMode;\n"
                        + "uniform float uBrightness;\n"
                        + "uniform float uContrast;\n"
                        + "uniform float uDither;\n"
                        + "uniform float uOutputHeight;\n"
                        + "varying vec2 vTexCoord;\n"
                        + "float bayer4(float x, float y) {\n"
                        + "  x = mod(x, 4.0); y = mod(y, 4.0);\n"
                        + "  if (y < 0.5) { if (x < 0.5) return 0.0; if (x < 1.5) return 8.0; if (x < 2.5) return 2.0; return 10.0; }\n"
                        + "  if (y < 1.5) { if (x < 0.5) return 12.0; if (x < 1.5) return 4.0; if (x < 2.5) return 14.0; return 6.0; }\n"
                        + "  if (y < 2.5) { if (x < 0.5) return 3.0; if (x < 1.5) return 11.0; if (x < 2.5) return 1.0; return 9.0; }\n"
                        + "  if (x < 0.5) return 15.0; if (x < 1.5) return 7.0; if (x < 2.5) return 13.0; return 5.0;\n"
                        + "}\n"
                        + "float q5(float value) {\n"
                        + "  float c = clamp(value, 0.0, 255.0);\n"
                        + "  float q = floor((c / 255.0) * 31.0 + 0.5);\n"
                        + "  return floor((q / 31.0) * 255.0 + 0.5) / 255.0;\n"
                        + "}\n"
                        + "float q6(float value) {\n"
                        + "  float c = clamp(value, 0.0, 255.0);\n"
                        + "  float q = floor((c / 255.0) * 63.0 + 0.5);\n"
                        + "  return floor((q / 63.0) * 255.0 + 0.5) / 255.0;\n"
                        + "}\n"
                        + "void main() {\n"
                        + "  vec4 sampleColor = texture2D(uTexture, vTexCoord);\n"
                        + "  float r = sampleColor.r * 255.0;\n"
                        + "  float g = sampleColor.g * 255.0;\n"
                        + "  float b = sampleColor.b * 255.0;\n"
                        + "  float px = floor(gl_FragCoord.x - 0.5);\n"
                        + "  float py = floor(uOutputHeight - gl_FragCoord.y);\n"
                        + "  float threshold = bayer4(px, py) - 7.5;\n"
                        + "  if (uMode < 0.5) {\n"
                        + "    float lum = 0.299*r + 0.587*g + 0.114*b;\n"
                        + "    lum = ((lum - 128.0) * uContrast) + 128.0 + uBrightness;\n"
                        + "    if (uDither > 0.5) lum += threshold * 7.0;\n"
                        + "    lum = clamp(lum, 0.0, 255.0);\n"
                        + "    if (lum < 64.0) gl_FragColor = vec4(15.0/255.0,56.0/255.0,15.0/255.0,1.0);\n"
                        + "    else if (lum < 128.0) gl_FragColor = vec4(48.0/255.0,98.0/255.0,48.0/255.0,1.0);\n"
                        + "    else if (lum < 192.0) gl_FragColor = vec4(139.0/255.0,172.0/255.0,15.0/255.0,1.0);\n"
                        + "    else gl_FragColor = vec4(155.0/255.0,188.0/255.0,15.0/255.0,1.0);\n"
                        + "    return;\n"
                        + "  }\n"
                        + "  r = ((r - 128.0) * uContrast) + 128.0 + uBrightness;\n"
                        + "  g = ((g - 128.0) * uContrast) + 128.0 + uBrightness;\n"
                        + "  b = ((b - 128.0) * uContrast) + 128.0 + uBrightness;\n"
                        + "  if (uDither > 0.5) { float d = threshold * 2.5; r += d; g += d; b += d; }\n"
                        + "  if (uMode > 2.5) gl_FragColor = vec4(q6(r), q6(g), q6(b), 1.0);\n"
                        + "  else gl_FragColor = vec4(q5(r), q5(g), q5(b), 1.0);\n"
                        + "}\n";

        private static final String GBC_LOOKUP_FRAGMENT_SHADER =
                "precision highp float;\n"
                        + "uniform sampler2D uImage;\n"
                        + "uniform sampler2D uLookup;\n"
                        + "varying vec2 vTexCoord;\n"
                        + "void main() {\n"
                        + "  vec3 c = texture2D(uImage, vTexCoord).rgb;\n"
                        + "  float r5 = floor(c.r * 31.0 + 0.5);\n"
                        + "  float g5 = floor(c.g * 31.0 + 0.5);\n"
                        + "  float b5 = floor(c.b * 31.0 + 0.5);\n"
                        + "  float key = r5 * 1024.0 + g5 * 32.0 + b5;\n"
                        + "  float x = mod(key, 256.0);\n"
                        + "  float y = floor(key / 256.0);\n"
                        + "  vec2 lookupUv = (vec2(x, y) + vec2(0.5)) / vec2(256.0, 128.0);\n"
                        + "  gl_FragColor = texture2D(uLookup, lookupUv);\n"
                        + "}\n";

        private final int targetWidth;
        private final int targetHeight;
        private final MediaFileConverter.Options options;
        private final boolean gbcMode;
        private final FloatBuffer vertexBuffer;
        private final FloatBuffer textureBuffer;
        private final FloatBuffer identityTextureBuffer;
        private final int externalTextureId;
        private final int externalProgram;
        private final int lookupProgram;

        private int gbcTextureId;
        private int gbcFramebufferId;
        private int lookupTextureId;
        private final ByteBuffer readback;
        private final ByteBuffer lookupPixels;
        private final int[] counts = new int[32768];
        private final int[] paletteKeys = new int[GBC_COLOR_LIMIT];
        private final int[] paletteCounts = new int[GBC_COLOR_LIMIT];

        FrameRenderer(
                int targetWidth,
                int targetHeight,
                int rotation,
                MediaFileConverter.Options options
        ) {
            this.targetWidth = targetWidth;
            this.targetHeight = targetHeight;
            this.options = options;
            this.gbcMode = GameBoyFilter.MODE_GBC.equals(options.mode);

            vertexBuffer = allocateFloatBuffer(VERTICES);
            textureBuffer = allocateFloatBuffer(textureCoordinates(rotation));
            identityTextureBuffer = allocateFloatBuffer(textureCoordinates(0));

            externalProgram = createProgram(VERTEX_SHADER, EXTERNAL_FRAGMENT_SHADER);
            lookupProgram = gbcMode
                    ? createProgram(VERTEX_SHADER, GBC_LOOKUP_FRAGMENT_SHADER)
                    : 0;

            int[] textures = new int[1];
            GLES20.glGenTextures(1, textures, 0);
            externalTextureId = textures[0];
            GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, externalTextureId);
            GLES20.glTexParameteri(
                    GLES11Ext.GL_TEXTURE_EXTERNAL_OES,
                    GLES20.GL_TEXTURE_MIN_FILTER,
                    GLES20.GL_NEAREST
            );
            GLES20.glTexParameteri(
                    GLES11Ext.GL_TEXTURE_EXTERNAL_OES,
                    GLES20.GL_TEXTURE_MAG_FILTER,
                    GLES20.GL_NEAREST
            );
            GLES20.glTexParameteri(
                    GLES11Ext.GL_TEXTURE_EXTERNAL_OES,
                    GLES20.GL_TEXTURE_WRAP_S,
                    GLES20.GL_CLAMP_TO_EDGE
            );
            GLES20.glTexParameteri(
                    GLES11Ext.GL_TEXTURE_EXTERNAL_OES,
                    GLES20.GL_TEXTURE_WRAP_T,
                    GLES20.GL_CLAMP_TO_EDGE
            );
            checkGl("external texture");

            if (gbcMode) {
                setupGbcTargets();
                readback = ByteBuffer.allocateDirect(targetWidth * targetHeight * 4)
                        .order(ByteOrder.nativeOrder());
                lookupPixels = ByteBuffer.allocateDirect(LOOKUP_WIDTH * LOOKUP_HEIGHT * 4)
                        .order(ByteOrder.nativeOrder());
            } else {
                readback = null;
                lookupPixels = null;
            }
        }

        int getExternalTextureId() {
            return externalTextureId;
        }

        void draw(float[] textureMatrix) throws IOException {
            if (gbcMode) {
                renderExternal(textureMatrix, gbcFramebufferId);
                updateGbcLookup();
                renderLookup();
            } else {
                renderExternal(textureMatrix, 0);
            }
            checkGl("draw frame");
        }

        void release() {
            if (externalProgram != 0) {
                GLES20.glDeleteProgram(externalProgram);
            }
            if (lookupProgram != 0) {
                GLES20.glDeleteProgram(lookupProgram);
            }
            int[] textures = {externalTextureId, gbcTextureId, lookupTextureId};
            GLES20.glDeleteTextures(textures.length, textures, 0);
            if (gbcFramebufferId != 0) {
                int[] framebuffers = {gbcFramebufferId};
                GLES20.glDeleteFramebuffers(1, framebuffers, 0);
            }
        }

        private void renderExternal(float[] textureMatrix, int framebuffer) {
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, framebuffer);
            GLES20.glViewport(0, 0, targetWidth, targetHeight);
            GLES20.glUseProgram(externalProgram);

            int position = GLES20.glGetAttribLocation(externalProgram, "aPosition");
            int texCoord = GLES20.glGetAttribLocation(externalProgram, "aTexCoord");
            int texMatrix = GLES20.glGetUniformLocation(externalProgram, "uTexMatrix");

            vertexBuffer.position(0);
            GLES20.glEnableVertexAttribArray(position);
            GLES20.glVertexAttribPointer(position, 2, GLES20.GL_FLOAT, false, 0, vertexBuffer);

            textureBuffer.position(0);
            GLES20.glEnableVertexAttribArray(texCoord);
            GLES20.glVertexAttribPointer(texCoord, 2, GLES20.GL_FLOAT, false, 0, textureBuffer);

            GLES20.glUniformMatrix4fv(texMatrix, 1, false, textureMatrix, 0);
            GLES20.glUniform1f(
                    GLES20.glGetUniformLocation(externalProgram, "uMode"),
                    modeValue(options.mode)
            );
            GLES20.glUniform1f(
                    GLES20.glGetUniformLocation(externalProgram, "uBrightness"),
                    options.brightness
            );
            GLES20.glUniform1f(
                    GLES20.glGetUniformLocation(externalProgram, "uContrast"),
                    options.contrast / 100.0f
            );
            GLES20.glUniform1f(
                    GLES20.glGetUniformLocation(externalProgram, "uDither"),
                    options.dither ? 1.0f : 0.0f
            );
            GLES20.glUniform1f(
                    GLES20.glGetUniformLocation(externalProgram, "uOutputHeight"),
                    targetHeight
            );

            GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
            GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, externalTextureId);
            GLES20.glUniform1i(
                    GLES20.glGetUniformLocation(externalProgram, "uTexture"),
                    0
            );
            GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4);
            GLES20.glDisableVertexAttribArray(position);
            GLES20.glDisableVertexAttribArray(texCoord);
        }

        private void setupGbcTargets() {
            int[] ids = new int[1];

            GLES20.glGenTextures(1, ids, 0);
            gbcTextureId = ids[0];
            GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, gbcTextureId);
            GLES20.glTexParameteri(
                    GLES20.GL_TEXTURE_2D,
                    GLES20.GL_TEXTURE_MIN_FILTER,
                    GLES20.GL_NEAREST
            );
            GLES20.glTexParameteri(
                    GLES20.GL_TEXTURE_2D,
                    GLES20.GL_TEXTURE_MAG_FILTER,
                    GLES20.GL_NEAREST
            );
            GLES20.glTexParameteri(
                    GLES20.GL_TEXTURE_2D,
                    GLES20.GL_TEXTURE_WRAP_S,
                    GLES20.GL_CLAMP_TO_EDGE
            );
            GLES20.glTexParameteri(
                    GLES20.GL_TEXTURE_2D,
                    GLES20.GL_TEXTURE_WRAP_T,
                    GLES20.GL_CLAMP_TO_EDGE
            );
            GLES20.glTexImage2D(
                    GLES20.GL_TEXTURE_2D,
                    0,
                    GLES20.GL_RGBA,
                    targetWidth,
                    targetHeight,
                    0,
                    GLES20.GL_RGBA,
                    GLES20.GL_UNSIGNED_BYTE,
                    null
            );

            GLES20.glGenFramebuffers(1, ids, 0);
            gbcFramebufferId = ids[0];
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, gbcFramebufferId);
            GLES20.glFramebufferTexture2D(
                    GLES20.GL_FRAMEBUFFER,
                    GLES20.GL_COLOR_ATTACHMENT0,
                    GLES20.GL_TEXTURE_2D,
                    gbcTextureId,
                    0
            );
            if (GLES20.glCheckFramebufferStatus(GLES20.GL_FRAMEBUFFER)
                    != GLES20.GL_FRAMEBUFFER_COMPLETE) {
                throw new IllegalStateException("GBC framebuffer unavailable");
            }
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0);

            GLES20.glGenTextures(1, ids, 0);
            lookupTextureId = ids[0];
            GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, lookupTextureId);
            GLES20.glTexParameteri(
                    GLES20.GL_TEXTURE_2D,
                    GLES20.GL_TEXTURE_MIN_FILTER,
                    GLES20.GL_NEAREST
            );
            GLES20.glTexParameteri(
                    GLES20.GL_TEXTURE_2D,
                    GLES20.GL_TEXTURE_MAG_FILTER,
                    GLES20.GL_NEAREST
            );
            GLES20.glTexParameteri(
                    GLES20.GL_TEXTURE_2D,
                    GLES20.GL_TEXTURE_WRAP_S,
                    GLES20.GL_CLAMP_TO_EDGE
            );
            GLES20.glTexParameteri(
                    GLES20.GL_TEXTURE_2D,
                    GLES20.GL_TEXTURE_WRAP_T,
                    GLES20.GL_CLAMP_TO_EDGE
            );
            GLES20.glTexImage2D(
                    GLES20.GL_TEXTURE_2D,
                    0,
                    GLES20.GL_RGBA,
                    LOOKUP_WIDTH,
                    LOOKUP_HEIGHT,
                    0,
                    GLES20.GL_RGBA,
                    GLES20.GL_UNSIGNED_BYTE,
                    null
            );
            checkGl("GBC targets");
        }

        private void updateGbcLookup() {
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, gbcFramebufferId);
            readback.clear();
            GLES20.glReadPixels(
                    0,
                    0,
                    targetWidth,
                    targetHeight,
                    GLES20.GL_RGBA,
                    GLES20.GL_UNSIGNED_BYTE,
                    readback
            );
            readback.position(0);

            Arrays.fill(counts, 0);
            int pixelCount = targetWidth * targetHeight;
            for (int i = 0; i < pixelCount; i++) {
                int r = readback.get() & 0xff;
                int g = readback.get() & 0xff;
                int b = readback.get() & 0xff;
                readback.get();
                counts[rgb555Key(r, g, b)]++;
            }

            Arrays.fill(paletteKeys, -1);
            Arrays.fill(paletteCounts, 0);
            for (int key = 0; key < counts.length; key++) {
                int count = counts[key];
                if (count == 0) {
                    continue;
                }
                for (int slot = 0; slot < GBC_COLOR_LIMIT; slot++) {
                    if (count > paletteCounts[slot]) {
                        for (int shift = GBC_COLOR_LIMIT - 1; shift > slot; shift--) {
                            paletteCounts[shift] = paletteCounts[shift - 1];
                            paletteKeys[shift] = paletteKeys[shift - 1];
                        }
                        paletteCounts[slot] = count;
                        paletteKeys[slot] = key;
                        break;
                    }
                }
            }

            lookupPixels.clear();
            for (int key = 0; key < counts.length; key++) {
                int mapped = key;
                if (counts[key] > 0 && !containsPaletteKey(key)) {
                    mapped = nearestPaletteKey(key);
                }
                putLookupColor(lookupPixels, mapped);
            }
            lookupPixels.flip();

            GLES20.glActiveTexture(GLES20.GL_TEXTURE1);
            GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, lookupTextureId);
            GLES20.glTexSubImage2D(
                    GLES20.GL_TEXTURE_2D,
                    0,
                    0,
                    0,
                    LOOKUP_WIDTH,
                    LOOKUP_HEIGHT,
                    GLES20.GL_RGBA,
                    GLES20.GL_UNSIGNED_BYTE,
                    lookupPixels
            );
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0);
        }

        private void renderLookup() {
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0);
            GLES20.glViewport(0, 0, targetWidth, targetHeight);
            GLES20.glUseProgram(lookupProgram);

            int position = GLES20.glGetAttribLocation(lookupProgram, "aPosition");
            int texCoord = GLES20.glGetAttribLocation(lookupProgram, "aTexCoord");
            int texMatrix = GLES20.glGetUniformLocation(lookupProgram, "uTexMatrix");

            vertexBuffer.position(0);
            GLES20.glEnableVertexAttribArray(position);
            GLES20.glVertexAttribPointer(position, 2, GLES20.GL_FLOAT, false, 0, vertexBuffer);

            identityTextureBuffer.position(0);
            GLES20.glEnableVertexAttribArray(texCoord);
            GLES20.glVertexAttribPointer(
                    texCoord,
                    2,
                    GLES20.GL_FLOAT,
                    false,
                    0,
                    identityTextureBuffer
            );

            float[] identity = {
                    1,0,0,0,
                    0,1,0,0,
                    0,0,1,0,
                    0,0,0,1
            };
            GLES20.glUniformMatrix4fv(texMatrix, 1, false, identity, 0);

            GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
            GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, gbcTextureId);
            GLES20.glUniform1i(GLES20.glGetUniformLocation(lookupProgram, "uImage"), 0);

            GLES20.glActiveTexture(GLES20.GL_TEXTURE1);
            GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, lookupTextureId);
            GLES20.glUniform1i(GLES20.glGetUniformLocation(lookupProgram, "uLookup"), 1);

            GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4);
            GLES20.glDisableVertexAttribArray(position);
            GLES20.glDisableVertexAttribArray(texCoord);
        }

        private boolean containsPaletteKey(int key) {
            for (int paletteKey : paletteKeys) {
                if (paletteKey == key) {
                    return true;
                }
            }
            return false;
        }

        private int nearestPaletteKey(int sourceKey) {
            int sr = (sourceKey >> 10) & 31;
            int sg = (sourceKey >> 5) & 31;
            int sb = sourceKey & 31;
            int bestKey = paletteKeys[0] >= 0 ? paletteKeys[0] : sourceKey;
            int bestDistance = Integer.MAX_VALUE;

            for (int paletteKey : paletteKeys) {
                if (paletteKey < 0) {
                    continue;
                }
                int r = (paletteKey >> 10) & 31;
                int g = (paletteKey >> 5) & 31;
                int b = paletteKey & 31;
                int dr = sr - r;
                int dg = sg - g;
                int db = sb - b;
                int distance = dr * dr + dg * dg + db * db;
                if (distance < bestDistance) {
                    bestDistance = distance;
                    bestKey = paletteKey;
                }
            }
            return bestKey;
        }

        private static void putLookupColor(ByteBuffer buffer, int key) {
            int r5 = (key >> 10) & 31;
            int g5 = (key >> 5) & 31;
            int b5 = key & 31;
            int r = Math.round((r5 / 31.0f) * 255.0f);
            int g = Math.round((g5 / 31.0f) * 255.0f);
            int b = Math.round((b5 / 31.0f) * 255.0f);
            buffer.put((byte) r);
            buffer.put((byte) g);
            buffer.put((byte) b);
            buffer.put((byte) 255);
        }

        private static int rgb555Key(int r, int g, int b) {
            int r5 = Math.round((r / 255.0f) * 31.0f);
            int g5 = Math.round((g / 255.0f) * 31.0f);
            int b5 = Math.round((b / 255.0f) * 31.0f);
            return (r5 << 10) | (g5 << 5) | b5;
        }

        private static float modeValue(String mode) {
            if (GameBoyFilter.MODE_DS.equals(mode)) {
                return 3.0f;
            }
            if (GameBoyFilter.MODE_GBA.equals(mode)) {
                return 2.0f;
            }
            if (GameBoyFilter.MODE_GBC.equals(mode)) {
                return 1.0f;
            }
            return 0.0f;
        }

        private static float[] textureCoordinates(int rotation) {
            if (rotation == 90) {
                return new float[]{0f,1f, 0f,0f, 1f,1f, 1f,0f};
            }
            if (rotation == 180) {
                return new float[]{1f,1f, 0f,1f, 1f,0f, 0f,0f};
            }
            if (rotation == 270) {
                return new float[]{1f,0f, 1f,1f, 0f,0f, 0f,1f};
            }
            return new float[]{0f,0f, 1f,0f, 0f,1f, 1f,1f};
        }

        private static FloatBuffer allocateFloatBuffer(float[] values) {
            ByteBuffer bytes = ByteBuffer.allocateDirect(values.length * 4)
                    .order(ByteOrder.nativeOrder());
            FloatBuffer floats = bytes.asFloatBuffer();
            floats.put(values);
            floats.position(0);
            return floats;
        }

        private static int createProgram(String vertexSource, String fragmentSource) {
            int vertex = compileShader(GLES20.GL_VERTEX_SHADER, vertexSource);
            int fragment = compileShader(GLES20.GL_FRAGMENT_SHADER, fragmentSource);
            int program = GLES20.glCreateProgram();
            GLES20.glAttachShader(program, vertex);
            GLES20.glAttachShader(program, fragment);
            GLES20.glLinkProgram(program);

            int[] status = new int[1];
            GLES20.glGetProgramiv(program, GLES20.GL_LINK_STATUS, status, 0);
            GLES20.glDeleteShader(vertex);
            GLES20.glDeleteShader(fragment);

            if (status[0] == 0) {
                String log = GLES20.glGetProgramInfoLog(program);
                GLES20.glDeleteProgram(program);
                throw new IllegalStateException("OpenGL program link failed: " + log);
            }
            return program;
        }

        private static int compileShader(int type, String source) {
            int shader = GLES20.glCreateShader(type);
            GLES20.glShaderSource(shader, source);
            GLES20.glCompileShader(shader);

            int[] status = new int[1];
            GLES20.glGetShaderiv(shader, GLES20.GL_COMPILE_STATUS, status, 0);
            if (status[0] == 0) {
                String log = GLES20.glGetShaderInfoLog(shader);
                GLES20.glDeleteShader(shader);
                throw new IllegalStateException("OpenGL shader compile failed: " + log);
            }
            return shader;
        }

        private static void checkGl(String stage) {
            int error = GLES20.glGetError();
            if (error != GLES20.GL_NO_ERROR) {
                throw new IllegalStateException(
                        stage + " OpenGL error 0x" + Integer.toHexString(error)
                );
            }
        }
    }
}
