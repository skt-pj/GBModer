package com.sktpj.gbmoder;

import android.app.ActivityManager;
import android.content.Context;
import android.content.pm.ConfigurationInfo;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.media.MediaCodecInfo;
import android.media.MediaCodecList;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.media.MediaMetadataRetriever;
import android.net.Uri;
import android.os.Build;
import android.os.SystemClock;

import java.util.ArrayList;
import java.util.List;

public final class VideoPipelineDiagnostics {
    private static final String VIDEO_MIME = "video/avc";
    private static final int SAMPLE_FRAMES = 6;
    private static final int MAX_PTS_SAMPLES = 6000;

    public interface Progress {
        void onProgress(int percent, String stage);
    }

    public static final class Result {
        public String sourceMime = "";
        public String decoderName = "";
        public String encoderName = "";
        public int sourceWidth;
        public int sourceHeight;
        public int targetWidth;
        public int targetHeight;
        public long durationMs;
        public int ptsSamples;
        public double sourcePtsFps;
        public int converterNominalFps;
        public boolean variableFrameRate;
        public double ptsJitterPercent;
        public boolean sourcePtsPreserved = true;

        public double fullDecodeMs;
        public double fullResizeMs;
        public double fullFilterMs;
        public double fullYuvMs;
        public double fullTotalMs;

        public double scaledDecodeMs;
        public double scaledResizeMs;
        public double scaledFilterMs;
        public double scaledYuvMs;
        public double scaledTotalMs;
        public double targetFirstSpeedup;

        public boolean scaledDecodeSupported;
        public boolean surfaceEncoderSupported;
        public boolean decoderHardwareAccelerated;
        public boolean encoderHardwareAccelerated;
        public boolean openGlEs2Supported;
        public boolean gpuPipelineCandidate;
        public boolean gbcExactPaletteNeedsGlobalPass;
        public String dominantCpuStage = "";
        public int benchmarkSamples;
    }

    private VideoPipelineDiagnostics() {
    }

