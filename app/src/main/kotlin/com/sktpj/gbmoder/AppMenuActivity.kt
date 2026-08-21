package com.sktpj.gbmoder

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text as MaterialText
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

enum class AppMenuPage {
    HOME,
    LIBRARIES,
    PRIVACY,
}

class AppMenuActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        LiveModeBillingManager.initialize(this)

        val options = MediaFileConverter.Options(
            intent.getStringExtra(MediaConversionActivity.EXTRA_MODE),
            intent.getStringExtra(MediaConversionActivity.EXTRA_RESOLUTION),
            intent.getIntExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, 6),
            intent.getIntExtra(MediaConversionActivity.EXTRA_CONTRAST, 122),
            intent.getBooleanExtra(MediaConversionActivity.EXTRA_DITHER, true),
        )

        setContent {
            GbModerTheme(this) {
                AppMenuScreen(
                    options = options,
                    onClose = ::finish,
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        LiveModeBillingManager.refreshEntitlement()
    }
}

@Composable
private fun AppMenuScreen(
    options: MediaFileConverter.Options,
    onClose: () -> Unit,
) {
    var pageName by rememberSaveable { mutableStateOf(AppMenuPage.HOME.name) }
    val page = runCatching { AppMenuPage.valueOf(pageName) }.getOrDefault(AppMenuPage.HOME)

    BackHandler(enabled = page != AppMenuPage.HOME) {
        pageName = AppMenuPage.HOME.name
    }

    Scaffold(
        modifier = Modifier.fillMaxSize().testTag("app-menu-screen"),
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
            Spacer(Modifier.height(12.dp).testTag("menu-top-quiet-zone"))

            when (page) {
                AppMenuPage.HOME -> AppMenuHome(
                    options = options,
                    onLibraries = { pageName = AppMenuPage.LIBRARIES.name },
                    onPrivacy = { pageName = AppMenuPage.PRIVACY.name },
                    onClose = onClose,
                )
                AppMenuPage.LIBRARIES -> LibrariesPage(
                    onBack = { pageName = AppMenuPage.HOME.name },
                )
                AppMenuPage.PRIVACY -> PrivacyPolicyPage(
                    onBack = { pageName = AppMenuPage.HOME.name },
                )
            }
        }
    }
}

@Composable
private fun AppMenuHome(
    options: MediaFileConverter.Options,
    onLibraries: () -> Unit,
    onPrivacy: () -> Unit,
    onClose: () -> Unit,
) {
    val context = LocalContext.current

    MaterialText(
        text = stringResource(R.string.menu_title),
        style = MaterialTheme.typography.headlineSmall,
        fontWeight = FontWeight.SemiBold,
    )
    MaterialText(
        text = stringResource(R.string.menu_description),
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )

    MenuEntry(
        title = stringResource(R.string.menu_diagnostics_title),
        description = stringResource(R.string.menu_diagnostics_description),
        tag = "menu-diagnostics",
        onClick = {
            context.startActivity(
                Intent(context, VideoDiagnosticsActivity::class.java).apply {
                    putExtra(MediaConversionActivity.EXTRA_MODE, options.mode)
                    putExtra(MediaConversionActivity.EXTRA_RESOLUTION, options.resolution)
                    putExtra(MediaConversionActivity.EXTRA_BRIGHTNESS, options.brightness)
                    putExtra(MediaConversionActivity.EXTRA_CONTRAST, options.contrast)
                    putExtra(MediaConversionActivity.EXTRA_DITHER, options.dither)
                },
            )
        },
    )
    MenuEntry(
        title = stringResource(R.string.menu_libraries_title),
        description = stringResource(R.string.menu_libraries_description),
        tag = "menu-libraries",
        onClick = onLibraries,
    )
    MenuEntry(
        title = stringResource(R.string.menu_privacy_title),
        description = stringResource(R.string.menu_privacy_description),
        tag = "menu-privacy",
        onClick = onPrivacy,
    )

    HorizontalDivider()
    MaterialText(
        text = stringResource(R.string.live_mode_title),
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
    )
    LiveModeSubscriptionCard()

    HorizontalDivider()
    MaterialText(
        text = stringResource(R.string.menu_about_title),
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
    )
    OutlinedCard(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            MaterialText(stringResource(R.string.menu_version_format, BuildConfig.VERSION_NAME))
            MaterialText(stringResource(R.string.menu_package_format, context.packageName))
        }
    }

    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
        TextButton(onClick = onClose) {
            MaterialText(stringResource(R.string.close))
        }
    }
}

