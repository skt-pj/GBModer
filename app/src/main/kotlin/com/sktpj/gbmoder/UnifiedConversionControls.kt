package com.sktpj.gbmoder

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.database.Cursor
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.provider.OpenableColumns
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import java.util.Locale

private enum class ConversionKind {
    PHOTO,
    VIDEO,
    MODEL,
}

private data class ConversionSource(
    val uri: Uri,
    val name: String,
    val kind: ConversionKind,
    val extension: String,
)

@Composable
internal fun UnifiedConversionControls(
    options: MediaFileConverter.Options,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val mainHandler = remember { Handler(Looper.getMainLooper()) }

    var sourceUriText by rememberSaveable { mutableStateOf<String?>(null) }
    var sourceName by rememberSaveable { mutableStateOf<String?>(null) }
    var sourceKindName by rememberSaveable { mutableStateOf<String?>(null) }
    var sourceExtension by rememberSaveable { mutableStateOf("") }
    var outputUriText by rememberSaveable { mutableStateOf<String?>(null) }
    var outputName by rememberSaveable { mutableStateOf<String?>(null) }
    var running by rememberSaveable { mutableStateOf(false) }

    fun currentSource(): ConversionSource? {
        val uri = sourceUriText?.let(Uri::parse) ?: return null
        val name = sourceName ?: return null
        val kind = sourceKindName?.let { value ->
            runCatching { ConversionKind.valueOf(value) }.getOrNull()
        } ?: return null
        return ConversionSource(uri, name, kind, sourceExtension)
    }

    fun showMessage(message: String) {
        Toast.makeText(context, GbModerLocalization.localize(context, message), Toast.LENGTH_SHORT).show()
    }

    fun startConversion() {
        val source = currentSource() ?: return
        val output = outputUriText?.let(Uri::parse) ?: return
        if (running) return
        running = true

        Thread({
            try {
                val progressCallback = MediaFileConverter.Progress { _, _ -> }
                when (source.kind) {
                    ConversionKind.PHOTO -> MediaFileConverter.convertPhoto(
                        context,
                        source.uri,
                        output,
                        options,
                        progressCallback,
                    )

                    ConversionKind.VIDEO -> MediaFileConverter.convertVideo(
                        context,
                        source.uri,
                        output,
                        options,
                        progressCallback,
                    )

                    ConversionKind.MODEL -> MediaFileConverter.convertModel(
                        context,
                        source.uri,
                        output,
                        source.extension,
                        options,
                        progressCallback,
                    )
                }
                mainHandler.post {
                    running = false
                    showMessage("変換しました")
                }
            } catch (error: Throwable) {
                mainHandler.post {
                    running = false
                    showMessage("変換できませんでした: ${error.message ?: error.javaClass.simpleName}")
                }
            }
        }, "GBModerUnifiedConversion").start()
    }

    val outputLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        val uri = if (result.resultCode == Activity.RESULT_OK) result.data?.data else null
        if (uri != null) {
            outputUriText = uri.toString()
            outputName = queryConversionDisplayName(context, uri)
                ?: currentSource()?.let(::buildConversionOutputName)
        }
    }

    val sourceLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument(),
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult

        val name = queryConversionDisplayName(context, uri).orEmpty().ifBlank { "input" }
        val detected = detectConversionSource(context, uri, name)
        if (detected == null) {
            sourceUriText = null
            sourceName = null
            sourceKindName = null
            sourceExtension = ""
            outputUriText = null
            outputName = null
            showMessage("対応していないファイル形式です")
            return@rememberLauncherForActivityResult
        }

        sourceUriText = detected.uri.toString()
        sourceName = detected.name
        sourceKindName = detected.kind.name
        sourceExtension = detected.extension
        outputUriText = null
        outputName = null
    }

    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        FilledTonalButton(
            onClick = {
                sourceLauncher.launch(
                    arrayOf(
                        "image/*",
                        "video/*",
                        "model/gltf+json",
                        "model/gltf-binary",
                        "application/octet-stream",
                        "text/plain",
                    ),
                )
            },
            enabled = !running,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 52.dp)
                .testTag("conversion-source-select"),
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_folder_open_24),
                contentDescription = null,
                modifier = Modifier.size(ButtonDefaults.IconSize),
            )
            Spacer(Modifier.width(ButtonDefaults.IconSpacing))
            Text(sourceName ?: "対象ファイルを選択", modifier = Modifier.weight(1f))
        }

        OutlinedButton(
            onClick = {
                val source = currentSource() ?: return@OutlinedButton
                val outputIntent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = conversionOutputMimeType(source)
                    putExtra(Intent.EXTRA_TITLE, buildConversionOutputName(source))
                }
                outputLauncher.launch(outputIntent)
            },
            enabled = !running && currentSource() != null,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 52.dp)
                .testTag("conversion-output-select"),
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_save_24),
                contentDescription = null,
                modifier = Modifier.size(ButtonDefaults.IconSize),
            )
            Spacer(Modifier.width(ButtonDefaults.IconSpacing))
            Text(outputName ?: "出力先を選択", modifier = Modifier.weight(1f))
        }

        Button(
            onClick = ::startConversion,
            enabled = !running && currentSource() != null && outputUriText != null,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 56.dp)
                .testTag("conversion-run"),
        ) {
            Text("変換")
        }
    }
}

