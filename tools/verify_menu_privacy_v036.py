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


require("version.properties", "VERSION_NAME=0.1.37", "version name")
require("version.properties", "VERSION_CODE=38", "version code")
require("app/src/main/AndroidManifest.xml", '.AppMenuActivity', "menu activity registered")

menu = "app/src/main/kotlin/com/sktpj/gbmoder/AppMenuActivity.kt"
require(menu, 'testTag("app-menu-screen")', "menu screen")
require(menu, 'tag = "menu-diagnostics"', "diagnostics menu item")
require(menu, 'tag = "menu-libraries"', "libraries menu item")
require(menu, 'tag = "menu-privacy"', "privacy menu item")
require(menu, ".testTag(tag)", "menu item tag binding")
require(menu, 'tag = "menu-subscription"', "subscription menu item")
require(menu, 'tag = "menu-app-info"', "app info menu item")
require(menu, "LiveModeBillingManager.openSubscriptionManagement", "subscription management action")
require(menu, "BuildConfig.VERSION_NAME", "runtime version display")
require(menu, "BuildConfig.APPLICATION_ID", "runtime package display")

privacy = "app/src/main/kotlin/com/sktpj/gbmoder/PrivacyPolicyActivity.kt"
require(privacy, 'testTag("privacy-policy-screen")', "privacy screen")
require(privacy, 'testTag("privacy-policy-body")', "privacy body")
require(privacy, "PRIVACY_POLICY_URL", "public privacy policy URL")
require(privacy, "AccessibilityService", "accessibility disclosure")

manifest = "app/src/main/AndroidManifest.xml"
require(manifest, '.PrivacyPolicyActivity', "privacy activity registered")
require(manifest, '.AccessibilityDisclosureActivity', "accessibility disclosure registered")
reject(manifest, 'android:isAccessibilityTool="true"', "must not claim accessibility-tool exemption")

for values_dir in ("values", "values-ja", "values-zh-rCN", "values-ko"):
    strings = f"app/src/main/res/{values_dir}/menu_privacy_strings.xml"
    require(strings, 'name="menu_title"', f"{values_dir} menu localization")
    require(strings, 'name="privacy_policy_title"', f"{values_dir} privacy localization")
    require(strings, 'name="accessibility_disclosure_title"', f"{values_dir} accessibility disclosure")

require("docs/privacy-policy.html", "GBModer Privacy Policy", "publishable privacy page")

print("MENU + PRIVACY FEATURE GATE: PASS")