    public static Result diagnose(
            Context context,
            Uri source,
            MediaFileConverter.Options options,
            Progress progress
    ) throws Exception {
        Result result = new Result();
        progress(progress, 2, "metadata");

        MediaMetadataRetriever metadata = new MediaMetadataRetriever();
        MediaExtractor extractor = new MediaExtractor();
        MediaFormat sourceVideoFormat = null;
        try {
            metadata.setDataSource(context, source);
            extractor.setDataSource(context, source, null);
            int videoTrack = findVideoTrack(extractor);
            if (videoTrack < 0) {
                throw new IllegalArgumentException("No video track");
            }
            sourceVideoFormat = extractor.getTrackFormat(videoTrack);
            extractor.selectTrack(videoTrack);

            result.sourceMime = sourceVideoFormat.getString(MediaFormat.KEY_MIME);
            result.durationMs = parseLong(
                    metadata.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION),
                    0L
            );
            int width = parseInt(metadata.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH), 0);
            int height = parseInt(metadata.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT), 0);
            int rotation = parseInt(metadata.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION), 0);
            if ((rotation % 180) != 0) {
                int swap = width;
                width = height;
                height = swap;
            }

            if (width <= 0 || height <= 0) {
                Bitmap first = metadata.getFrameAtTime(0L, MediaMetadataRetriever.OPTION_CLOSEST_SYNC);
                if (first == null) throw new IllegalArgumentException("Could not decode a video frame");
                width = first.getWidth();
                height = first.getHeight();
                first.recycle();
            }

            result.sourceWidth = width;
            result.sourceHeight = height;
            result.targetWidth = makeEven(GameBoyFilter.getTargetWidth(options.resolution, width));
            result.targetHeight = makeEven(GameBoyFilter.getTargetHeight(options.resolution, height));
            result.scaledDecodeSupported = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1;
            result.gbcExactPaletteNeedsGlobalPass = GameBoyFilter.MODE_GBC.equals(options.mode);

            PtsStats pts = scanPts(extractor);
            result.ptsSamples = pts.samples;
            result.sourcePtsFps = pts.fps;
            result.variableFrameRate = pts.variable;
            result.ptsJitterPercent = pts.jitterPercent;
            result.converterNominalFps = determineNominalFrameRate(metadata, result.durationMs * 1000L);

            progress(progress, 12, "codec-capabilities");
            fillCodecCapabilities(context, sourceVideoFormat, result);
        } finally {
            try {
                extractor.release();
            } catch (Throwable ignored) {
            }
            try {
                metadata.release();
            } catch (Throwable ignored) {
            }
        }

        progress(progress, 20, "full-resolution-path");
        Benchmark full = benchmarkPath(context, source, options, result, false, progress, 20, 52);
        result.fullDecodeMs = full.decodeMs;
        result.fullResizeMs = full.resizeMs;
        result.fullFilterMs = full.filterMs;
        result.fullYuvMs = full.yuvMs;
        result.fullTotalMs = full.totalMs;
        result.benchmarkSamples = full.samples;

        progress(progress, 55, "target-first-path");
        Benchmark scaled = benchmarkPath(context, source, options, result, true, progress, 55, 90);
        result.scaledDecodeMs = scaled.decodeMs;
        result.scaledResizeMs = scaled.resizeMs;
        result.scaledFilterMs = scaled.filterMs;
        result.scaledYuvMs = scaled.yuvMs;
        result.scaledTotalMs = scaled.totalMs;
        result.benchmarkSamples = Math.min(result.benchmarkSamples, scaled.samples);
        if (result.scaledTotalMs > 0.0) {
            result.targetFirstSpeedup = result.fullTotalMs / result.scaledTotalMs;
        }
        result.dominantCpuStage = dominantStage(result);
        progress(progress, 100, "done");
        return result;
    }

    private static Benchmark benchmarkPath(
            Context context,
            Uri source,
            MediaFileConverter.Options options,
            Result result,
            boolean targetFirst,
            Progress progress,
            int startProgress,
            int endProgress
    ) throws Exception {
        MediaMetadataRetriever retriever = new MediaMetadataRetriever();
        retriever.setDataSource(context, source);
        long durationUs = Math.max(1L, result.durationMs * 1000L);
        List<Long> times = sampleTimes(durationUs);

        long decodeNs = 0L;
        long resizeNs = 0L;
        long filterNs = 0L;
        long yuvNs = 0L;
        int completed = 0;

        try {
            for (int i = 0; i < times.size(); i++) {
                long timeUs = times.get(i);
                Bitmap decoded = null;
                Bitmap target = null;
                try {
                    long started = SystemClock.elapsedRealtimeNanos();
                    if (targetFirst && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
                        decoded = retriever.getScaledFrameAtTime(
                                timeUs,
                                MediaMetadataRetriever.OPTION_CLOSEST,
                                result.targetWidth,
                                result.targetHeight
                        );
                    } else {
                        decoded = retriever.getFrameAtTime(timeUs, MediaMetadataRetriever.OPTION_CLOSEST);
                    }
                    decodeNs += SystemClock.elapsedRealtimeNanos() - started;
                    if (decoded == null) continue;

                    started = SystemClock.elapsedRealtimeNanos();
                    target = toTargetBitmap(decoded, result.targetWidth, result.targetHeight);
                    resizeNs += SystemClock.elapsedRealtimeNanos() - started;

                    started = SystemClock.elapsedRealtimeNanos();
                    GameBoyFilter.apply(
                            target,
                            options.mode,
                            options.brightness,
                            options.contrast,
                            options.dither
                    );
                    filterNs += SystemClock.elapsedRealtimeNanos() - started;

                    started = SystemClock.elapsedRealtimeNanos();
                    bitmapToYuv420Benchmark(target);
                    yuvNs += SystemClock.elapsedRealtimeNanos() - started;
                    completed++;
                } finally {
                    if (target != null && !target.isRecycled()) target.recycle();
                    if (decoded != null && decoded != target && !decoded.isRecycled()) decoded.recycle();
                }

                int span = Math.max(1, endProgress - startProgress);
                int percent = startProgress + (int) Math.round((i + 1) * span / (double) times.size());
                progress(progress, percent, targetFirst ? "target-first-path" : "full-resolution-path");
            }
        } finally {
            retriever.release();
        }

        Benchmark benchmark = new Benchmark();
        benchmark.samples = completed;
        if (completed > 0) {
            benchmark.decodeMs = nanosToMs(decodeNs) / completed;
            benchmark.resizeMs = nanosToMs(resizeNs) / completed;
            benchmark.filterMs = nanosToMs(filterNs) / completed;
            benchmark.yuvMs = nanosToMs(yuvNs) / completed;
            benchmark.totalMs = benchmark.decodeMs
                    + benchmark.resizeMs
                    + benchmark.filterMs
                    + benchmark.yuvMs;
        }
        return benchmark;
    }

    private static Bitmap toTargetBitmap(Bitmap source, int targetWidth, int targetHeight) {
        Bitmap scaled = Bitmap.createScaledBitmap(
                source,
                Math.max(1, targetWidth),
                Math.max(1, targetHeight),
                false
        );
        if (scaled == source) {
            return source.copy(Bitmap.Config.ARGB_8888, true);
        }
        if (scaled.getConfig() != Bitmap.Config.ARGB_8888 || !scaled.isMutable()) {
            Bitmap mutable = scaled.copy(Bitmap.Config.ARGB_8888, true);
            scaled.recycle();
            return mutable;
        }
        return scaled;
    }

    private static byte[] bitmapToYuv420Benchmark(Bitmap bitmap) {
        int width = bitmap.getWidth();
        int height = bitmap.getHeight();
        int[] pixels = new int[width * height];
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height);
        int frameSize = width * height;
        byte[] yuv = new byte[frameSize * 3 / 2];
        int yIndex = 0;
        int uvIndex = frameSize;
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int color = pixels[y * width + x];
                int r = Color.red(color);
                int g = Color.green(color);
                int b = Color.blue(color);
                int yy = clampInt(((66 * r + 129 * g + 25 * b + 128) >> 8) + 16, 0, 255);
                int uu = clampInt(((-38 * r - 74 * g + 112 * b + 128) >> 8) + 128, 0, 255);
                int vv = clampInt(((112 * r - 94 * g - 18 * b + 128) >> 8) + 128, 0, 255);
                yuv[yIndex++] = (byte) yy;
                if ((y & 1) == 0 && (x & 1) == 0) {
                    yuv[uvIndex++] = (byte) uu;
                    yuv[uvIndex++] = (byte) vv;
                }
            }
        }
        return yuv;
    }

    private static PtsStats scanPts(MediaExtractor extractor) {
        long previous = -1L;
        long minDelta = Long.MAX_VALUE;
        long maxDelta = 0L;
        double sum = 0.0;
        double sumSquares = 0.0;
        int deltas = 0;
        int samples = 0;

        while (samples < MAX_PTS_SAMPLES) {
            long timeUs = extractor.getSampleTime();
            if (timeUs < 0L) break;
            if (previous >= 0L && timeUs > previous) {
                long delta = timeUs - previous;
                minDelta = Math.min(minDelta, delta);
                maxDelta = Math.max(maxDelta, delta);
                sum += delta;
                sumSquares += (double) delta * delta;
                deltas++;
            }
            previous = timeUs;
            samples++;
            if (!extractor.advance()) break;
        }

        PtsStats stats = new PtsStats();
        stats.samples = samples;
        if (deltas > 0 && sum > 0.0) {
            double average = sum / deltas;
            double variance = Math.max(0.0, (sumSquares / deltas) - (average * average));
            double stddev = Math.sqrt(variance);
            stats.fps = 1_000_000.0 / average;
            stats.jitterPercent = average > 0.0 ? (stddev / average) * 100.0 : 0.0;
            double spread = average > 0.0 && minDelta != Long.MAX_VALUE
                    ? (maxDelta - minDelta) / average
                    : 0.0;
            stats.variable = stats.jitterPercent > 5.0 && spread > 0.10;
        }
        return stats;
    }

    private static void fillCodecCapabilities(Context context, MediaFormat sourceFormat, Result result) {
        MediaCodecList list = new MediaCodecList(MediaCodecList.REGULAR_CODECS);
        try {
            String decoder = list.findDecoderForFormat(sourceFormat);
            result.decoderName = decoder == null ? "" : decoder;
            MediaCodecInfo decoderInfo = findCodecInfo(list, decoder);
            if (decoderInfo != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                result.decoderHardwareAccelerated = decoderInfo.isHardwareAccelerated();
            }
        } catch (Throwable ignored) {
        }

        try {
            MediaFormat encoderFormat = MediaFormat.createVideoFormat(
                    VIDEO_MIME,
                    Math.max(2, result.targetWidth),
                    Math.max(2, result.targetHeight)
            );
            encoderFormat.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface);
            encoderFormat.setInteger(MediaFormat.KEY_BIT_RATE, Math.max(300_000, result.targetWidth * result.targetHeight * 4));
            encoderFormat.setInteger(MediaFormat.KEY_FRAME_RATE, Math.max(1, result.converterNominalFps));
            encoderFormat.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1);
            String encoder = list.findEncoderForFormat(encoderFormat);
            result.encoderName = encoder == null ? "" : encoder;
            MediaCodecInfo encoderInfo = findCodecInfo(list, encoder);
            if (encoderInfo != null) {
                MediaCodecInfo.CodecCapabilities caps = encoderInfo.getCapabilitiesForType(VIDEO_MIME);
                for (int format : caps.colorFormats) {
                    if (format == MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface) {
                        result.surfaceEncoderSupported = true;
                        break;
                    }
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    result.encoderHardwareAccelerated = encoderInfo.isHardwareAccelerated();
                }
            }
        } catch (Throwable ignored) {
        }

        try {
            ActivityManager manager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
            ConfigurationInfo info = manager == null ? null : manager.getDeviceConfigurationInfo();
            result.openGlEs2Supported = info != null && info.reqGlEsVersion >= 0x20000;
        } catch (Throwable ignored) {
        }
        result.gpuPipelineCandidate = result.openGlEs2Supported
                && result.surfaceEncoderSupported
                && !result.decoderName.isEmpty();
    }

    private static MediaCodecInfo findCodecInfo(MediaCodecList list, String name) {
        if (name == null || name.isEmpty()) return null;
        for (MediaCodecInfo info : list.getCodecInfos()) {
            if (name.equals(info.getName())) return info;
        }
        return null;
    }

    private static int findVideoTrack(MediaExtractor extractor) {
        for (int i = 0; i < extractor.getTrackCount(); i++) {
            MediaFormat format = extractor.getTrackFormat(i);
            String mime = format.getString(MediaFormat.KEY_MIME);
            if (mime != null && mime.startsWith("video/")) return i;
        }
        return -1;
    }

    private static int determineNominalFrameRate(MediaMetadataRetriever retriever, long durationUs) {
        float frameRate = parseFloat(
                retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_CAPTURE_FRAMERATE),
                0f
        );
        if (frameRate <= 0f && Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            long frameCount = parseLong(
                    retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_FRAME_COUNT),
                    0L
            );
            if (frameCount > 0L && durationUs > 0L) {
                frameRate = (float) (frameCount * 1_000_000.0 / durationUs);
            }
        }
        if (frameRate <= 0f) frameRate = 30f;
        return Math.max(1, Math.min(60, Math.round(frameRate)));
    }

    private static List<Long> sampleTimes(long durationUs) {
        List<Long> times = new ArrayList<>();
        if (SAMPLE_FRAMES <= 1) {
            times.add(0L);
            return times;
        }
        long end = Math.max(0L, durationUs - 1L);
        for (int i = 0; i < SAMPLE_FRAMES; i++) {
            times.add((long) Math.round(end * (i / (double) (SAMPLE_FRAMES - 1))));
        }
        return times;
    }

    private static String dominantStage(Result result) {
        double max = result.fullDecodeMs;
        String stage = "decode";
        if (result.fullResizeMs > max) {
            max = result.fullResizeMs;
            stage = "resize";
        }
        if (result.fullFilterMs > max) {
            max = result.fullFilterMs;
            stage = "filter";
        }
        if (result.fullYuvMs > max) {
            stage = "yuv";
        }
        return stage;
    }

    private static int makeEven(int value) {
        int safe = Math.max(2, value);
        return (safe & 1) == 0 ? safe : safe - 1;
    }

    private static double nanosToMs(long nanos) {
        return nanos / 1_000_000.0;
    }

    private static void progress(Progress callback, int percent, String stage) {
        if (callback != null) callback.onProgress(Math.max(0, Math.min(100, percent)), stage);
    }

    private static int parseInt(String value, int fallback) {
        if (value == null) return fallback;
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static long parseLong(String value, long fallback) {
        if (value == null) return fallback;
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static float parseFloat(String value, float fallback) {
        if (value == null) return fallback;
        try {
            return Float.parseFloat(value);
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static int clampInt(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    private static final class Benchmark {
        int samples;
        double decodeMs;
        double resizeMs;
        double filterMs;
        double yuvMs;
        double totalMs;
    }

    private static final class PtsStats {
        int samples;
        double fps;
        boolean variable;
        double jitterPercent;
    }
}
