package com.sktpj.gbmoder;

import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaFormat;
import android.os.SystemClock;

import java.nio.ByteBuffer;

public final class VideoEncoderDiagnostics {
    private static final String VIDEO_MIME = "video/avc";
    private static final long TIMEOUT_US = 20_000L;
    private static final int WARMUP_FRAMES = 2;
    private static final int MEASURE_FRAMES = 8;

    private VideoEncoderDiagnostics() {
    }

    public static double measure(int width, int height, int fps) throws Exception {
        MediaCodec encoder = null;
        try {
            encoder = MediaCodec.createEncoderByType(VIDEO_MIME);
            int colorFormat = chooseColorFormat(
                    encoder.getCodecInfo().getCapabilitiesForType(VIDEO_MIME)
            );
            MediaFormat format = MediaFormat.createVideoFormat(
                    VIDEO_MIME,
                    makeEven(width),
                    makeEven(height)
            );
            format.setInteger(MediaFormat.KEY_COLOR_FORMAT, colorFormat);
            format.setInteger(MediaFormat.KEY_BIT_RATE, Math.max(300_000, width * height * Math.max(1, fps) * 2));
            format.setInteger(MediaFormat.KEY_FRAME_RATE, Math.max(1, fps));
            format.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1);
            encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE);
            encoder.start();

            int bytesPerFrame = makeEven(width) * makeEven(height) * 3 / 2;
            byte[] black = new byte[bytesPerFrame];
            MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
            long frameDurationUs = Math.max(1L, 1_000_000L / Math.max(1, fps));
            long measuredNs = 0L;
            int measured = 0;
            int total = WARMUP_FRAMES + MEASURE_FRAMES;

            for (int frame = 0; frame < total; frame++) {
                long started = SystemClock.elapsedRealtimeNanos();
                queueFrame(encoder, black, frame * frameDurationUs, info);
                long elapsed = SystemClock.elapsedRealtimeNanos() - started;
                if (frame >= WARMUP_FRAMES) {
                    measuredNs += elapsed;
                    measured++;
                }
            }
            queueEos(encoder, total * frameDurationUs, info);
            return measured > 0 ? (measuredNs / 1_000_000.0) / measured : 0.0;
        } finally {
            if (encoder != null) {
                try {
                    encoder.stop();
                } catch (Throwable ignored) {
                }
                try {
                    encoder.release();
                } catch (Throwable ignored) {
                }
            }
        }
    }

    private static void queueFrame(
            MediaCodec encoder,
            byte[] data,
            long ptsUs,
            MediaCodec.BufferInfo info
    ) throws Exception {
        while (true) {
            int index = encoder.dequeueInputBuffer(TIMEOUT_US);
            if (index >= 0) {
                ByteBuffer buffer = encoder.getInputBuffer(index);
                if (buffer == null || buffer.capacity() < data.length) {
                    throw new IllegalStateException("Encoder input buffer is too small");
                }
                buffer.clear();
                buffer.put(data);
                encoder.queueInputBuffer(index, 0, data.length, ptsUs, 0);
                break;
            }
            drain(encoder, info, false);
        }
        drain(encoder, info, false);
    }

    private static void queueEos(
            MediaCodec encoder,
            long ptsUs,
            MediaCodec.BufferInfo info
    ) throws Exception {
        while (true) {
            int index = encoder.dequeueInputBuffer(TIMEOUT_US);
            if (index >= 0) {
                encoder.queueInputBuffer(index, 0, 0, ptsUs, MediaCodec.BUFFER_FLAG_END_OF_STREAM);
                break;
            }
            drain(encoder, info, false);
        }
        while (!drain(encoder, info, true)) {
            // Drain until EOS.
        }
    }

    private static boolean drain(
            MediaCodec encoder,
            MediaCodec.BufferInfo info,
            boolean wait
    ) {
        while (true) {
            int index = encoder.dequeueOutputBuffer(info, wait ? TIMEOUT_US : 0L);
            if (index == MediaCodec.INFO_TRY_AGAIN_LATER) return false;
            if (index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) continue;
            if (index < 0) continue;
            boolean eos = (info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0;
            encoder.releaseOutputBuffer(index, false);
            if (eos) return true;
            if (!wait) return false;
        }
    }

    private static int chooseColorFormat(MediaCodecInfo.CodecCapabilities capabilities) {
        int flexible = -1;
        int planar = -1;
        int semiPlanar = -1;
        for (int value : capabilities.colorFormats) {
            if (value == MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible) flexible = value;
            if (value == MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Planar) planar = value;
            if (value == MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar) semiPlanar = value;
        }
        if (semiPlanar >= 0) return semiPlanar;
        if (planar >= 0) return planar;
        if (flexible >= 0) return flexible;
        throw new IllegalStateException("No YUV420 encoder input format");
    }

    private static int makeEven(int value) {
        int safe = Math.max(2, value);
        return (safe & 1) == 0 ? safe : safe - 1;
    }
}
