package com.sktpj.gbmoder;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.media.MediaMetadataRetriever;
import android.media.MediaMuxer;
import android.net.Uri;
import android.os.Build;
import android.os.ParcelFileDescriptor;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class MediaFileConverter {
    private static final String VIDEO_MIME = "video/avc";
    private static final long CODEC_TIMEOUT_US = 20_000L;
    private static final int GLB_MAGIC = 0x46546C67;
    private static final int GLB_JSON_CHUNK = 0x4E4F534A;

    public interface Progress {
        void onProgress(int percent, String message);
    }

    public static final class Options {
        public final String mode;
        public final String resolution;
        public final int brightness;
        public final int contrast;
        public final boolean dither;

        public Options(String mode, String resolution, int brightness, int contrast, boolean dither) {
            this.mode = safeMode(mode);
            this.resolution = GameBoyFilter.safeResolution(resolution);
            this.brightness = brightness;
            this.contrast = contrast;
            this.dither = dither;
        }
    }

    private MediaFileConverter() {
    }

    public static boolean isSupportedModelExtension(String extension) {
        return "ply".equals(extension)
                || "obj".equals(extension)
                || "gltf".equals(extension)
                || "glb".equals(extension);
    }

    public static void convertPhoto(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
        notifyProgress(progress, 5, "写真を読み込んでいます");
        Bitmap sourceBitmap;
        try (InputStream input = context.getContentResolver().openInputStream(source)) {
            if (input == null) throw new IOException("写真を開けません");
            sourceBitmap = BitmapFactory.decodeStream(input);
        }
        if (sourceBitmap == null) throw new IOException("画像形式を読み取れません");

        Bitmap converted = null;
        try {
            notifyProgress(progress, 35, "写真を変換しています");
            converted = prepareFilteredBitmap(sourceBitmap, options, true);
            notifyProgress(progress, 80, "写真を書き出しています");
            try (OutputStream stream = context.getContentResolver().openOutputStream(output, "w")) {
                if (stream == null) throw new IOException("保存先を開けません");
                if (!converted.compress(Bitmap.CompressFormat.PNG, 100, stream)) {
                    throw new IOException("PNGの書き出しに失敗しました");
                }
            }
            notifyProgress(progress, 100, "写真を保存しました");
        } finally {
            if (converted != null && converted != sourceBitmap && !converted.isRecycled()) {
                converted.recycle();
            }
            if (!sourceBitmap.isRecycled()) {
                sourceBitmap.recycle();
            }
        }
    }

    public static void convertVideo(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
        MediaMetadataRetriever retriever = new MediaMetadataRetriever();
        MediaCodec encoder = null;
        MediaExtractor audioExtractor = null;
        MediaMuxer muxer = null;
        ParcelFileDescriptor outputFd = null;
        Bitmap firstFrame = null;

        try {
            retriever.setDataSource(context, source);
            long durationUs = parseLong(retriever.extractMetadata(
                    MediaMetadataRetriever.METADATA_KEY_DURATION
            ), 0L) * 1000L;
            if (durationUs <= 0L) throw new IOException("動画の長さを取得できません");

            firstFrame = retriever.getFrameAtTime(0L, MediaMetadataRetriever.OPTION_CLOSEST_SYNC);
            if (firstFrame == null) {
                firstFrame = retriever.getFrameAtTime(0L, MediaMetadataRetriever.OPTION_CLOSEST);
            }
            if (firstFrame == null) throw new IOException("動画フレームを読み取れません");

            int targetWidth = makeEven(GameBoyFilter.getTargetWidth(options.resolution, firstFrame.getWidth()));
            int targetHeight = makeEven(GameBoyFilter.getTargetHeight(options.resolution, firstFrame.getHeight()));
            int fps = determineFrameRate(retriever, durationUs);
            long frameDurationUs = Math.max(1L, 1_000_000L / fps);
            int totalFrames = Math.max(1, (int) Math.ceil(durationUs / (double) frameDurationUs));

            notifyProgress(progress, 2, "動画エンコーダーを準備しています");
            encoder = MediaCodec.createEncoderByType(VIDEO_MIME);
            int colorFormat = chooseYuv420ColorFormat(encoder.getCodecInfo().getCapabilitiesForType(VIDEO_MIME));
            MediaFormat videoFormat = MediaFormat.createVideoFormat(VIDEO_MIME, targetWidth, targetHeight);
            videoFormat.setInteger(MediaFormat.KEY_COLOR_FORMAT, colorFormat);
            videoFormat.setInteger(MediaFormat.KEY_FRAME_RATE, fps);
            videoFormat.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1);
            videoFormat.setInteger(
                    MediaFormat.KEY_BIT_RATE,
                    Math.max(300_000, Math.min(12_000_000, targetWidth * targetHeight * fps * 2))
            );
            encoder.configure(videoFormat, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE);

            outputFd = context.getContentResolver().openFileDescriptor(output, "rwt");
            if (outputFd == null) throw new IOException("動画の保存先を開けません");
            muxer = new MediaMuxer(outputFd.getFileDescriptor(), MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);

            audioExtractor = new MediaExtractor();
            audioExtractor.setDataSource(context, source, null);
            int sourceAudioTrack = findAacAudioTrack(audioExtractor);
            int muxerAudioTrack = -1;
            if (sourceAudioTrack >= 0) {
                audioExtractor.selectTrack(sourceAudioTrack);
                muxerAudioTrack = muxer.addTrack(audioExtractor.getTrackFormat(sourceAudioTrack));
            }

            VideoMuxerState muxerState = new VideoMuxerState(muxer, muxerAudioTrack);
            MediaCodec.BufferInfo bufferInfo = new MediaCodec.BufferInfo();
            encoder.start();

            for (int frameIndex = 0; frameIndex < totalFrames; frameIndex++) {
                long timeUs = Math.min(durationUs - 1L, frameIndex * frameDurationUs);
                Bitmap sourceFrame;
                if (frameIndex == 0 && firstFrame != null) {
                    sourceFrame = firstFrame;
                    firstFrame = null;
                } else {
                    sourceFrame = retriever.getFrameAtTime(timeUs, MediaMetadataRetriever.OPTION_CLOSEST);
                }
                if (sourceFrame == null) {
                    continue;
                }

                Bitmap filtered = null;
                try {
                    filtered = prepareFilteredBitmap(sourceFrame, options, false, targetWidth, targetHeight);
                    byte[] yuv = bitmapToYuv420(filtered, colorFormat);
                    queueVideoInput(encoder, yuv, timeUs, muxerState, bufferInfo);
                } finally {
                    if (filtered != null && filtered != sourceFrame && !filtered.isRecycled()) {
                        filtered.recycle();
                    }
                    if (!sourceFrame.isRecycled()) {
                        sourceFrame.recycle();
                    }
                }

                int percent = 5 + (int) Math.round((frameIndex + 1) * 80.0 / totalFrames);
                notifyProgress(progress, Math.min(85, percent), "動画を変換しています " + (frameIndex + 1) + "/" + totalFrames);
            }

            queueVideoEndOfStream(
                    encoder,
                    Math.max(0L, durationUs),
                    muxerState,
                    bufferInfo
            );

            if (!muxerState.started) {
                throw new IOException("動画トラックを生成できません");
            }

            if (sourceAudioTrack >= 0 && muxerState.audioTrack >= 0) {
                notifyProgress(progress, 90, "音声を保持しています");
                copyAudioTrack(audioExtractor, muxerState.muxer, muxerState.audioTrack, durationUs);
            }

            notifyProgress(progress, 100, "動画を保存しました");
        } finally {
            if (firstFrame != null && !firstFrame.isRecycled()) firstFrame.recycle();
            try {
                retriever.release();
            } catch (Throwable ignored) {
            }
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
            if (audioExtractor != null) {
                try {
                    audioExtractor.release();
                } catch (Throwable ignored) {
                }
            }
            if (muxer != null) {
                try {
                    muxer.stop();
                } catch (Throwable ignored) {
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

    public static void convertModel(
            Context context,
            Uri source,
            Uri output,
            String extension,
            Options options,
            Progress progress
    ) throws Exception {
        String ext = extension == null ? "" : extension.toLowerCase(Locale.ROOT);
        notifyProgress(progress, 5, "3Dモデルを読み込んでいます");
        if ("ply".equals(ext)) {
            convertAsciiPly(context, source, output, options, progress);
        } else if ("obj".equals(ext)) {
            convertObj(context, source, output, options, progress);
        } else if ("gltf".equals(ext)) {
            convertGltf(context, source, output, options, progress);
        } else if ("glb".equals(ext)) {
            convertGlb(context, source, output, options, progress);
        } else {
            throw new IOException("未対応の3Dモデル形式です");
        }
        notifyProgress(progress, 100, "3Dモデルを保存しました");
    }

    private static Bitmap prepareFilteredBitmap(Bitmap source, Options options, boolean deriveTargetSize) {
        int width = deriveTargetSize
                ? GameBoyFilter.getTargetWidth(options.resolution, source.getWidth())
                : source.getWidth();
        int height = deriveTargetSize
                ? GameBoyFilter.getTargetHeight(options.resolution, source.getHeight())
                : source.getHeight();
        return prepareFilteredBitmap(source, options, false, width, height);
    }

    private static Bitmap prepareFilteredBitmap(
            Bitmap source,
            Options options,
            boolean ignored,
            int targetWidth,
            int targetHeight
    ) {
        Bitmap scaled = Bitmap.createScaledBitmap(
                source,
                Math.max(1, targetWidth),
                Math.max(1, targetHeight),
                false
        );
        if (scaled == source) {
            scaled = source.copy(Bitmap.Config.ARGB_8888, true);
        } else if (scaled.getConfig() != Bitmap.Config.ARGB_8888 || !scaled.isMutable()) {
            Bitmap mutable = scaled.copy(Bitmap.Config.ARGB_8888, true);
            scaled.recycle();
            scaled = mutable;
        }
        if (scaled == null) throw new IllegalStateException("変換用Bitmapを作成できません");
        GameBoyFilter.apply(scaled, options.mode, options.brightness, options.contrast, options.dither);
        return scaled;
    }

    private static int determineFrameRate(MediaMetadataRetriever retriever, long durationUs) {
        float frameRate = parseFloat(retriever.extractMetadata(
                MediaMetadataRetriever.METADATA_KEY_CAPTURE_FRAMERATE
        ), 0f);
        if (frameRate <= 0f && Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            long frameCount = parseLong(retriever.extractMetadata(
                    MediaMetadataRetriever.METADATA_KEY_VIDEO_FRAME_COUNT
            ), 0L);
            if (frameCount > 0 && durationUs > 0) {
                frameRate = (float) (frameCount * 1_000_000.0 / durationUs);
            }
        }
        if (frameRate <= 0f) frameRate = 30f;
        return Math.max(1, Math.min(60, Math.round(frameRate)));
    }

    private static int chooseYuv420ColorFormat(MediaCodecInfo.CodecCapabilities capabilities) throws IOException {
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
        throw new IOException("端末のH.264エンコーダーがYUV420入力に対応していません");
    }

    private static void queueVideoInput(
            MediaCodec encoder,
            byte[] data,
            long presentationTimeUs,
            VideoMuxerState state,
            MediaCodec.BufferInfo info
    ) throws IOException {
        while (true) {
            int inputIndex = encoder.dequeueInputBuffer(CODEC_TIMEOUT_US);
            if (inputIndex >= 0) {
                ByteBuffer inputBuffer = encoder.getInputBuffer(inputIndex);
                if (inputBuffer == null || inputBuffer.capacity() < data.length) {
                    throw new IOException("動画エンコーダーの入力バッファが不足しています");
                }
                inputBuffer.clear();
                inputBuffer.put(data);
                encoder.queueInputBuffer(inputIndex, 0, data.length, presentationTimeUs, 0);
                break;
            }
            drainEncoder(encoder, state, info, false);
        }
        drainEncoder(encoder, state, info, false);
    }

    private static void queueVideoEndOfStream(
            MediaCodec encoder,
            long presentationTimeUs,
            VideoMuxerState state,
            MediaCodec.BufferInfo info
    ) throws IOException {
        while (true) {
            int inputIndex = encoder.dequeueInputBuffer(CODEC_TIMEOUT_US);
            if (inputIndex >= 0) {
                encoder.queueInputBuffer(
                        inputIndex,
                        0,
                        0,
                        presentationTimeUs,
                        MediaCodec.BUFFER_FLAG_END_OF_STREAM
                );
                break;
            }
            drainEncoder(encoder, state, info, false);
        }
        while (!drainEncoder(encoder, state, info, true)) {
            // Continue until encoder EOS is observed.
        }
    }

    private static boolean drainEncoder(
            MediaCodec encoder,
            VideoMuxerState state,
            MediaCodec.BufferInfo info,
            boolean waitForEos
    ) throws IOException {
        while (true) {
            int outputIndex = encoder.dequeueOutputBuffer(info, waitForEos ? CODEC_TIMEOUT_US : 0L);
            if (outputIndex == MediaCodec.INFO_TRY_AGAIN_LATER) {
                return false;
            }
            if (outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                if (state.videoTrack >= 0) throw new IOException("動画出力形式が複数回変更されました");
                state.videoTrack = state.muxer.addTrack(encoder.getOutputFormat());
                state.muxer.start();
                state.started = true;
                continue;
            }
            if (outputIndex < 0) {
                continue;
            }

            ByteBuffer outputBuffer = encoder.getOutputBuffer(outputIndex);
            if (outputBuffer == null) throw new IOException("動画エンコーダーの出力バッファを取得できません");

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
            boolean eos = (info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0;
            encoder.releaseOutputBuffer(outputIndex, false);
            if (eos) return true;
        }
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

    private static void copyAudioTrack(
            MediaExtractor extractor,
            MediaMuxer muxer,
            int muxerTrack,
            long durationUs
    ) throws IOException {
        extractor.seekTo(0L, MediaExtractor.SEEK_TO_CLOSEST_SYNC);
        MediaFormat format = extractor.getTrackFormat(extractor.getSampleTrackIndex() >= 0
                ? extractor.getSampleTrackIndex()
                : 0);
        int maxInput = format.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)
                ? Math.max(64 * 1024, format.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE))
                : 1024 * 1024;
        ByteBuffer buffer = ByteBuffer.allocateDirect(maxInput);
        MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
        while (true) {
            buffer.clear();
            int size = extractor.readSampleData(buffer, 0);
            if (size < 0) break;
            long sampleTime = extractor.getSampleTime();
            if (sampleTime < 0 || sampleTime > durationUs) break;
            info.set(0, size, sampleTime, extractor.getSampleFlags());
            buffer.position(0);
            buffer.limit(size);
            muxer.writeSampleData(muxerTrack, buffer, info);
            if (!extractor.advance()) break;
        }
    }

    private static byte[] bitmapToYuv420(Bitmap bitmap, int colorFormat) {
        int width = bitmap.getWidth();
        int height = bitmap.getHeight();
        int[] pixels = new int[width * height];
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height);

        int frameSize = width * height;
        byte[] yuv = new byte[frameSize * 3 / 2];
        boolean semiPlanar = colorFormat == MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar;
        int yIndex = 0;
        int uIndex = frameSize;
        int vIndex = frameSize + frameSize / 4;
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
                    if (semiPlanar) {
                        yuv[uvIndex++] = (byte) uu;
                        yuv[uvIndex++] = (byte) vv;
                    } else {
                        yuv[uIndex++] = (byte) uu;
                        yuv[vIndex++] = (byte) vv;
                    }
                }
            }
        }
        return yuv;
    }

    private static void convertAsciiPly(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
        List<String> lines = new ArrayList<>();
        try (InputStream input = context.getContentResolver().openInputStream(source);
             BufferedReader reader = new BufferedReader(new InputStreamReader(requireInput(input), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) lines.add(line);
        }
        if (lines.isEmpty() || !"ply".equals(lines.get(0).trim())) throw new IOException("PLYヘッダーがありません");

        int headerEnd = -1;
        int vertexCount = -1;
        boolean vertexElement = false;
        List<String> propertyNames = new ArrayList<>();
        List<String> propertyTypes = new ArrayList<>();
        for (int i = 1; i < lines.size(); i++) {
            String line = lines.get(i).trim();
            if (line.startsWith("format ") && !line.startsWith("format ascii")) {
                throw new IOException("PLYはASCII形式に対応しています");
            }
            if (line.startsWith("element ")) {
                String[] parts = line.split("\\s+");
                vertexElement = parts.length >= 3 && "vertex".equals(parts[1]);
                if (vertexElement) {
                    vertexCount = Integer.parseInt(parts[2]);
                    propertyNames.clear();
                    propertyTypes.clear();
                }
            } else if (vertexElement && line.startsWith("property ")) {
                String[] parts = line.split("\\s+");
                if (parts.length >= 3 && !"list".equals(parts[1])) {
                    propertyTypes.add(parts[1]);
                    propertyNames.add(parts[2].toLowerCase(Locale.ROOT));
                }
            }
            if ("end_header".equals(line)) {
                headerEnd = i;
                break;
            }
        }
        if (headerEnd < 0 || vertexCount < 0) throw new IOException("PLYのvertex定義を読み取れません");
        int rIndex = findProperty(propertyNames, "red", "r");
        int gIndex = findProperty(propertyNames, "green", "g");
        int bIndex = findProperty(propertyNames, "blue", "b");
        if (rIndex < 0 || gIndex < 0 || bIndex < 0) {
            throw new IOException("PLYに頂点色(red/green/blue)がありません");
        }
        if (headerEnd + vertexCount >= lines.size() + 1) throw new IOException("PLYの頂点データが不足しています");

        for (int vertex = 0; vertex < vertexCount; vertex++) {
            int lineIndex = headerEnd + 1 + vertex;
            String[] values = lines.get(lineIndex).trim().split("\\s+");
            int maxIndex = Math.max(rIndex, Math.max(gIndex, bIndex));
            if (values.length <= maxIndex) throw new IOException("PLYの頂点色を読み取れません");
            boolean normalized = isFloatingType(propertyTypes.get(rIndex))
                    && Math.abs(Double.parseDouble(values[rIndex])) <= 1.0001
                    && Math.abs(Double.parseDouble(values[gIndex])) <= 1.0001
                    && Math.abs(Double.parseDouble(values[bIndex])) <= 1.0001;
            int r = parseColor(values[rIndex], normalized);
            int g = parseColor(values[gIndex], normalized);
            int b = parseColor(values[bIndex], normalized);
            int transformed = transformColor(r, g, b, options);
            values[rIndex] = formatColor(Color.red(transformed), propertyTypes.get(rIndex), normalized);
            values[gIndex] = formatColor(Color.green(transformed), propertyTypes.get(gIndex), normalized);
            values[bIndex] = formatColor(Color.blue(transformed), propertyTypes.get(bIndex), normalized);
            lines.set(lineIndex, join(values));
            if ((vertex & 1023) == 0) {
                notifyProgress(progress, 10 + (int) (75L * vertex / Math.max(1, vertexCount)), "PLY頂点色を変換しています");
            }
        }

        try (OutputStream outputStream = context.getContentResolver().openOutputStream(output, "w");
             BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(requireOutput(outputStream), StandardCharsets.UTF_8))) {
            for (String line : lines) {
                writer.write(line);
                writer.newLine();
            }
        }
        notifyProgress(progress, 90, "PLYを書き出しました");
    }

    private static void convertObj(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
        List<String> lines = new ArrayList<>();
        int changed = 0;
        try (InputStream input = context.getContentResolver().openInputStream(source);
             BufferedReader reader = new BufferedReader(new InputStreamReader(requireInput(input), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                String trimmed = line.trim();
                if (trimmed.startsWith("v ")) {
                    String[] tokens = trimmed.split("\\s+");
                    if (tokens.length >= 7) {
                        int colorStart = tokens.length >= 8 ? tokens.length - 3 : 4;
                        if (colorStart + 2 < tokens.length) {
                            double rv = Double.parseDouble(tokens[colorStart]);
                            double gv = Double.parseDouble(tokens[colorStart + 1]);
                            double bv = Double.parseDouble(tokens[colorStart + 2]);
                            boolean normalized = Math.abs(rv) <= 1.0001 && Math.abs(gv) <= 1.0001 && Math.abs(bv) <= 1.0001;
                            int transformed = transformColor(
                                    normalized ? toByte(rv) : clampInt((int) Math.round(rv), 0, 255),
                                    normalized ? toByte(gv) : clampInt((int) Math.round(gv), 0, 255),
                                    normalized ? toByte(bv) : clampInt((int) Math.round(bv), 0, 255),
                                    options
                            );
                            tokens[colorStart] = normalized ? formatUnit(Color.red(transformed)) : Integer.toString(Color.red(transformed));
                            tokens[colorStart + 1] = normalized ? formatUnit(Color.green(transformed)) : Integer.toString(Color.green(transformed));
                            tokens[colorStart + 2] = normalized ? formatUnit(Color.blue(transformed)) : Integer.toString(Color.blue(transformed));
                            line = join(tokens);
                            changed++;
                        }
                    }
                }
                lines.add(line);
            }
        }
        if (changed == 0) throw new IOException("OBJに頂点色がありません");
        notifyProgress(progress, 75, "OBJ頂点色を変換しました");
        try (OutputStream stream = context.getContentResolver().openOutputStream(output, "w");
             BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(requireOutput(stream), StandardCharsets.UTF_8))) {
            for (String line : lines) {
                writer.write(line);
                writer.newLine();
            }
        }
        notifyProgress(progress, 90, "OBJを書き出しました");
    }

    private static void convertGltf(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
        byte[] data = readAll(context, source);
        JSONObject root = new JSONObject(new String(data, StandardCharsets.UTF_8));
        int changed = transformGltfRoot(root, options, true);
        if (changed == 0) {
            throw new IOException("glTFに変換可能なマテリアル色または埋込テクスチャがありません");
        }
        notifyProgress(progress, 80, "glTFの色と埋込テクスチャを変換しました");
        writeAll(context, output, root.toString().getBytes(StandardCharsets.UTF_8));
        notifyProgress(progress, 90, "glTFを書き出しました");
    }

    private static void convertGlb(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
        byte[] sourceBytes = readAll(context, source);
        if (sourceBytes.length < 20) throw new IOException("GLBファイルが短すぎます");
        ByteBuffer buffer = ByteBuffer.wrap(sourceBytes).order(ByteOrder.LITTLE_ENDIAN);
        int magic = buffer.getInt();
        int version = buffer.getInt();
        int declaredLength = buffer.getInt();
        if (magic != GLB_MAGIC || version != 2 || declaredLength > sourceBytes.length) {
            throw new IOException("GLB 2.0形式ではありません");
        }

        List<GlbChunk> chunks = new ArrayList<>();
        while (buffer.remaining() >= 8) {
            int length = buffer.getInt();
            int type = buffer.getInt();
            if (length < 0 || length > buffer.remaining()) throw new IOException("GLBチャンクが壊れています");
            byte[] bytes = new byte[length];
            buffer.get(bytes);
            chunks.add(new GlbChunk(type, bytes));
        }
        if (chunks.isEmpty() || chunks.get(0).type != GLB_JSON_CHUNK) {
            throw new IOException("GLB JSONチャンクがありません");
        }

        String jsonText = new String(chunks.get(0).data, StandardCharsets.UTF_8)
                .replace("\u0000", "")
                .trim();
        JSONObject root = new JSONObject(jsonText);
        int changed = transformGltfRoot(root, options, false);
        if (changed == 0) throw new IOException("GLBに変換可能なマテリアル色がありません");
        chunks.set(0, new GlbChunk(GLB_JSON_CHUNK, root.toString().getBytes(StandardCharsets.UTF_8)));

        ByteArrayOutputStream body = new ByteArrayOutputStream();
        for (GlbChunk chunk : chunks) {
            int paddedLength = (chunk.data.length + 3) & ~3;
            writeLeInt(body, paddedLength);
            writeLeInt(body, chunk.type);
            body.write(chunk.data);
            byte pad = chunk.type == GLB_JSON_CHUNK ? (byte) 0x20 : 0;
            for (int i = chunk.data.length; i < paddedLength; i++) body.write(pad);
        }
        byte[] bodyBytes = body.toByteArray();
        ByteArrayOutputStream glb = new ByteArrayOutputStream(12 + bodyBytes.length);
        writeLeInt(glb, GLB_MAGIC);
        writeLeInt(glb, 2);
        writeLeInt(glb, 12 + bodyBytes.length);
        glb.write(bodyBytes);
        writeAll(context, output, glb.toByteArray());
        notifyProgress(progress, 90, "GLBマテリアル色を書き出しました");
    }

    private static int transformGltfRoot(JSONObject root, Options options, boolean transformDataImages) throws Exception {
        int changed = 0;
        JSONArray materials = root.optJSONArray("materials");
        if (materials != null) {
            for (int i = 0; i < materials.length(); i++) {
                JSONObject material = materials.optJSONObject(i);
                if (material == null) continue;
                JSONObject pbr = material.optJSONObject("pbrMetallicRoughness");
                if (pbr != null) {
                    JSONArray base = pbr.optJSONArray("baseColorFactor");
                    if (transformColorFactor(base, options)) changed++;
                }
                JSONArray emissive = material.optJSONArray("emissiveFactor");
                if (transformColorFactor(emissive, options)) changed++;
            }
        }

        if (transformDataImages) {
            JSONArray images = root.optJSONArray("images");
            if (images != null) {
                for (int i = 0; i < images.length(); i++) {
                    JSONObject image = images.optJSONObject(i);
                    if (image == null) continue;
                    String uri = image.optString("uri", "");
                    int comma = uri.indexOf(',');
                    if (!uri.startsWith("data:image/") || comma < 0 || !uri.substring(0, comma).contains(";base64")) {
                        continue;
                    }
                    byte[] decoded = Base64.decode(uri.substring(comma + 1), Base64.DEFAULT);
                    Bitmap bitmap = BitmapFactory.decodeByteArray(decoded, 0, decoded.length);
                    if (bitmap == null) continue;
                    Bitmap mutable = bitmap.getConfig() == Bitmap.Config.ARGB_8888 && bitmap.isMutable()
                            ? bitmap
                            : bitmap.copy(Bitmap.Config.ARGB_8888, true);
                    if (mutable != bitmap) bitmap.recycle();
                    try {
                        GameBoyFilter.apply(mutable, options.mode, options.brightness, options.contrast, options.dither);
                        ByteArrayOutputStream png = new ByteArrayOutputStream();
                        if (!mutable.compress(Bitmap.CompressFormat.PNG, 100, png)) continue;
                        image.put("uri", "data:image/png;base64," + Base64.encodeToString(png.toByteArray(), Base64.NO_WRAP));
                        changed++;
                    } finally {
                        mutable.recycle();
                    }
                }
            }
        }
        return changed;
    }

    private static boolean transformColorFactor(JSONArray factor, Options options) throws Exception {
        if (factor == null || factor.length() < 3) return false;
        int color = transformColor(
                toByte(factor.optDouble(0, 0.0)),
                toByte(factor.optDouble(1, 0.0)),
                toByte(factor.optDouble(2, 0.0)),
                options
        );
        factor.put(0, Color.red(color) / 255.0);
        factor.put(1, Color.green(color) / 255.0);
        factor.put(2, Color.blue(color) / 255.0);
        return true;
    }

    private static int transformColor(int r, int g, int b, Options options) {
        float contrast = options.contrast / 100.0f;
        if (GameBoyFilter.MODE_GB.equals(options.mode)) {
            float lum = (0.299f * r) + (0.587f * g) + (0.114f * b);
            lum = clamp(((lum - 128f) * contrast) + 128f + options.brightness, 0f, 255f);
            int palette = clampInt(3 - (int) Math.floor(lum / 64f), 0, 3);
            int[][] colors = {
                    {155, 188, 15},
                    {139, 172, 15},
                    {48, 98, 48},
                    {15, 56, 15}
            };
            return Color.rgb(colors[palette][0], colors[palette][1], colors[palette][2]);
        }

        float rr = ((r - 128f) * contrast) + 128f + options.brightness;
        float gg = ((g - 128f) * contrast) + 128f + options.brightness;
        float bb = ((b - 128f) * contrast) + 128f + options.brightness;
        int levels = GameBoyFilter.MODE_DS.equals(options.mode) ? 63 : 31;
        return Color.rgb(
                quantize(rr, levels),
                quantize(gg, levels),
                quantize(bb, levels)
        );
    }

    private static int quantize(float value, int levels) {
        float clamped = clamp(value, 0f, 255f);
        int q = Math.round((clamped / 255f) * levels);
        return Math.round((q / (float) levels) * 255f);
    }

    private static String safeMode(String mode) {
        if (GameBoyFilter.MODE_GBC.equals(mode)) return GameBoyFilter.MODE_GBC;
        if (GameBoyFilter.MODE_GBA.equals(mode)) return GameBoyFilter.MODE_GBA;
        if (GameBoyFilter.MODE_DS.equals(mode)) return GameBoyFilter.MODE_DS;
        return GameBoyFilter.MODE_GB;
    }

    private static int findProperty(List<String> names, String first, String second) {
        int index = names.indexOf(first);
        return index >= 0 ? index : names.indexOf(second);
    }

    private static boolean isFloatingType(String type) {
        return "float".equals(type)
                || "float32".equals(type)
                || "double".equals(type)
                || "float64".equals(type);
    }

    private static int parseColor(String value, boolean normalized) {
        double parsed = Double.parseDouble(value);
        return normalized ? toByte(parsed) : clampInt((int) Math.round(parsed), 0, 255);
    }

    private static String formatColor(int value, String type, boolean normalized) {
        if (normalized || isFloatingType(type)) {
            if (normalized) return formatUnit(value);
            return String.format(Locale.US, "%.6f", (double) value);
        }
        return Integer.toString(value);
    }

    private static String formatUnit(int value) {
        return String.format(Locale.US, "%.6f", value / 255.0);
    }

    private static int toByte(double unit) {
        return clampInt((int) Math.round(unit * 255.0), 0, 255);
    }

    private static String join(String[] values) {
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < values.length; i++) {
            if (i > 0) builder.append(' ');
            builder.append(values[i]);
        }
        return builder.toString();
    }

    private static int makeEven(int value) {
        int safe = Math.max(2, value);
        return (safe & 1) == 0 ? safe : safe - 1;
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

    private static float clamp(float value, float min, float max) {
        return Math.max(min, Math.min(max, value));
    }

    private static InputStream requireInput(InputStream stream) throws IOException {
        if (stream == null) throw new IOException("入力ファイルを開けません");
        return stream;
    }

    private static OutputStream requireOutput(OutputStream stream) throws IOException {
        if (stream == null) throw new IOException("出力ファイルを開けません");
        return stream;
    }

    private static byte[] readAll(Context context, Uri source) throws IOException {
        try (InputStream stream = context.getContentResolver().openInputStream(source)) {
            InputStream input = requireInput(stream);
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            byte[] buffer = new byte[64 * 1024];
            int read;
            while ((read = input.read(buffer)) >= 0) {
                if (read > 0) output.write(buffer, 0, read);
            }
            return output.toByteArray();
        }
    }

    private static void writeAll(Context context, Uri output, byte[] data) throws IOException {
        try (OutputStream stream = context.getContentResolver().openOutputStream(output, "w")) {
            OutputStream target = requireOutput(stream);
            target.write(data);
            target.flush();
        }
    }

    private static void writeLeInt(ByteArrayOutputStream output, int value) {
        output.write(value & 0xFF);
        output.write((value >>> 8) & 0xFF);
        output.write((value >>> 16) & 0xFF);
        output.write((value >>> 24) & 0xFF);
    }

    private static void notifyProgress(Progress progress, int percent, String message) {
        if (progress != null) progress.onProgress(percent, message);
    }

    private static final class VideoMuxerState {
        final MediaMuxer muxer;
        final int audioTrack;
        int videoTrack = -1;
        boolean started = false;

        VideoMuxerState(MediaMuxer muxer, int audioTrack) {
            this.muxer = muxer;
            this.audioTrack = audioTrack;
        }
    }

    private static final class GlbChunk {
        final int type;
        final byte[] data;

        GlbChunk(int type, byte[] data) {
            this.type = type;
            this.data = data;
        }
    }
}
