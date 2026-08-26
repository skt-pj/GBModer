#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_video_pipeline_v031.py <generated_src_root>")

root = Path(sys.argv[1]) / "com/sktpj/gbmoder"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)

# Diagnostics entry: keep the existing Compose button/test tag but route it to the comparison screen.
main_path = root / "MainActivity.java"
main = main_path.read_text()
main = replace_once(
    main,
    '''            @Override
            public void onLogSync() {
                beginLogSync();
            }
''',
    '''            @Override
            public void onLogSync() {
                Intent diagnostics = new Intent(MainActivity.this, VideoDiagnosticsActivity.class);
                diagnostics.putExtra(MediaConversionActivity.EXTRA_MODE, getSelectedMode());
                diagnostics.putExtra(MediaConversionActivity.EXTRA_RESOLUTION, getSelectedResolution());
                diagnostics.putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, getBrightness());
                diagnostics.putExtra(MediaConversionActivity.EXTRA_CONTRAST, getContrast());
                diagnostics.putExtra(MediaConversionActivity.EXTRA_DITHER, isUiDitherEnabled());
                startActivity(diagnostics);
            }
''',
    "diagnostics entry",
)
main_path.write_text(main)

converter_path = root / "MediaFileConverter.java"
converter = converter_path.read_text()
method_start = converter.find("    public static void convertVideo(\n")
method_end = converter.find("\n    public static void convertModel(\n", method_start)
if method_start < 0 or method_end < 0:
    raise SystemExit("convertVideo method markers not found")

