#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def require(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle not in text:
        raise SystemExit(f"{label}: missing {needle!r} in {path}")


def reject(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle in text:
        raise SystemExit(f"{label}: unexpected {needle!r} in {path}")


require("app/build.gradle", "targetSdk 36", "Play target API")
require("app/build.gradle", "com.android.billingclient:billing:9.1.0", "Billing Library")
require("app/build.gradle", "prepareBillingKotlin", "billing Kotlin generation")
require("app/src/debug/AndroidManifest.xml", '.LiveModePaywallActivity', "debug-only paywall activity")
reject("app/src/main/AndroidManifest.xml", '.LiveModePaywallActivity', "formal release excludes paywall activity")

billing = "app/src/main/kotlin/com/sktpj/gbmoder/LiveModeBilling.kt"
require(billing, 'PRODUCT_ID = "live_mode"', "subscription product")
require(billing, 'BASE_PLAN_ID = "monthly"', "subscription base plan")
require(billing, "QueryPurchasesParams", "entitlement restore")
require(billing, "Purchase.PurchaseState.PURCHASED", "purchased handling")
require(billing, "Purchase.PurchaseState.PENDING", "pending handling")
require(billing, "acknowledgePurchase", "purchase acknowledgement")
require(billing, "formattedPrice", "localized Play price")
require(billing, "LiveModePaywallActivity", "dedicated paywall")
require(billing, "openSubscriptionManagement", "subscription management")

prepare = "tools/prepare_billing_kotlin_v035.py"
require(prepare, "LiveModeSubscriptionCard()", "main-screen subscription card implementation")
require(prepare, "ライブモード開始", "live button labeling implementation")

gate = "tools/finish_billing_gate_v035.py"
require(gate, "LiveModeBillingManager.isEntitled()", "live entitlement gate")
require(gate, "LiveModePaywallActivity.class", "unsubscribed paywall route")
require(gate, "this::beginStartFlow", "continue requested live start after purchase")

for values_dir in ("values", "values-ja", "values-zh-rCN", "values-ko"):
    strings = f"app/src/main/res/{values_dir}/billing_strings.xml"
    require(strings, 'name="live_mode_paywall_headline"', f"{values_dir} paywall localization")
    require(strings, 'name="live_mode_other_free"', f"{values_dir} free-feature disclosure")
    require(strings, 'name="live_mode_auto_renew"', f"{values_dir} renewal disclosure")
    require(strings, 'name="live_mode_cancel_info"', f"{values_dir} cancellation disclosure")

require(
    "app/src/main/kotlin/com/sktpj/gbmoder/GbModerComposeUi.kt",
    "UnifiedConversionControls(",
    "free conversion UI retained",
)
reject(
    "app/src/main/java/com/sktpj/gbmoder/MediaFileConverter.java",
    "LiveModeBillingManager",
    "file conversion must remain free",
)

print("LIVE BILLING DEBUG FEATURE GATE: PASS")
