#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def require(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r} in {path}")
    print(f"PASS {label}")


def reject(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle in text:
        raise SystemExit(f"FAIL {label}: unexpected {needle!r} in {path}")
    print(f"PASS {label}")


require("version.properties", "VERSION_NAME=0.1.43", "version name")
require("version.properties", "VERSION_CODE=44", "version code")
require("app/src/main/AndroidManifest.xml", '.AppMenuActivity', "menu activity registered")

menu = "app/src/main/kotlin/com/sktpj/gbmoder/AppMenuActivity.kt"
require(menu, 'testTag("app-menu-screen")', "menu screen")
require(menu, 'tag = "menu-diagnostics"', "diagnostics implementation retained")
require(menu, 'tag = "menu-libraries"', "libraries menu item")
require(menu, 'tag = "menu-privacy"', "privacy menu item")
require(menu, ".testTag(tag)", "menu item tag binding")
require(menu, "VideoDiagnosticsActivity::class.java", "diagnostics route retained")
require(menu, "LiveModeSubscriptionCard()", "subscription implementation retained")
require(menu, "BuildConfig.VERSION_NAME", "app version display")
require(menu, '"Google Play Billing Library", "9.1.0"', "billing library disclosure")
require(menu, '"Jetpack Compose UI / Foundation / Material 3", "BOM 2026.08.00"', "Compose library disclosure")
require(menu, '"AndroidX Activity Compose", "1.13.0"', "Activity Compose disclosure")
require(menu, '"Material 3 Adaptive", "1.3.0"', "Adaptive library disclosure")

shortcut = "app/src/main/kotlin/com/sktpj/gbmoder/AppMenuShortcut.kt"
require(shortcut, 'testTag("app-menu")', "main menu shortcut")
require(shortcut, "Icons.Default.MoreVert", "Material menu icon")
require(shortcut, "AppMenuActivity::class.java", "main menu route")
require(shortcut, "MediaConversionActivity.EXTRA_RESOLUTION", "menu receives current settings")

prepare = "tools/prepare_billing_kotlin_v035.py"
require(prepare, "AppMenuShortcut(", "generated main UI menu insertion")
require(prepare, 'testTag("accessibility-disclosure-accept")', "accessibility disclosure accept")
require(prepare, 'testTag("accessibility-disclosure-decline")', "accessibility disclosure decline")
require(prepare, "R.string.accessibility_disclosure_body", "accessibility prominent disclosure text")
require(prepare, "actions.onAccessibilitySetup()", "accessibility settings only after affirmative action")

for values_dir in ("values", "values-ja", "values-zh-rCN", "values-ko"):
    strings = f"app/src/main/res/{values_dir}/menu_privacy_strings.xml"
    require(strings, 'name="menu_privacy_title"', f"{values_dir} privacy menu localization")
    require(strings, 'name="privacy_accessibility_body"', f"{values_dir} accessibility privacy text")
    require(strings, 'name="accessibility_disclosure_body"', f"{values_dir} prominent disclosure")
    require(strings, 'name="accessibility_disclosure_accept"', f"{values_dir} disclosure accept")
    require(strings, 'name="accessibility_disclosure_decline"', f"{values_dir} disclosure decline")

privacy = "docs/privacy-policy.html"
require(privacy, "AccessibilityService", "publishable accessibility privacy policy")
require(privacy, "MediaProjection", "publishable screen-capture privacy policy")
require(privacy, "Google Play Billing", "publishable billing privacy policy")
require(privacy, "GBModer GitHub Issues", "publishable contact route")

accessibility = "app/src/main/res/xml/accessibility_service_config.xml"
require(accessibility, 'android:canRetrieveWindowContent="true"', "declared accessibility data access")
reject(accessibility, 'android:isAccessibilityTool="true"', "app does not self-designate as accessibility tool")

print("MENU + PRIVACY + ACCESSIBILITY DISCLOSURE v0.1.43 AUTOMATED GATE: PASS")
