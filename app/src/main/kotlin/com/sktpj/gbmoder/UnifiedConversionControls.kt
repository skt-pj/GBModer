package com.sktpj.gbmoder

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.database.Cursor
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.provider.DocumentsContract
import android.provider.OpenableColumns
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import java.util.Locale

private const val CONVERSION_PREFS = "conversion_output"
private const val PREF_OUTPUT_TREE_URI = "output_tree_uri"
private const val PREF_OUTPUT_TREE_NAME = "output_tree_name"

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

private data class RememberedOutputFolder(
    val uriText: String?,
    val name: String?,
)

@Composable
internal fun UnifiedConversionControls(
    options: MediaFileConverter.Options,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val mainHandler = remember { Handler(Looper.getMainLooper()) }
    val rememberedFolder = remember { loadRememberedOutputFolder(context) }

    var sourceUriText by rememberSaveable { mutableStateOf<String?>(null) }
    var sourceName by rememberSaveable { mutableStateOf<String?>(null) }
    var sourceKindName by rememberSaveable { mutableStateOf<String?>(null) }
    var sourceExtension by rememberSaveable { mutableStateOf("") }
    var outputTreeUriText by rememberSaveable { mutableStateOf(rememberedFolder.uriText) }
    var outputFolderName by rememberSaveable { mutableStateOf(rememberedFolder.name) }
    var running by rememberSaveable { mutableStateOf(false) }
    var progress by rememberSaveable { mutableIntStateOf(0) }
    var progressVisible by rememberSaveable { mutableStateOf(false) }
    var completedUriText by rememberSaveable { mutableStateOf<String?>(null) }
    var completedName by rememberSaveable { mutableStateOf<String?>(null) }
    var completedMime by rememberSaveable { mutableStateOf<String?>(null) }

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
        val treeUri = outputTreeUriText?.let(Uri::parse) ?: return
        if (running) return

        running = true
        progress = 0
        progressVisible = true
        completedUriText = null
        completedName = null
        completedMime = null

        Thread({
            var createdOutput: Uri? = null
            try {
                val outputName = buildConversionOutputName(source)
                val outputMime = conversionOutputMimeType(source)
                val output = createOutputDocument(context, treeUri, outputMime, outputName)
                createdOutput = output

                val progressCallback = MediaFileConverter.Progress { percent, _ ->
                    mainHandler.post {
                        progress = percent.coerceIn(0, 100)
                    }
                }
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
                    progress = 100
                    running = false
                    completedUriText = output.toString()
                    completedName = outputName
                    completedMime = outputMime
                }
            } catch (error: Throwable) {
                createdOutput?.let { output ->
                    runCatching { DocumentsContract.deleteDocument(context.contentResolver, output) }
                }
                mainHandler.post {
                    running = false
                    progressVisible = false
                    if (error is SecurityException) {
                        clearRememberedOutputFolder(context)
                        outputTreeUriText = null
                        outputFolderName = null
                    }
                    showMessage("変換できませんでした: ${error.message ?: error.javaClass.simpleName}")
                }
            }
        }, "GBModerUnifiedConversion").start()
    }

    val outputFolderLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree(),
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult

        val grantFlags = Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        try {
            outputTreeUriText?.let { previous ->
                if (previous != uri.toString()) {
                    runCatching {
                        context.contentResolver.releasePersistableUriPermission(Uri.parse(previous), grantFlags)
                    }
                }
            }
            context.contentResolver.takePersistableUriPermission(uri, grantFlags)
            val folderName = queryConversionFolderName(context, uri) ?: uri.lastPathSegment ?: "folder"
            rememberOutputFolder(context, uri, folderName)
            outputTreeUriText = uri.toString()
            outputFolderName = folderName
        } catch (_: SecurityException) {
            showMessage("出力先フォルダの権限を保存できませんでした")
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
            progressVisible = false
            showMessage("対応していないファイル形式です")
            return@rememberLauncherForActivityResult
        }

        sourceUriText = detected.uri.toString()
        sourceName = detected.name
        sourceKindName = detected.kind.name
        sourceExtension = detected.extension
        progress = 0
        progressVisible = false
        completedUriText = null
        completedName = null
        completedMime = null
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
            Text(
                sourceName ?: "対象ファイルを選択",
                modifier = Modifier.weight(1f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        OutlinedButton(
            onClick = {
                outputFolderLauncher.launch(outputTreeUriText?.let(Uri::parse))
            },
            enabled = !running,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 52.dp)
                .testTag("conversion-output-folder-select"),
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_save_24),
                contentDescription = null,
                modifier = Modifier.size(ButtonDefaults.IconSize),
            )
            Spacer(Modifier.width(ButtonDefaults.IconSpacing))
            Text(
                outputFolderName ?: "出力先フォルダを選択",
                modifier = Modifier.weight(1f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        Button(
            onClick = ::startConversion,
            enabled = !running && currentSource() != null && outputTreeUriText != null,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 56.dp)
                .testTag("conversion-run"),
        ) {
            Text("変換")
        }

        if (progressVisible) {
            Column(
                modifier = Modifier.fillMaxWidth().testTag("conversion-progress-block"),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                LinearProgressIndicator(
                    progress = { progress / 100f },
                    modifier = Modifier.fillMaxWidth().testTag("conversion-progress"),
                )
                Row(modifier = Modifier.fillMaxWidth()) {
                    Spacer(Modifier.weight(1f))
                    Text("$progress%", modifier = Modifier.testTag("conversion-progress-percent"))
                }
            }
        }
    }

    val doneUri = completedUriText?.let(Uri::parse)
    val doneName = completedName
    val doneMime = completedMime
    if (doneUri != null && doneName != null && doneMime != null) {
        AlertDialog(
            onDismissRequest = {
                completedUriText = null
                completedName = null
                completedMime = null
            },
            modifier = Modifier.testTag("conversion-complete-dialog"),
            title = { Text("変換完了") },
            text = { Text("保存しました: $doneName") },
            confirmButton = {
                TextButton(
                    onClick = { openConvertedFile(context, doneUri, doneMime) },
                    modifier = Modifier.testTag("conversion-open-file"),
                ) {
                    Text("ファイルを開く")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = {
                        completedUriText = null
                        completedName = null
                        completedMime = null
                    },
                ) {
                    Text("閉じる")
                }
            },
        )
    }
}

