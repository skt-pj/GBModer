package com.sktpj.gbmoder

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.database.Cursor
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.annotation.DrawableRes
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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.util.Locale

class MediaConversionActivity : ComponentActivity() {
    companion object {
        const val EXTRA_KIND = "kind"
        const val EXTRA_MODE = "mode"
        const val EXTRA_RESOLUTION = "resolution"
        const val EXTRA_BRIGHTNESS = "brightness"
        const val EXTRA_CONTRAST = "contrast"
        const val EXTRA_DITHER = "dither"

        const val KIND_PHOTO = "photo"
        const val KIND_VIDEO = "video"
        const val KIND_MODEL = "model"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val kind = intent.getStringExtra(EXTRA_KIND)
        if (kind != KIND_PHOTO && kind != KIND_VIDEO && kind != KIND_MODEL) {
            finish()
            return
        }

        val options = MediaFileConverter.Options(
            intent.getStringExtra(EXTRA_MODE),
            intent.getStringExtra(EXTRA_RESOLUTION),
            intent.getIntExtra(EXTRA_BRIGHTNESS, 6),
            intent.getIntExtra(EXTRA_CONTRAST, 122),
            intent.getBooleanExtra(EXTRA_DITHER, true),
        )

        setContent {
            GbModerTheme(this) {
                MediaConversionScreen(
                    kind = kind,
                    options = options,
                    onClose = ::finish,
                )
            }
        }
    }
}

@Composable
private fun MediaConversionScreen(
    kind: String,
    options: MediaFileConverter.Options,
    onClose: () -> Unit,
) {
    val context = LocalContext.current
    val mainHandler = remember { Handler(Looper.getMainLooper()) }

    var sourceUriText by rememberSaveable { mutableStateOf<String?>(null) }
    var sourceName by rememberSaveable { mutableStateOf<String?>(null) }
    var modelExtension by rememberSaveable { mutableStateOf("") }
    var status by rememberSaveable { mutableStateOf("変換元ファイルを選択してください") }
    var running by rememberSaveable { mutableStateOf(false) }
    var progress by rememberSaveable { mutableIntStateOf(0) }
    var progressVisible by rememberSaveable { mutableStateOf(false) }

    fun startConversion(outputUri: Uri) {
        val sourceUri = sourceUriText?.let(Uri::parse) ?: return
        val currentSourceName = sourceName ?: defaultInputName(kind)
        running = true
        progress = 0
        progressVisible = true
        status = "変換中: $currentSourceName"

        Thread({
            try {
                val progressCallback = MediaFileConverter.Progress { percent, message ->
                    mainHandler.post {
                        progress = percent.coerceIn(0, 100)
                        if (!message.isNullOrBlank()) {
                            status = message
                        }
                    }
                }

                when (kind) {
                    MediaConversionActivity.KIND_PHOTO -> MediaFileConverter.convertPhoto(
                        context,
                        sourceUri,
                        outputUri,
                        options,
                        progressCallback,
                    )

                    MediaConversionActivity.KIND_VIDEO -> MediaFileConverter.convertVideo(
                        context,
                        sourceUri,
                        outputUri,
                        options,
                        progressCallback,
                    )

                    else -> MediaFileConverter.convertModel(
                        context,
                        sourceUri,
                        outputUri,
                        modelExtension,
                        options,
                        progressCallback,
                    )
                }

                mainHandler.post {
                    progress = 100
                    status = "保存しました: ${buildOutputName(currentSourceName, kind, modelExtension)}"
                    running = false
                }
            } catch (error: Throwable) {
                mainHandler.post {
                    progressVisible = false
                    status = "変換できませんでした: ${error.message ?: error.javaClass.simpleName}"
                    running = false
                }
            }
        }, "GBModerFileConversion").start()
    }

    val outputLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        val outputUri = if (result.resultCode == Activity.RESULT_OK) result.data?.data else null
        if (outputUri == null) {
            status = "保存先は未選択です"
        } else {
            startConversion(outputUri)
        }
    }

    val sourceLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument(),
    ) { uri ->
        if (uri == null) {
            status = "変換元ファイルは未選択です"
            return@rememberLauncherForActivityResult
        }

        val name = queryDisplayName(context, uri).orEmpty().ifBlank { defaultInputName(kind) }
        val extension = if (kind == MediaConversionActivity.KIND_MODEL) extensionOf(name) else ""
        if (kind == MediaConversionActivity.KIND_MODEL && !MediaFileConverter.isSupportedModelExtension(extension)) {
            sourceUriText = null
            sourceName = null
            modelExtension = ""
            status = "3Dモデルは .ply / .obj / .gltf / .glb に対応しています"
            return@rememberLauncherForActivityResult
        }

        sourceUriText = uri.toString()
        sourceName = name
        modelExtension = extension
        progressVisible = false
        progress = 0
        status = "選択済み: $name"
    }

    Scaffold(
        modifier = Modifier.fillMaxSize().testTag("media-conversion-scaffold"),
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
            Spacer(Modifier.height(12.dp).testTag("media-top-quiet-zone"))

            Surface(
                shape = RoundedCornerShape(20.dp),
                color = MaterialTheme.colorScheme.secondaryContainer,
            ) {
                Icon(
                    painter = painterResource(kindIcon(kind)),
                    contentDescription = null,
                    modifier = Modifier.padding(16.dp).size(36.dp),
                    tint = MaterialTheme.colorScheme.onSecondaryContainer,
                )
            }

            Text(
                text = kindTitle(kind),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = kindDescription(kind),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            OutlinedCard(modifier = Modifier.fillMaxWidth().testTag("source-file-card")) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text("変換元", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Text(
                        text = sourceName ?: "未選択",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (sourceName == null) {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        } else {
                            MaterialTheme.colorScheme.onSurface
                        },
                    )
                    FilledTonalButton(
                        onClick = { sourceLauncher.launch(inputMimeTypes(kind)) },
                        enabled = !running,
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = 52.dp)
                            .testTag("choose-source"),
                    ) {
                        Icon(
                            painter = painterResource(R.drawable.ic_folder_open_24),
                            contentDescription = null,
                            modifier = Modifier.size(ButtonDefaults.IconSize),
                        )
                        Spacer(Modifier.width(ButtonDefaults.IconSpacing))
                        Text(if (sourceName == null) "ファイルを選択" else "ファイルを選び直す")
                    }
                }
            }

            if (sourceUriText != null) {
                Button(
                    onClick = {
                        val name = sourceName ?: defaultInputName(kind)
                        val outputIntent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                            addCategory(Intent.CATEGORY_OPENABLE)
                            type = outputMimeType(kind, modelExtension)
                            putExtra(
                                Intent.EXTRA_TITLE,
                                buildOutputName(name, kind, modelExtension),
                            )
                        }
                        status = "保存先を選択してください"
                        outputLauncher.launch(outputIntent)
                    },
                    enabled = !running,
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 56.dp)
                        .testTag("choose-output-and-convert"),
                ) {
                    Icon(
                        painter = painterResource(R.drawable.ic_save_24),
                        contentDescription = null,
                        modifier = Modifier.size(ButtonDefaults.IconSize),
                    )
                    Spacer(Modifier.width(ButtonDefaults.IconSpacing))
                    Text("保存先を選んで変換")
                }
            }

            if (progressVisible) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    LinearProgressIndicator(
                        progress = { progress / 100f },
                        modifier = Modifier.fillMaxWidth().testTag("conversion-progress"),
                    )
                    Text("$progress%", style = MaterialTheme.typography.labelMedium)
                }
            }

            Surface(
                modifier = Modifier.fillMaxWidth().testTag("conversion-status"),
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surfaceContainer,
            ) {
                Text(
                    text = status,
                    modifier = Modifier.padding(14.dp),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                TextButton(
                    onClick = onClose,
                    enabled = !running,
                    modifier = Modifier.heightIn(min = 48.dp).testTag("close-conversion"),
                ) {
                    Text("閉じる")
                }
            }

            Spacer(Modifier.height(12.dp))
        }
    }
}

