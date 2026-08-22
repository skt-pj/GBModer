package com.sktpj.gbmoder

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.sktpj.td2048.GameApp

class Game2048ContentActivity : ComponentActivity() {
    private val serviceReady = mutableStateOf(false)
    private lateinit var options: MediaFileConverter.Options
    private var filterStarted = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        options = MediaFileConverter.Options(
            intent.getStringExtra(MediaConversionActivity.EXTRA_MODE),
            intent.getStringExtra(MediaConversionActivity.EXTRA_RESOLUTION),
            intent.getIntExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, 6),
            intent.getIntExtra(MediaConversionActivity.EXTRA_CONTRAST, 122),
            intent.getBooleanExtra(MediaConversionActivity.EXTRA_DITHER, true),
        )

        setContent {
            val ready by serviceReady
            GbModerTheme(this) {
                when {
                    Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE -> {
                        EmbeddedContentMessage(
                            title = "2048TD",
                            body = "フィルター付きコンテンツはAndroid 14以降で利用できます。",
                            buttonLabel = "戻る",
                            onClick = ::finish,
                        )
                    }
                    !ready -> {
                        EmbeddedContentMessage(
                            title = "2048TD",
                            body = "フィルターを適用するため、GBModerのユーザー補助サービスを有効にしてください。",
                            buttonLabel = "ユーザー補助を開く",
                            onClick = {
                                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
                            },
                        )
                    }
                    else -> GameApp()
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        refreshServiceReady()
        window.decorView.postDelayed(::refreshServiceReady, 500L)
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) {
            refreshServiceReady()
            startFilterIfReady()
        }
    }

    override fun onStop() {
        stopEmbeddedFilter()
        super.onStop()
    }

    private fun refreshServiceReady() {
        val ready = Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE &&
            FilterAccessibilityService.getInstance() != null
        serviceReady.value = ready
        if (ready && hasWindowFocus()) {
            startFilterIfReady()
        }
    }

    private fun startFilterIfReady() {
        if (filterStarted || !serviceReady.value) {
            return
        }
        val service = FilterAccessibilityService.getInstance() ?: return
        service.startEmbeddedContentFilter(
            options.mode,
            options.resolution,
            options.brightness,
            options.contrast,
            options.dither,
        )
        filterStarted = true
    }

    private fun stopEmbeddedFilter() {
        if (!filterStarted) {
            return
        }
        FilterAccessibilityService.getInstance()?.let { service ->
            service.stopWindowFilter()
            service.clearOverlay()
        }
        filterStarted = false
    }

    override fun onDestroy() {
        stopEmbeddedFilter()
        super.onDestroy()
    }
}

@Composable
private fun EmbeddedContentMessage(
    title: String,
    body: String,
    buttonLabel: String,
    onClick: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(text = title, style = MaterialTheme.typography.headlineSmall)
        Text(
            text = body,
            modifier = Modifier.padding(top = 12.dp, bottom = 20.dp),
            style = MaterialTheme.typography.bodyMedium,
        )
        Button(onClick = onClick) {
            Text(buttonLabel)
        }
    }
}