@Composable
private fun MenuEntry(
    title: String,
    description: String,
    tag: String,
    onClick: () -> Unit,
) {
    OutlinedCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .testTag(tag),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            MaterialText(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            MaterialText(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

private data class LibraryInfo(
    val name: String,
    val version: String,
    val license: String,
    val runtime: Boolean,
)

@Composable
private fun LibrariesPage(onBack: () -> Unit) {
    val libraries = listOf(
        LibraryInfo("Jetpack Compose UI / Foundation / Material 3", "BOM 2026.08.00", "Apache License 2.0", true),
        LibraryInfo("AndroidX Activity Compose", "1.13.0", "Apache License 2.0", true),
        LibraryInfo("Material 3 Adaptive", "1.3.0", "Apache License 2.0", true),
        LibraryInfo("Google Play Billing Library", "9.1.0", "Google Play SDK terms", true),
        LibraryInfo("JUnit", "4.13.2", "Eclipse Public License 1.0", false),
        LibraryInfo("Android Gradle Plugin", "9.3.0", "Build tool", false),
        LibraryInfo("Kotlin Compose plugin", "2.3.21", "Build tool", false),
    )

    PageHeader(
        title = stringResource(R.string.menu_libraries_title),
        description = stringResource(R.string.libraries_page_description),
        onBack = onBack,
    )

    libraries.forEach { library ->
        OutlinedCard(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                MaterialText(
                    text = library.name,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                )
                MaterialText(
                    text = library.version,
                    style = MaterialTheme.typography.bodyMedium,
                )
                MaterialText(
                    text = library.license,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                MaterialText(
                    text = if (library.runtime) {
                        stringResource(R.string.library_scope_runtime)
                    } else {
                        stringResource(R.string.library_scope_build_test)
                    },
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun PrivacyPolicyPage(onBack: () -> Unit) {
    PageHeader(
        title = stringResource(R.string.menu_privacy_title),
        description = stringResource(R.string.privacy_policy_intro),
        onBack = onBack,
    )

    PrivacySection(
        title = stringResource(R.string.privacy_section_data_access),
        body = stringResource(R.string.privacy_data_access_body),
    )
    PrivacySection(
        title = stringResource(R.string.privacy_section_accessibility),
        body = stringResource(R.string.privacy_accessibility_body),
    )
    PrivacySection(
        title = stringResource(R.string.privacy_section_screen_capture),
        body = stringResource(R.string.privacy_screen_capture_body),
    )
    PrivacySection(
        title = stringResource(R.string.privacy_section_files),
        body = stringResource(R.string.privacy_files_body),
    )
    PrivacySection(
        title = stringResource(R.string.privacy_section_billing),
        body = stringResource(R.string.privacy_billing_body),
    )
    PrivacySection(
        title = stringResource(R.string.privacy_section_diagnostics),
        body = stringResource(R.string.privacy_diagnostics_body),
    )
    PrivacySection(
        title = stringResource(R.string.privacy_section_network),
        body = stringResource(R.string.privacy_network_body),
    )
    PrivacySection(
        title = stringResource(R.string.privacy_section_retention),
        body = stringResource(R.string.privacy_retention_body),
    )
    PrivacySection(
        title = stringResource(R.string.privacy_section_contact),
        body = stringResource(R.string.privacy_contact_body),
    )
    MaterialText(
        text = stringResource(R.string.privacy_last_updated),
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

@Composable
private fun PageHeader(
    title: String,
    description: String,
    onBack: () -> Unit,
) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            MaterialText(
                text = title,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.SemiBold,
            )
            MaterialText(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        TextButton(onClick = onBack) {
            MaterialText(stringResource(R.string.menu_back))
        }
    }
}

@Composable
private fun PrivacySection(title: String, body: String) {
    OutlinedCard(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            MaterialText(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
            )
            MaterialText(
                text = body,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}