private fun detectConversionSource(context: Context, uri: Uri, name: String): ConversionSource? {
    val mime = runCatching { context.contentResolver.getType(uri) }
        .getOrNull()
        .orEmpty()
        .lowercase(Locale.ROOT)
    val fileExtension = conversionExtensionOf(name)
    val extension = when {
        fileExtension.isNotBlank() -> fileExtension
        mime == "model/gltf+json" -> "gltf"
        mime == "model/gltf-binary" -> "glb"
        else -> ""
    }

    val kind = when {
        mime.startsWith("image/") -> ConversionKind.PHOTO
        mime.startsWith("video/") -> ConversionKind.VIDEO
        mime == "model/gltf+json" || mime == "model/gltf-binary" -> ConversionKind.MODEL
        extension in setOf("ply", "obj", "gltf", "glb") -> ConversionKind.MODEL
        extension in setOf("png", "jpg", "jpeg", "webp", "heic", "heif", "bmp") -> ConversionKind.PHOTO
        extension in setOf("mp4", "m4v", "3gp", "webm", "mkv", "mov") -> ConversionKind.VIDEO
        else -> null
    } ?: return null

    if (kind == ConversionKind.MODEL && !MediaFileConverter.isSupportedModelExtension(extension)) {
        return null
    }
    return ConversionSource(uri, name, kind, extension)
}

private fun buildConversionOutputName(source: ConversionSource): String {
    val dot = source.name.lastIndexOf('.')
    val base = if (dot > 0) source.name.substring(0, dot) else source.name
    return when (source.kind) {
        ConversionKind.PHOTO -> "$base-gbmoder.png"
        ConversionKind.VIDEO -> "$base-gbmoder.mp4"
        ConversionKind.MODEL -> "$base-gbmoder.${source.extension}"
    }
}

private fun conversionOutputMimeType(source: ConversionSource): String = when (source.kind) {
    ConversionKind.PHOTO -> "image/png"
    ConversionKind.VIDEO -> "video/mp4"
    ConversionKind.MODEL -> when (source.extension) {
        "gltf" -> "model/gltf+json"
        "glb" -> "model/gltf-binary"
        "obj" -> "text/plain"
        else -> "application/octet-stream"
    }
}

private fun queryConversionDisplayName(context: Context, uri: Uri): String? {
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
                if (index >= 0) return cursor.getString(index)
            }
        }
    } catch (_: Throwable) {
    }
    return null
}

private fun conversionExtensionOf(name: String): String {
    val dot = name.lastIndexOf('.')
    if (dot < 0 || dot == name.length - 1) return ""
    return name.substring(dot + 1).lowercase(Locale.ROOT)
}