optimized_method = r'''    public static void convertVideo(
            Context context,
            Uri source,
            Uri output,
            Options options,
            Progress progress
    ) throws Exception {
        MediaMetadataRetriever retriever = new MediaMetadataRetriever();
        MediaCodec encoder = null;
        MediaExtractor timingExtractor = null;
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

            timingExtractor = new MediaExtractor();
            timingExtractor.setDataSource(context, source, null);
            int sourceVideoTrack = findVideoTrack(timingExtractor);
            if (sourceVideoTrack < 0) throw new IOException("動画トラックを読み取れません");
            timingExtractor.selectTrack(sourceVideoTrack);
            long firstVideoTimeUs = timingExtractor.getSampleTime();
            if (firstVideoTimeUs < 0L) firstVideoTimeUs = 0L;

            firstFrame = retriever.getFrameAtTime(firstVideoTimeUs, MediaMetadataRetriever.OPTION_CLOSEST_SYNC);
            if (firstFrame == null) {
                firstFrame = retriever.getFrameAtTime(firstVideoTimeUs, MediaMetadataRetriever.OPTION_CLOSEST);
            }
            if (firstFrame == null) throw new IOException("動画フレームを読み取れません");

            int targetWidth = makeEven(GameBoyFilter.getTargetWidth(options.resolution, firstFrame.getWidth()));
            int targetHeight = makeEven(GameBoyFilter.getTargetHeight(options.resolution, firstFrame.getHeight()));
            int fps = determineFrameRate(retriever, durationUs);
            int totalFrames = determineFrameCount(retriever, durationUs, fps);

            notifyProgress(progress, 2, "動画エンコーダーを準備しています");
            encoder = MediaCodec.createEncoderByType(VIDEO_MIME);
            int colorFormat = chooseYuv420ColorFormat(encoder.getCodecInfo().getCapabilitiesForType(VIDEO_MIME));
            MediaFormat videoFormat = MediaFormat.createVideoFormat(VIDEO_MIME, targetWidth, targetHeight);
            videoFormat.setInteger(MediaFormat.KEY_COLOR_FORMAT, colorFormat);
            // This is a nominal encoder rate-control hint. Actual frame presentation timestamps below
            // are taken from the source track so VFR/CFR timing is not regenerated from this value.
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

            int frameIndex = 0;
            long lastPresentationTimeUs = -1L;
            while (true) {
                long sourceTimeUs = timingExtractor.getSampleTime();
                if (sourceTimeUs < 0L) break;

                // MediaMuxer requires monotonically increasing presentation timestamps. Normal
                // source tracks already satisfy this; clamp only pathological/regressing samples.
                long presentationTimeUs = lastPresentationTimeUs < 0L
                        ? Math.max(0L, sourceTimeUs)
                        : Math.max(lastPresentationTimeUs + 1L, sourceTimeUs);

                Bitmap sourceFrame;
                if (frameIndex == 0 && firstFrame != null) {
                    sourceFrame = firstFrame;
                    firstFrame = null;
                } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
                    // Decode at the final working size before the CPU filter. Android explicitly
                    // recommends getScaledFrameAtTime when full-resolution pixels are unnecessary.
                    sourceFrame = retriever.getScaledFrameAtTime(
                            sourceTimeUs,
                            MediaMetadataRetriever.OPTION_CLOSEST,
                            targetWidth,
                            targetHeight
                    );
                } else {
                    sourceFrame = retriever.getFrameAtTime(
                            sourceTimeUs,
                            MediaMetadataRetriever.OPTION_CLOSEST
                    );
                }

                if (sourceFrame != null) {
                    Bitmap filtered = null;
                    try {
                        filtered = prepareFilteredBitmap(
                                sourceFrame,
                                options,
                                false,
                                targetWidth,
                                targetHeight
                        );
                        byte[] yuv = bitmapToYuv420(filtered, colorFormat);
                        queueVideoInput(
                                encoder,
                                yuv,
                                presentationTimeUs,
                                muxerState,
                                bufferInfo
                        );
                        lastPresentationTimeUs = presentationTimeUs;
                        frameIndex++;
                    } finally {
                        if (filtered != null && filtered != sourceFrame && !filtered.isRecycled()) {
                            filtered.recycle();
                        }
                        if (!sourceFrame.isRecycled()) {
                            sourceFrame.recycle();
                        }
                    }
                }

                int percent = 5 + (int) Math.round(frameIndex * 80.0 / Math.max(1, totalFrames));
                notifyProgress(
                        progress,
                        Math.min(85, percent),
                        "動画を変換しています " + frameIndex + "/" + totalFrames
                );

                if (!timingExtractor.advance()) break;
            }

            if (frameIndex <= 0 || lastPresentationTimeUs < 0L) {
                throw new IOException("変換できる動画フレームがありません");
            }

            queueVideoEndOfStream(
                    encoder,
                    Math.max(lastPresentationTimeUs + 1L, durationUs),
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

            PerformanceLog.log(
                    "video_conversion_complete"
                            + " source_pts=true"
                            + " target_first=" + (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1)
                            + " target=" + targetWidth + "x" + targetHeight
                            + " nominal_fps=" + fps
                            + " frames=" + frameIndex
            );
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
            if (timingExtractor != null) {
                try {
                    timingExtractor.release();
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
'''

converter = converter[:method_start] + optimized_method + converter[method_end:]

frame_rate_marker = '''    private static int chooseYuv420ColorFormat(MediaCodecInfo.CodecCapabilities capabilities) throws IOException {
'''
helpers = r'''    private static int determineFrameCount(
            MediaMetadataRetriever retriever,
            long durationUs,
            int nominalFps
    ) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            long metadataCount = parseLong(retriever.extractMetadata(
                    MediaMetadataRetriever.METADATA_KEY_VIDEO_FRAME_COUNT
            ), 0L);
            if (metadataCount > 0L && metadataCount <= Integer.MAX_VALUE) {
                return (int) metadataCount;
            }
        }
        return Math.max(
                1,
                (int) Math.ceil((durationUs / 1_000_000.0) * Math.max(1, nominalFps))
        );
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

'''
if frame_rate_marker not in converter:
    raise SystemExit("video helper insertion marker not found")
converter = converter.replace(frame_rate_marker, helpers + frame_rate_marker, 1)
converter_path.write_text(converter)

print("v0.1.31 video PTS and target-size-first conversion applied")
