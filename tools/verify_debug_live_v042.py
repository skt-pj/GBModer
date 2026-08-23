#!/usr/bin/env python3
from pathlib import Path

repo = Path(__file__).resolve().parents[1]


def require(path: str, needle: str, label: str) -> None:
    text = (repo / path).read_text()
    if needle not in text:
        raise SystemExit(f"FAIL {label}: missing {needle!r} in {path}")
    print(f"PASS {label}")


require("version.properties", "VERSION_NAME=0.1.45", "version name")
require("version.properties", "VERSION_CODE=46", "version code")
require("tools/prepare_billing_release_v041.py", "finish_debug_live_bypass_v042.py", "debug live bypass finalizer registered")

billing = "app/build/generated/gbmoderBilling/kotlin/com/sktpj/gbmoder/LiveModeBilling.kt"
require(billing, "if (BuildConfig.DEBUG_FEATURES) {\n            appContext = context.applicationContext", "debug billing initialization bypass")
require(billing, "entitlementState = LiveModeEntitlementState.ACTIVE", "debug entitlement active")
require(billing, "fun isEntitled(): Boolean = BuildConfig.DEBUG_FEATURES || entitlementState == LiveModeEntitlementState.ACTIVE", "debug live entitlement is immediate")
require(billing, "if (BuildConfig.DEBUG_FEATURES) {\n            entitlementState = LiveModeEntitlementState.ACTIVE\n            canPurchase = false\n            return", "debug entitlement refresh stays active")
require(billing, "state == LiveModeEntitlementState.ACTIVE && !BuildConfig.DEBUG_FEATURES", "debug build hides subscription management")

main = "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java"
require(main, "if (!BuildConfig.DEBUG_FEATURES) {", "formal build live guard retained")
require(main, "if (LiveModeBillingManager.isEntitled()) {", "live start uses entitlement abstraction")
require(main, "beginStartFlow();", "live start route retained")

workflow = ".github/workflows/build-apk.yml"
require(workflow, "-PGBMODER_DEBUG_FEATURES=true :app:assembleDebug", "internal APK enables debug features")

print("DEBUG LIVE MODE v0.1.45 AUTOMATED GATE: PASS")
