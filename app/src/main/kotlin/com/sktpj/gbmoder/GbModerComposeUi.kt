package com.sktpj.gbmoder

import android.app.Activity
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
import androidx.compose.material3.HorizontalDivider
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
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.ViewCompositionStrategy
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.material3.adaptive.ExperimentalMaterial3AdaptiveApi
import androidx.compose.material3.adaptive.currentWindowDpSize
import kotlin.math.roundToInt

interface GbModerUiActions {
    fun onStart(
        modePosition: Int,
        resolutionPosition: Int,
        brightness: Int,
        contrast: Int,
        dither: Boolean,
    )

    fun onStop()
    fun onLogSync()
    fun onAdbGuide()
    fun onAccessibilitySetup()
}

class GbModerUiState {
    var status by mutableStateOf("停止中")
        private set

    var running by mutableStateOf(false)
        private set

    var accessibilityReady by mutableStateOf(false)
        private set

    fun setStatus(value: String) {
        status = value
    }

    fun setRunning(value: Boolean) {
        running = value
    }

    fun setAccessibilityReady(value: Boolean) {
        accessibilityReady = value
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
private fun GbModerTheme(activity: Activity, content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val colorScheme = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && dark -> dynamicDarkColorScheme(activity)
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> dynamicLightColorScheme(activity)
        dark -> androidx.compose.material3.darkColorScheme()
        else -> androidx.compose.material3.lightColorScheme()
    }
    MaterialTheme(colorScheme = colorScheme, content = content)
}

@OptIn(ExperimentalMaterial3AdaptiveApi::class)
@Composable
private fun GbModerScreen(state: GbModerUiState, actions: GbModerUiActions) {
    val windowSize = currentWindowDpSize()
    val expanded = windowSize.width >= 840.dp

    Scaffold(
        modifier = Modifier.fillMaxSize().testTag("gbmoder-scaffold"),
        contentWindowInsets = WindowInsets.safeDrawing,
        topBar = {
            TopAppBar(
                title = { Text("GBModer", fontWeight = FontWeight.SemiBold) },
                actions = { StatusPill(running = state.running) },
            )
        },
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
private fun StatusPill(running: Boolean) {
    Surface(
        modifier = Modifier.padding(end = 12.dp).testTag("status-pill"),
        shape = RoundedCornerShape(100.dp),
        tonalElevation = 2.dp,
    ) {
        Text(
            text = if (running) "実行中" else "停止中",
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            style = MaterialTheme.typography.labelMedium,
        )
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

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { dither = !dither }
                .padding(vertical = 6.dp)
                .semantics { contentDescription = "ディザ ${if (dither) "オン" else "オフ"}" }
                .testTag("dither-row"),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text("ディザ", style = MaterialTheme.typography.titleSmall)
                Text(
                    "階調境界をパターン化して見かけの階調を補います。",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Switch(checked = dither, onCheckedChange = { dither = it })
        }

        DiagnosticsCard(
            expanded = detailsExpanded,
            onToggle = { detailsExpanded = !detailsExpanded },
            onLogSync = actions::onLogSync,
            onAdbGuide = actions::onAdbGuide,
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
private fun DiagnosticsCard(
    expanded: Boolean,
    onToggle: () -> Unit,
    onLogSync: () -> Unit,
    onAdbGuide: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onToggle)
            .testTag("diagnostics-card"),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text("詳細設定・診断", style = MaterialTheme.typography.titleSmall)
                    Text(
                        "ログ同期・ADB手順・診断情報",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Text(if (expanded) "⌃" else "⌄")
            }
            if (expanded) {
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
                    "Android 14以降は『1つのアプリ』共有を使用します。画面全体を選ぶと自己キャプチャ検出で停止します。DRM / FLAG_SECUREで保護された画面は取得できません。",
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
