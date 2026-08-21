package com.sktpj.gbmoder

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Build
import android.view.View
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalWindowInfo
import androidx.compose.ui.platform.ViewCompositionStrategy
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.roundToInt

interface GbModerUiActions {
    fun onStart(
        modePosition: Int,
        resolutionPosition: Int,
        brightness: Int,
        contrast: Int,
        dither: Boolean,
        captureRoutePosition: Int,
        textRecognitionEnabled: Boolean,
    )

    fun onStop()
    fun onLogSync()
    fun onAdbGuide()
    fun onAccessibilitySetup()
}

class GbModerUiState {
    private var statusState by mutableStateOf("停止中")
    private var runningState by mutableStateOf(false)
    private var accessibilityReadyState by mutableStateOf(false)

    val status: String
        get() = statusState

    val running: Boolean
        get() = runningState

    val accessibilityReady: Boolean
        get() = accessibilityReadyState

    fun setStatus(value: String) {
        statusState = value
    }

    fun setRunning(value: Boolean) {
        runningState = value
    }

    fun setAccessibilityReady(value: Boolean) {
        accessibilityReadyState = value
    }
}

object GbModerComposeUi {
    @JvmStatic
    fun createView(
        activity: Activity,
        state: GbModerUiState,
        actions: GbModerUiActions,
    ): View {
        return ComposeView(activity).apply {
            setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnDetachedFromWindow)
            setContent {
                GbModerTheme(activity) {
                    GbModerScreen(state = state, actions = actions)
                }
            }
        }
    }
}

@Composable
internal fun GbModerTheme(activity: Activity, content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val colorScheme = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && dark -> dynamicDarkColorScheme(activity)
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> dynamicLightColorScheme(activity)
        dark -> androidx.compose.material3.darkColorScheme()
        else -> androidx.compose.material3.lightColorScheme()
    }
    MaterialTheme(colorScheme = colorScheme, content = content)
}

@Composable
private fun GbModerScreen(state: GbModerUiState, actions: GbModerUiActions) {
    val windowInfo = LocalWindowInfo.current
    val density = LocalDensity.current
    val expanded = with(density) { windowInfo.containerSize.width.toDp() } >= 840.dp

    Scaffold(
        modifier = Modifier.fillMaxSize().testTag("gbmoder-scaffold"),
        contentWindowInsets = WindowInsets.safeDrawing,
    ) { innerPadding ->
        if (expanded) {
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
            ) {
                PreviewPane(
                    modifier = Modifier
                        .weight(0.9f)
                        .fillMaxHeight()
                        .padding(24.dp),
                )
                HorizontalDivider(modifier = Modifier.fillMaxHeight().width(1.dp))
                SettingsPane(
                    state = state,
                    actions = actions,
                    modifier = Modifier
                        .weight(1.1f)
                        .fillMaxHeight(),
                )
            }
        } else {
            SettingsPane(
                state = state,
                actions = actions,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
            )
        }
    }
}

