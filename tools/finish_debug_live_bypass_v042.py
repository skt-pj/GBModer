#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_debug_live_bypass_v042.py <generated_kotlin_root>")

path = Path(sys.argv[1]) / "com/sktpj/gbmoder/LiveModeBilling.kt"
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    "    fun initialize(context: Context) {\n        if (appContext == null) {\n",
    "    fun initialize(context: Context) {\n"
    "        if (BuildConfig.DEBUG_FEATURES) {\n"
    "            appContext = context.applicationContext\n"
    "            entitlementState = LiveModeEntitlementState.ACTIVE\n"
    "            formattedPrice = null\n"
    "            canPurchase = false\n"
    "            return\n"
    "        }\n"
    "        if (appContext == null) {\n",
    "debug build entitlement initialization",
)

replace_once(
    "    fun isEntitled(): Boolean = entitlementState == LiveModeEntitlementState.ACTIVE\n",
    "    fun isEntitled(): Boolean = BuildConfig.DEBUG_FEATURES || entitlementState == LiveModeEntitlementState.ACTIVE\n",
    "debug build entitlement bypass",
)

replace_once(
    "    fun refreshEntitlement() {\n        val client = billingClient\n",
    "    fun refreshEntitlement() {\n"
    "        if (BuildConfig.DEBUG_FEATURES) {\n"
    "            entitlementState = LiveModeEntitlementState.ACTIVE\n"
    "            canPurchase = false\n"
    "            return\n"
    "        }\n"
    "        val client = billingClient\n",
    "debug build entitlement refresh",
)

replace_once(
    "                if (state == LiveModeEntitlementState.ACTIVE) {\n"
    "                    OutlinedButton(onClick = { LiveModeBillingManager.openSubscriptionManagement(context) }) {\n",
    "                if (state == LiveModeEntitlementState.ACTIVE && !BuildConfig.DEBUG_FEATURES) {\n"
    "                    OutlinedButton(onClick = { LiveModeBillingManager.openSubscriptionManagement(context) }) {\n",
    "hide subscription management in debug build",
)

path.write_text(text)
print("v0.1.42 debug-feature live mode bypasses Play entitlement and starts directly")
