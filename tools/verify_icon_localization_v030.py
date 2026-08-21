#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = (root / "version.properties").read_text()
manifest = (root / "app/src/main/AndroidManifest.xml").read_text()
compose = (root / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt").read_text()
conversion = (root / "app/src/main/kotlin/com/sktpj/gbmoder/MediaConversionActivity.kt").read_text()
localization = (root / "app/src/main/kotlin/com/sktpj/gbmoder/GbModerLocalization.kt").read_text()
adaptive26 = (root / "app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml").read_text()
adaptive33 = (root / "app/src/main/res/mipmap-anydpi-v33/ic_launcher.xml").read_text()
foreground = (root / "app/src/main/res/drawable/ic_launcher_foreground.xml").read_text()
monochrome = (root / "app/src/main/res/drawable/ic_launcher_monochrome.xml").read_text()
notification = (root / "app/src/main/res/drawable/ic_notification.xml").read_text()
locale_config = (root / "app/src/main/res/xml/locales_config.xml").read_text()
generated_main = (root / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java").read_text()
generated_capture = (root / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/FilterCaptureService.java").read_text()


def need(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r}")
    print(f"PASS {label}")


need(version, "VERSION_NAME=0.1.33", "version name")
need(version, "VERSION_CODE=34", "version code")
need(manifest, 'android:icon="@mipmap/ic_launcher"', "adaptive launcher reference")
need(manifest, 'android:roundIcon="@mipmap/ic_launcher"', "round launcher reference")
need(manifest, 'android:localeConfig="@xml/locales_config"', "per-app locale config")
need(manifest, 'android:label="@string/app_name"', "localized app label")
need(manifest, 'android:label="@string/accessibility_service_label"', "localized service label")

need(adaptive26, '@drawable/ic_launcher_background', "adaptive background")
need(adaptive26, '@drawable/ic_launcher_foreground', "adaptive foreground")
need(adaptive33, '@drawable/ic_launcher_monochrome', "Android 13 themed icon")
need(foreground, 'android:viewportWidth="108"', "108dp adaptive canvas")
need(foreground, 'android:viewportHeight="108"', "108dp adaptive canvas height")
if 'M18,4 H90' in foreground or 'M4,4' in foreground:
    raise SystemExit("FAIL adaptive foreground: do not bake a rounded-square launcher mask into the foreground")
print("PASS adaptive foreground has no baked launcher mask")
need(monochrome, '#FFFFFFFF', "single-color themed glyph")
need(notification, '#FFFFFFFF', "notification silhouette")

for locale in ('en', 'ja', 'zh-Hans', 'ko'):
    need(locale_config, f'android:name="{locale}"', f"locale {locale}")
for path in (
    "app/src/main/res/values/strings.xml",
    "app/src/main/res/values-ja/strings.xml",
    "app/src/main/res/values-zh-rCN/strings.xml",
    "app/src/main/res/values-ko/strings.xml",
):
    if not (root / path).exists():
        raise SystemExit(f"FAIL locale resource missing: {path}")
    print(f"PASS locale resource {path}")

if 'import androidx.compose.material3.Text' in compose or 'import androidx.compose.material3.Text\n' in conversion:
    raise SystemExit("FAIL Compose UI bypasses localization bridge with direct Material Text import")
print("PASS Compose text routed through localization bridge")
need(localization, "object GbModerLocalization", "localization bridge")
need(localization, "R.string.phone_ratio_format", "dynamic resolution localization")
need(localization, "R.string.converting_format", "dynamic conversion localization")
need(localization, "MaterialText(", "Material 3 text renderer retained")

need(generated_main, "GbModerLocalization.localize(this, value)", "generated status localization")
need(generated_main, "R.string.adb_guide_message", "localized ADB guide")
need(generated_capture, "R.drawable.ic_notification", "proper notification small icon")
need(generated_capture, "R.string.notification_filter_active", "localized notification content")
need(generated_capture, "R.string.notification_stop", "localized notification stop action")
need(generated_capture, "R.string.whole_screen_not_supported", "localized capture warning")

print("ANDROID ICON + LOCALIZATION v0.1.33 AUTOMATED GATE: PASS")
