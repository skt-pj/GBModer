package com.sktpj.gbmoder

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

class MediaConversionActivity : ComponentActivity() {
    companion object {
        const val EXTRA_KIND = "kind"
        const val EXTRA_MODE = "mode"
        const val EXTRA_RESOLUTION = "resolution"
        const val EXTRA_BRIGHTNESS = "brightness"
        const val EXTRA_CONTRAST = "contrast"
        const val EXTRA_DITHER = "dither"

        // Retained only so older internal intents do not break. The current UI never asks the user
        // to choose a media kind; file type is detected after the source document is selected.
        const val KIND_PHOTO = "photo"
        const val KIND_VIDEO = "video"
        const val KIND_MODEL = "model"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val options = MediaFileConverter.Options(
            intent.getStringExtra(EXTRA_MODE),
            intent.getStringExtra(EXTRA_RESOLUTION),
            intent.getIntExtra(EXTRA_BRIGHTNESS, 6),
            intent.getIntExtra(EXTRA_CONTRAST, 122),
            intent.getBooleanExtra(EXTRA_DITHER, true),
        )

        setContent {
            GbModerTheme(this) {
                UnifiedMediaConversionScreen(options)
            }
        }
    }
}

@Composable
private fun UnifiedMediaConversionScreen(options: MediaFileConverter.Options) {
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
            Text(
                "変換",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
            )
            UnifiedConversionControls(
                options = options,
                modifier = Modifier.fillMaxWidth().testTag("media-conversion-controls"),
            )
            Spacer(Modifier.height(12.dp))
        }
    }
}
