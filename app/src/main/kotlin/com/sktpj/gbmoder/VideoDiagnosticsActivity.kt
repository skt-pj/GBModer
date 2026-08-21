package com.sktpj.gbmoder

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text as MaterialText
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.util.Locale

class VideoDiagnosticsActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val options = MediaFileConverter.Options(
            intent.getStringExtra(MediaConversionActivity.EXTRA_MODE),
            intent.getStringExtra(MediaConversionActivity.EXTRA_RESOLUTION),
            intent.getIntExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, 6),
            intent.getIntExtra(MediaConversionActivity.EXTRA_CONTRAST, 122),
            intent.getBooleanExtra(MediaConversionActivity.EXTRA_DITHER, true),
        )

        setContent {
            GbModerTheme(this) {
                VideoDiagnosticsScreen(options = options, onClose = ::finish)
            }
        }
    }
}

@Composable
private fun VideoDiagnosticsScreen(
    options: MediaFileConverter.Options,
    onClose: () -> Unit,
) {
    val context = LocalContext.current
    var running by remember { mutableStateOf(false) }
    var progress by remember { mutableIntStateOf(0) }
    var stage by remember { mutableStateOf("") }
    var sourceName by remember { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<VideoPipelineDiagnostics.Result?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var reportText by remember { mutableStateOf<String?>(null) }
    var logStatus by remember { mutableStateOf<String?>(null) }

    val reportExporter = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("text/plain"),
    ) { uri ->
        val text = reportText
        if (uri != null && text != null) {
            runCatching {
                context.contentResolver.openOutputStream(uri, "wt")?.bufferedWriter()?.use { it.write(text) }
            }.onSuccess {
                logStatus = context.getString(R.string.diag_report_saved)
            }.onFailure {
                logStatus = context.getString(R.string.diag_report_save_failed, it.javaClass.simpleName)
            }
        }
    }

    val performanceLogExporter = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("text/plain"),
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        PerformanceLog.syncToUri(context, uri) { success, message ->
            logStatus = if (success) {
                context.getString(R.string.log_synced)
            } else {
                context.getString(R.string.log_sync_failed_format, message)
            }
        }
    }

    val sourceLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        sourceName = queryDiagnosticDisplayName(context, uri) ?: uri.lastPathSegment
        result = null
        error = null
        reportText = null
        logStatus = null
        running = true
        progress = 0
        stage = "metadata"

        Thread({
            try {
                val diagnosed = VideoPipelineDiagnostics.diagnose(
                    context,
                    uri,
                    options,
                ) { percent, currentStage ->
                    runOnMainThread(context as ComponentActivity) {
                        progress = percent
                        stage = currentStage
                    }
                }
                val report = buildDiagnosticReport(diagnosed, options, sourceName.orEmpty())
                runOnMainThread(context as ComponentActivity) {
                    result = diagnosed
                    reportText = report
                    running = false
                    progress = 100
                    stage = "done"
                }
            } catch (failure: Throwable) {
                runOnMainThread(context as ComponentActivity) {
                    error = failure.message ?: failure.javaClass.simpleName
                    running = false
                }
            }
        }, "GBModerVideoDiagnostics").start()
    }

    Scaffold(
        modifier = Modifier.fillMaxSize().testTag("video-diagnostics-screen"),
        contentWindowInsets = WindowInsets.safeDrawing,
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Spacer(Modifier.height(12.dp).testTag("diagnostics-top-quiet-zone"))

            MaterialText(
                text = stringResource(R.string.video_diagnostics_title),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold,
            )
            MaterialText(
                text = stringResource(R.string.video_diagnostics_description),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            FilledTonalButton(
                onClick = { sourceLauncher.launch(arrayOf("video/*")) },
                enabled = !running,
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 52.dp)
                    .testTag("diagnose-video"),
            ) {
                MaterialText(
                    if (sourceName == null) {
                        stringResource(R.string.diag_choose_video)
                    } else {
                        stringResource(R.string.diag_choose_another_video)
                    }
                )
            }

            sourceName?.let {
                MaterialText(
                    text = stringResource(R.string.diag_selected_video, it),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            if (running) {
                LinearProgressIndicator(
                    progress = { progress / 100f },
                    modifier = Modifier.fillMaxWidth(),
                )
                MaterialText(
                    text = stringResource(
                        R.string.diag_running_stage,
                        progress,
                        localizedStage(stage),
                    ),
                    style = MaterialTheme.typography.bodySmall,
                )
            }

            error?.let {
                OutlinedCard(modifier = Modifier.fillMaxWidth()) {
                    MaterialText(
                        text = stringResource(R.string.diag_failed, it),
                        modifier = Modifier.padding(16.dp),
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }

            result?.let { diagnosed ->
                DiagnosticResultCards(diagnosed)

                Button(
                    onClick = {
                        reportExporter.launch("gbmoder-video-diagnostics.txt")
                    },
                    modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp),
                ) {
                    MaterialText(stringResource(R.string.diag_export_report))
                }

                FilledTonalButton(
                    onClick = {
                        if (PerformanceLog.hasLog(context)) {
                            performanceLogExporter.launch("gbmoder-performance.log")
                        } else {
                            logStatus = context.getString(R.string.no_performance_log)
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 52.dp)
                        .testTag("sync-performance-log"),
                ) {
                    MaterialText(stringResource(R.string.diag_sync_performance_log))
                }
            }

            logStatus?.let {
                MaterialText(
                    text = it,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                TextButton(onClick = onClose, enabled = !running) {
                    MaterialText(stringResource(R.string.close))
                }
            }
        }
    }
}

@Composable
private fun DiagnosticResultCards(result: VideoPipelineDiagnostics.Result) {
    OutlinedCard(modifier = Modifier.fillMaxWidth().testTag("diagnostic-result")) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            MaterialText(
                text = stringResource(R.string.diag_source_and_fps),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            DiagnosticLine(
                stringResource(R.string.diag_source_size),
                "${result.sourceWidth}×${result.sourceHeight}",
            )
            DiagnosticLine(
                stringResource(R.string.diag_target_size),
                "${result.targetWidth}×${result.targetHeight}",
            )
            DiagnosticLine(
                stringResource(R.string.diag_source_pts_fps),
                formatDouble(result.sourcePtsFps),
            )
            DiagnosticLine(
                stringResource(R.string.diag_encoder_nominal_fps),
                result.converterNominalFps.toString(),
            )
            DiagnosticLine(
                stringResource(R.string.diag_vfr),
                if (result.variableFrameRate) stringResource(R.string.diag_yes) else stringResource(R.string.diag_no),
            )
            DiagnosticLine(
                stringResource(R.string.diag_pts_jitter),
                "${formatDouble(result.ptsJitterPercent)}%",
            )
            MaterialText(
                text = if (result.sourcePtsPreserved) {
                    stringResource(R.string.diag_pts_preserved)
                } else {
                    stringResource(R.string.diag_pts_not_preserved)
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }

    OutlinedCard(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            MaterialText(
                text = stringResource(R.string.diag_pipeline_comparison),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            MaterialText(
                text = stringResource(R.string.diag_full_path),
                style = MaterialTheme.typography.titleSmall,
            )
            TimingLines(
                decode = result.fullDecodeMs,
                resize = result.fullResizeMs,
                filter = result.fullFilterMs,
                yuv = result.fullYuvMs,
                total = result.fullTotalMs,
            )
            MaterialText(
                text = stringResource(R.string.diag_target_first_path),
                style = MaterialTheme.typography.titleSmall,
                modifier = Modifier.padding(top = 6.dp),
            )
            TimingLines(
                decode = result.scaledDecodeMs,
                resize = result.scaledResizeMs,
                filter = result.scaledFilterMs,
                yuv = result.scaledYuvMs,
                total = result.scaledTotalMs,
            )
            DiagnosticLine(
                stringResource(R.string.diag_speedup),
                "×${formatDouble(result.targetFirstSpeedup)}",
            )
            DiagnosticLine(
                stringResource(R.string.diag_estimated_fps),
                formatDouble(theoreticalFps(result.scaledTotalMs)),
            )
            MaterialText(
                text = stringResource(
                    R.string.diag_dominant_stage,
                    localizedStage(result.dominantCpuStage),
                ),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }

    OutlinedCard(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            MaterialText(
                text = stringResource(R.string.diag_gpu),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            DiagnosticLine(stringResource(R.string.diag_decoder), result.decoderName.ifBlank { "-" })
            DiagnosticLine(stringResource(R.string.diag_encoder), result.encoderName.ifBlank { "-" })
            DiagnosticLine(
                stringResource(R.string.diag_decoder_hw),
                yesNo(result.decoderHardwareAccelerated),
            )
            DiagnosticLine(
                stringResource(R.string.diag_encoder_hw),
                yesNo(result.encoderHardwareAccelerated),
            )
            DiagnosticLine(
                stringResource(R.string.diag_surface_input),
                yesNo(result.surfaceEncoderSupported),
            )
            DiagnosticLine(
                stringResource(R.string.diag_gpu_candidate),
                yesNo(result.gpuPipelineCandidate),
            )
            MaterialText(
                text = if (result.gpuPipelineCandidate) {
                    stringResource(R.string.diag_gpu_path_available)
                } else {
                    stringResource(R.string.diag_gpu_path_unavailable)
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (result.gbcExactPaletteNeedsGlobalPass) {
                MaterialText(
                    text = stringResource(R.string.diag_gbc_gpu_caveat),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }

    OutlinedCard(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            MaterialText(
                text = stringResource(R.string.diag_conclusion),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            if (result.targetFirstSpeedup > 1.10) {
                MaterialText(stringResource(R.string.diag_conclusion_target_first, formatDouble(result.targetFirstSpeedup)))
            } else {
                MaterialText(stringResource(R.string.diag_conclusion_target_first_small))
            }
            if (result.gpuPipelineCandidate) {
                MaterialText(stringResource(R.string.diag_conclusion_gpu))
            }
            MaterialText(
                if (result.variableFrameRate) {
                    stringResource(R.string.diag_conclusion_vfr)
                } else {
                    stringResource(R.string.diag_conclusion_cfr)
                }
            )
        }
    }
}

@Composable
private fun TimingLines(
    decode: Double,
    resize: Double,
    filter: Double,
    yuv: Double,
    total: Double,
) {
    DiagnosticLine(stringResource(R.string.diag_decode_ms), "${formatDouble(decode)} ms")
    DiagnosticLine(stringResource(R.string.diag_resize_ms), "${formatDouble(resize)} ms")
    DiagnosticLine(stringResource(R.string.diag_filter_ms), "${formatDouble(filter)} ms")
    DiagnosticLine(stringResource(R.string.diag_yuv_ms), "${formatDouble(yuv)} ms")
    DiagnosticLine(stringResource(R.string.diag_total_ms), "${formatDouble(total)} ms")
}

@Composable
private fun DiagnosticLine(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth()) {
        MaterialText(
            text = label,
            modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.bodyMedium,
        )
        MaterialText(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun yesNo(value: Boolean): String =
    if (value) stringResource(R.string.diag_yes) else stringResource(R.string.diag_no)

@Composable
private fun localizedStage(stage: String): String = when (stage) {
    "metadata" -> stringResource(R.string.diag_stage_metadata)
    "codec-capabilities" -> stringResource(R.string.diag_stage_codec)
    "full-resolution-path" -> stringResource(R.string.diag_stage_full)
    "target-first-path" -> stringResource(R.string.diag_stage_target_first)
    "resize" -> stringResource(R.string.diag_stage_resize)
    "filter" -> stringResource(R.string.diag_stage_filter)
    "yuv" -> stringResource(R.string.diag_stage_yuv)
    "decode" -> stringResource(R.string.diag_stage_decode)
    else -> stringResource(R.string.diag_stage_done)
}

private fun theoreticalFps(totalMs: Double): Double = if (totalMs > 0.0) 1000.0 / totalMs else 0.0

private fun formatDouble(value: Double): String = String.format(Locale.US, "%.2f", value)

private fun buildDiagnosticReport(
    result: VideoPipelineDiagnostics.Result,
    options: MediaFileConverter.Options,
    sourceName: String,
): String = buildString {
    appendLine("GBModer video diagnostics")
    appendLine("source=$sourceName")
    appendLine("mode=${options.mode} resolution=${options.resolution} brightness=${options.brightness} contrast=${options.contrast} dither=${options.dither}")
    appendLine("sourceSize=${result.sourceWidth}x${result.sourceHeight} targetSize=${result.targetWidth}x${result.targetHeight}")
    appendLine("sourceMime=${result.sourceMime} durationMs=${result.durationMs}")
    appendLine("sourcePtsFps=${formatDouble(result.sourcePtsFps)} nominalEncoderFps=${result.converterNominalFps} variableFrameRate=${result.variableFrameRate} ptsJitterPercent=${formatDouble(result.ptsJitterPercent)} sourcePtsPreserved=${result.sourcePtsPreserved}")
    appendLine("full.decodeMs=${formatDouble(result.fullDecodeMs)} full.resizeMs=${formatDouble(result.fullResizeMs)} full.filterMs=${formatDouble(result.fullFilterMs)} full.yuvMs=${formatDouble(result.fullYuvMs)} full.totalMs=${formatDouble(result.fullTotalMs)}")
    appendLine("targetFirst.decodeMs=${formatDouble(result.scaledDecodeMs)} targetFirst.resizeMs=${formatDouble(result.scaledResizeMs)} targetFirst.filterMs=${formatDouble(result.scaledFilterMs)} targetFirst.yuvMs=${formatDouble(result.scaledYuvMs)} targetFirst.totalMs=${formatDouble(result.scaledTotalMs)} speedup=${formatDouble(result.targetFirstSpeedup)}")
    appendLine("decoder=${result.decoderName} decoderHardware=${result.decoderHardwareAccelerated}")
    appendLine("encoder=${result.encoderName} encoderHardware=${result.encoderHardwareAccelerated} surfaceInput=${result.surfaceEncoderSupported}")
    appendLine("openGlEs2=${result.openGlEs2Supported} gpuPipelineCandidate=${result.gpuPipelineCandidate} gbcGlobalPalettePass=${result.gbcExactPaletteNeedsGlobalPass}")
    appendLine("dominantCpuStage=${result.dominantCpuStage} benchmarkSamples=${result.benchmarkSamples}")
}

private fun queryDiagnosticDisplayName(context: android.content.Context, uri: Uri): String? =
    runCatching {
        context.contentResolver.query(
            uri,
            arrayOf(android.provider.OpenableColumns.DISPLAY_NAME),
            null,
            null,
            null,
        )?.use { cursor ->
            if (!cursor.moveToFirst()) return@use null
            val index = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
            if (index < 0) null else cursor.getString(index)
        }
    }.getOrNull()

private fun runOnMainThread(activity: ComponentActivity, block: () -> Unit) {
    activity.runOnUiThread(block)
}