private fun loadRememberedOutputFolder(context: Context): RememberedOutputFolder {
    val prefs = context.getSharedPreferences(CONVERSION_PREFS, Context.MODE_PRIVATE)
    val uriText = prefs.getString(PREF_OUTPUT_TREE_URI, null) ?: return RememberedOutputFolder(null, null)
    val uri = runCatching { Uri.parse(uriText) }.getOrNull() ?: return RememberedOutputFolder(null, null)
    val hasWritePermission = context.contentResolver.persistedUriPermissions.any { permission ->
        permission.uri == uri && permission.isWritePermission
    }
    if (!hasWritePermission) {
        clearRememberedOutputFolder(context)
        return RememberedOutputFolder(null, null)
    }
    val name = prefs.getString(PREF_OUTPUT_TREE_NAME, null)
        ?: queryConversionFolderName(context, uri)
        ?: uri.lastPathSegment
    return RememberedOutputFolder(uriText, name)
}

private fun rememberOutputFolder(context: Context, uri: Uri, name: String) {
    context.getSharedPreferences(CONVERSION_PREFS, Context.MODE_PRIVATE)
        .edit()
        .putString(PREF_OUTPUT_TREE_URI, uri.toString())
        .putString(PREF_OUTPUT_TREE_NAME, name)
        .apply()
}

private fun clearRememberedOutputFolder(context: Context) {
    context.getSharedPreferences(CONVERSION_PREFS, Context.MODE_PRIVATE)
        .edit()
        .remove(PREF_OUTPUT_TREE_URI)
        .remove(PREF_OUTPUT_TREE_NAME)
        .apply()
}

private fun createOutputDocument(
    context: Context,
    treeUri: Uri,
    mimeType: String,
    displayName: String,
): Uri {
    val treeDocumentId = DocumentsContract.getTreeDocumentId(treeUri)
    val parentDocument = DocumentsContract.buildDocumentUriUsingTree(treeUri, treeDocumentId)
    return DocumentsContract.createDocument(
        context.contentResolver,
        parentDocument,
        mimeType,
        displayName,
    ) ?: throw IllegalStateException("output document could not be created")
}

private fun openConvertedFile(context: Context, uri: Uri, mimeType: String) {
    val intent = Intent(Intent.ACTION_VIEW).apply {
        setDataAndType(uri, mimeType)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    try {
        context.startActivity(intent)
    } catch (_: ActivityNotFoundException) {
        Toast.makeText(
            context,
            GbModerLocalization.localize(context, "このファイルを開けるアプリがありません"),
            Toast.LENGTH_SHORT,
        ).show()
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

private fun queryConversionFolderName(context: Context, treeUri: Uri): String? {
    return try {
        val treeDocumentId = DocumentsContract.getTreeDocumentId(treeUri)
        val documentUri = DocumentsContract.buildDocumentUriUsingTree(treeUri, treeDocumentId)
        queryConversionDisplayName(context, documentUri)
    } catch (_: Throwable) {
        null
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