private fun inputMimeTypes(kind: String): Array<String> = when (kind) {
    MediaConversionActivity.KIND_PHOTO -> arrayOf("image/*")
    MediaConversionActivity.KIND_VIDEO -> arrayOf("video/*")
    else -> arrayOf(
        "model/gltf+json",
        "model/gltf-binary",
        "application/octet-stream",
        "text/plain",
    )
}

private fun kindTitle(kind: String): String = when (kind) {
    MediaConversionActivity.KIND_PHOTO -> "写真を変換"
    MediaConversionActivity.KIND_VIDEO -> "動画を変換"
    else -> "3Dモデルを変換"
}

private fun kindDescription(kind: String): String = when (kind) {
    MediaConversionActivity.KIND_PHOTO -> "現在の表示設定を適用し、PNGとして保存します。"
    MediaConversionActivity.KIND_VIDEO -> "現在の表示設定を適用し、MP4として保存します。"
    else -> "現在の表示設定を色へ適用します。対応形式: PLY / OBJ / glTF / GLB。"
}

@DrawableRes
private fun kindIcon(kind: String): Int = when (kind) {
    MediaConversionActivity.KIND_PHOTO -> R.drawable.ic_photo_24
    MediaConversionActivity.KIND_VIDEO -> R.drawable.ic_video_24
    else -> R.drawable.ic_3d_model_24
}

private fun defaultInputName(kind: String): String = when (kind) {
    MediaConversionActivity.KIND_PHOTO -> "image"
    MediaConversionActivity.KIND_VIDEO -> "video"
    else -> "model.gltf"
}

private fun buildOutputName(sourceName: String, kind: String, modelExtension: String): String {
    var base = sourceName
    val dot = base.lastIndexOf('.')
    if (dot > 0) {
        base = base.substring(0, dot)
    }
    return when (kind) {
        MediaConversionActivity.KIND_PHOTO -> "$base-gbmoder.png"
        MediaConversionActivity.KIND_VIDEO -> "$base-gbmoder.mp4"
        else -> "$base-gbmoder.$modelExtension"
    }
}

private fun outputMimeType(kind: String, modelExtension: String): String = when (kind) {
    MediaConversionActivity.KIND_PHOTO -> "image/png"
    MediaConversionActivity.KIND_VIDEO -> "video/mp4"
    else -> when (modelExtension) {
        "gltf" -> "model/gltf+json"
        "glb" -> "model/gltf-binary"
        "obj" -> "text/plain"
        else -> "application/octet-stream"
    }
}

private fun queryDisplayName(context: Context, uri: Uri): String? {
    try {
        context.contentResolver.query(
            uri,
            arrayOf(OpenableColumns.DISPLAY_NAME),
            null,
            null,
            null,
        )?.use { cursor: Cursor ->
            if (cursor.moveToFirst()) {
                val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (index >= 0) {
                    return cursor.getString(index)
                }
            }
        }
    } catch (_: Throwable) {
    }
    return null
}

private fun extensionOf(name: String): String {
    val dot = name.lastIndexOf('.')
    if (dot < 0 || dot == name.length - 1) return ""
    return name.substring(dot + 1).lowercase(Locale.ROOT)
}
