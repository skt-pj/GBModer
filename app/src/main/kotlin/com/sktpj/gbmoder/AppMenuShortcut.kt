package com.sktpj.gbmoder

import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text as MaterialText
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag

@Composable
fun AppMenuShortcut(options: MediaFileConverter.Options) {
    val context = LocalContext.current
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.End,
    ) {
        TextButton(
            onClick = {
                context.startActivity(
                    Intent(context, AppMenuActivity::class.java).apply {
                        putExtra(MediaConversionActivity.EXTRA_MODE, options.mode)
                        putExtra(MediaConversionActivity.EXTRA_RESOLUTION, options.resolution)
                        putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, options.brightness)
                        putExtra(MediaConversionActivity.EXTRA_CONTRAST, options.contrast)
                        putExtra(MediaConversionActivity.EXTRA_DITHER, options.dither)
                    },
                )
            },
            modifier = Modifier.testTag("app-menu"),
        ) {
            MaterialText(
                text = "⋮",
                style = MaterialTheme.typography.headlineSmall,
            )
        }
    }
}