@Composable
private fun SettingsPane(
    state: GbModerUiState,
    actions: GbModerUiActions,
    modifier: Modifier = Modifier,
) {
    var modePosition by rememberSaveable { mutableStateOf(0) }
    var resolutionPosition by rememberSaveable { mutableStateOf(0) }
    var brightness by rememberSaveable { mutableStateOf(6f) }
    var contrast by rememberSaveable { mutableStateOf(122f) }
    var dither by rememberSaveable { mutableStateOf(true) }
    var textRecognitionEnabled by rememberSaveable { mutableStateOf(false) }
    var captureRoutePosition by rememberSaveable { mutableStateOf(0) }
    var detailsExpanded by rememberSaveable { mutableStateOf(false) }
    var resolutionMenuExpanded by remember { mutableStateOf(false) }

    val resolutions = listOf(
        "GB / 160×144",
        "GBC / 160×144",
        "GBA / 240×160",
        "DS / 256×192",
        "端末比 / 25%",
        "端末比 / 33%",
        "端末比 / 50%",
        "端末比 / 67%",
        "端末比 / 75%",
        "スマホの元解像度",
    )

    Column(
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp)
            .testTag("settings-scroll"),
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Spacer(Modifier.height(12.dp).testTag("top-quiet-zone"))

        if (!state.accessibilityReady) {
            FirstSetupCard(actions)
        }

        SectionTitle("表示モード")
        val modes = listOf("GB", "GBC", "GBA", "DS")
        SingleChoiceSegmentedButtonRow(
            modifier = Modifier.fillMaxWidth().testTag("mode-segmented"),
        ) {
            modes.forEachIndexed { index, label ->
                SegmentedButton(
                    selected = modePosition == index,
                    onClick = { modePosition = index },
                    shape = SegmentedButtonDefaults.itemShape(index = index, count = modes.size),
                    label = { Text(label) },
                )
            }
        }

        SectionTitle("解像度")
        Box(modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(
                onClick = { resolutionMenuExpanded = true },
                modifier = Modifier.fillMaxWidth().testTag("resolution-selector"),
            ) {
                Text(resolutions[resolutionPosition], modifier = Modifier.weight(1f))
                Text("▾")
            }
            DropdownMenu(
                expanded = resolutionMenuExpanded,
                onDismissRequest = { resolutionMenuExpanded = false },
            ) {
                resolutions.forEachIndexed { index, label ->
                    DropdownMenuItem(
                        text = { Text(label) },
                        onClick = {
                            resolutionPosition = index
                            resolutionMenuExpanded = false
                        },
                    )
                }
            }
        }
        Text(
            "表示モードの色・階調処理と解像度の出力サイズを組み合わせて適用します。",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        ValueSlider(
            title = "明るさ",
            value = brightness,
            range = -80f..80f,
            onValueChange = { brightness = it.roundToInt().toFloat() },
            tag = "brightness-slider",
        )

        ValueSlider(
            title = "コントラスト",
            value = contrast,
            range = 50f..200f,
            onValueChange = { contrast = it.roundToInt().toFloat() },
            tag = "contrast-slider",
        )

        ToggleSettingRow(
            title = "ディザ",
            description = "階調境界をパターン化して見かけの階調を補います。",
            checked = dither,
            onCheckedChange = { dither = it },
            contentDescription = "ディザ",
            tag = "dither-row",
        )

        ToggleSettingRow(
            title = "文字を読みやすくする",
            description = "画面内の文字を認識し、低解像度向け8×8フォントで再描画します。GB / 160×144で有効です。",
            checked = textRecognitionEnabled,
            onCheckedChange = { textRecognitionEnabled = it },
            contentDescription = "文字認識と8×8再描画",
            tag = "text-recognition-row",
        )

        Button(
            onClick = {
                if (state.running) {
                    actions.onStop()
                } else {
                    actions.onStart(
                        modePosition,
                        resolutionPosition,
                        brightness.roundToInt(),
                        contrast.roundToInt(),
                        dither,
                        captureRoutePosition,
                        textRecognitionEnabled,
                    )
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp)
                .semantics {
                    contentDescription = if (state.running) "フィルターを停止" else "フィルターを開始"
                }
                .testTag("primary-action"),
            colors = if (state.running) {
                ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
            } else {
                ButtonDefaults.buttonColors()
            },
        ) {
            Text(if (state.running) "停止" else "フィルター開始")
        }

        Surface(
            modifier = Modifier.fillMaxWidth().testTag("status-message"),
            shape = RoundedCornerShape(12.dp),
            color = MaterialTheme.colorScheme.surfaceContainer,
        ) {
            Text(
                text = state.status,
                modifier = Modifier.padding(14.dp),
                style = MaterialTheme.typography.bodyMedium,
            )
        }

        MediaConversionCard(
            modePosition = modePosition,
            resolutionPosition = resolutionPosition,
            brightness = brightness.roundToInt(),
            contrast = contrast.roundToInt(),
            dither = dither,
        )

        DiagnosticsCard(
            expanded = detailsExpanded,
            onToggle = { detailsExpanded = !detailsExpanded },
            captureRoutePosition = captureRoutePosition,
            onCaptureRouteChange = { captureRoutePosition = it },
            onLogSync = actions::onLogSync,
            onAdbGuide = actions::onAdbGuide,
        )

        Spacer(Modifier.height(12.dp))
    }
}

@Composable
private fun FirstSetupCard(actions: GbModerUiActions) {
    Card(
        modifier = Modifier.fillMaxWidth().testTag("first-setup-card"),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("初回設定", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "ユーザー補助を有効にして、画面のテキストを取得します。",
                style = MaterialTheme.typography.bodyMedium,
            )
            Button(
                onClick = actions::onAccessibilitySetup,
                modifier = Modifier.fillMaxWidth().testTag("accessibility-setup"),
            ) {
                Text("ユーザー補助を有効化")
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(text, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
}

@Composable
private fun ValueSlider(
    title: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    onValueChange: (Float) -> Unit,
    tag: String,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(title, style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
            Text(value.roundToInt().toString(), style = MaterialTheme.typography.labelLarge)
        }
        Slider(
            value = value,
            onValueChange = onValueChange,
            valueRange = range,
            modifier = Modifier
                .fillMaxWidth()
                .semantics { contentDescription = "$title ${value.roundToInt()}" }
                .testTag(tag),
        )
    }
}

@Composable
private fun ToggleSettingRow(
    title: String,
    description: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    contentDescription: String,
    tag: String,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onCheckedChange(!checked) }
            .padding(vertical = 6.dp)
            .semantics {
                this.contentDescription = "$contentDescription ${if (checked) "オン" else "オフ"}"
            }
            .testTag(tag),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(
                description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}

@Composable
private fun MediaConversionCard(
    modePosition: Int,
    resolutionPosition: Int,
    brightness: Int,
    contrast: Int,
    dither: Boolean,
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    Card(modifier = Modifier.fillMaxWidth().testTag("media-conversion-card")) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("ファイル変換", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Text(
                "現在の表示モード・解像度・明るさ・コントラスト・ディザで変換して保存します。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            ConversionActionButton(
                iconRes = R.drawable.ic_photo_24,
                label = "写真をPNGに変換",
                tag = "convert-photo",
                onClick = {
                    launchMediaConversion(
                        context,
                        MediaConversionActivity.KIND_PHOTO,
                        modePosition,
                        resolutionPosition,
                        brightness,
                        contrast,
                        dither,
                    )
                },
            )
            ConversionActionButton(
                iconRes = R.drawable.ic_video_24,
                label = "動画をMP4に変換",
                tag = "convert-video",
                onClick = {
                    launchMediaConversion(
                        context,
                        MediaConversionActivity.KIND_VIDEO,
                        modePosition,
                        resolutionPosition,
                        brightness,
                        contrast,
                        dither,
                    )
                },
            )
            ConversionActionButton(
                iconRes = R.drawable.ic_3d_model_24,
                label = "3Dモデルを変換",
                tag = "convert-model",
                onClick = {
                    launchMediaConversion(
                        context,
                        MediaConversionActivity.KIND_MODEL,
                        modePosition,
                        resolutionPosition,
                        brightness,
                        contrast,
                        dither,
                    )
                },
            )

            Text(
                "3Dモデル対応: PLY / OBJ / glTF / GLB",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ConversionActionButton(
    iconRes: Int,
    label: String,
    tag: String,
    onClick: () -> Unit,
) {
    FilledTonalButton(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 52.dp)
            .testTag(tag),
    ) {
        Icon(
            painter = painterResource(iconRes),
            contentDescription = null,
            modifier = Modifier.size(ButtonDefaults.IconSize),
        )
        Spacer(Modifier.width(ButtonDefaults.IconSpacing))
        Text(label, modifier = Modifier.weight(1f))
    }
}

private fun launchMediaConversion(
    context: Context,
    kind: String,
    modePosition: Int,
    resolutionPosition: Int,
    brightness: Int,
    contrast: Int,
    dither: Boolean,
) {
    val mode = when (modePosition) {
        1 -> GameBoyFilter.MODE_GBC
        2 -> GameBoyFilter.MODE_GBA
        3 -> GameBoyFilter.MODE_DS
        else -> GameBoyFilter.MODE_GB
    }
    val resolution = when (resolutionPosition) {
        1 -> GameBoyFilter.RESOLUTION_GBC
        2 -> GameBoyFilter.RESOLUTION_GBA
        3 -> GameBoyFilter.RESOLUTION_DS
        4 -> GameBoyFilter.RESOLUTION_PHONE_25
        5 -> GameBoyFilter.RESOLUTION_PHONE_33
        6 -> GameBoyFilter.RESOLUTION_PHONE_50
        7 -> GameBoyFilter.RESOLUTION_PHONE_67
        8 -> GameBoyFilter.RESOLUTION_PHONE_75
        9 -> GameBoyFilter.RESOLUTION_NATIVE
        else -> GameBoyFilter.RESOLUTION_GB
    }
    context.startActivity(
        Intent(context, MediaConversionActivity::class.java).apply {
            putExtra(MediaConversionActivity.EXTRA_KIND, kind)
            putExtra(MediaConversionActivity.EXTRA_MODE, mode)
            putExtra(MediaConversionActivity.EXTRA_RESOLUTION, resolution)
            putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, brightness)
            putExtra(MediaConversionActivity.EXTRA_CONTRAST, contrast)
            putExtra(MediaConversionActivity.EXTRA_DITHER, dither)
        },
    )
}

@Composable
private fun DiagnosticsCard(
    expanded: Boolean,
    onToggle: () -> Unit,
    captureRoutePosition: Int,
    onCaptureRouteChange: (Int) -> Unit,
    onLogSync: () -> Unit,
    onAdbGuide: () -> Unit,
) {
    var routeMenuExpanded by remember { mutableStateOf(false) }
    val routeLabels = listOf("標準（推奨）", "互換モード")

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("diagnostics-card"),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(onClick = onToggle)
                    .padding(vertical = 2.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text("詳細設定・診断", style = MaterialTheme.typography.titleSmall)
                    Text(
                        "画面取得方式・ログ・ADB",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Text(if (expanded) "⌃" else "⌄")
            }
            if (expanded) {
                HorizontalDivider()

                Text("画面取得方式", style = MaterialTheme.typography.titleSmall)
                Box(modifier = Modifier.fillMaxWidth()) {
                    OutlinedButton(
                        onClick = { routeMenuExpanded = true },
                        modifier = Modifier.fillMaxWidth().testTag("capture-route-selector"),
                    ) {
                        Text(routeLabels[captureRoutePosition], modifier = Modifier.weight(1f))
                        Text("▾")
                    }
                    DropdownMenu(
                        expanded = routeMenuExpanded,
                        onDismissRequest = { routeMenuExpanded = false },
                    ) {
                        DropdownMenuItem(
                            text = { Text("標準（推奨）") },
                            onClick = {
                                onCaptureRouteChange(0)
                                routeMenuExpanded = false
                            },
                        )
                        DropdownMenuItem(
                            text = { Text("互換モード（Android 14+）") },
                            enabled = Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE,
                            onClick = {
                                onCaptureRouteChange(1)
                                routeMenuExpanded = false
                            },
                        )
                    }
                }
                Text(
                    if (captureRoutePosition == 0) {
                        "MediaProjectionを使用します。通常はこちらを使用してください。"
                    } else {
                        "Accessibility Windowを使用します。Android 14以降向けの互換モードです。"
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                HorizontalDivider()
                OutlinedButton(
                    onClick = onLogSync,
                    modifier = Modifier.fillMaxWidth().testTag("log-sync"),
                ) {
                    Text("ログ同期")
                }
                OutlinedButton(
                    onClick = onAdbGuide,
                    modifier = Modifier.fillMaxWidth().testTag("adb-guide"),
                ) {
                    Text("ADB手順")
                }
                Text(
                    "画面共有では『1つのアプリ』を選択してください。画面全体を選ぶと自己キャプチャ検出で停止します。DRM / FLAG_SECUREで保護された画面は取得できません。",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun PreviewPane(modifier: Modifier = Modifier) {
    val dmgPalette = listOf(
        Color(0xFFE0E7C0),
        Color(0xFFA8B68A),
        Color(0xFF59664A),
        Color(0xFF1F241D),
    )

    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("プレビュー", style = MaterialTheme.typography.titleMedium, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(18.dp))
        Card(
            colors = CardDefaults.cardColors(containerColor = Color(0xFFB7C48D)),
            modifier = Modifier.testTag("gb-preview"),
        ) {
            Column(
                modifier = Modifier.padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                val previewLines = listOf(
                    "GAME BOY",
                    "0123456789",
                    "ABCDEFGHIJ",
                    "KLMNOPQRST",
                    "UVWXYZ",
                )
                previewLines.forEach { line ->
                    Text(
                        line,
                        color = Color(0xFF1F241D),
                        fontFamily = FontFamily.Monospace,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp,
                    )
                }
            }
        }

        Spacer(Modifier.height(22.dp))
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("GB (DMG) パレット", style = MaterialTheme.typography.titleSmall)
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    dmgPalette.forEachIndexed { index, color ->
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Box(Modifier.size(36.dp).background(color, RoundedCornerShape(4.dp)))
                            Text(index.toString(), style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            }
        }
    }
}
