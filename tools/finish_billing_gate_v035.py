#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_billing_gate_v035.py <generated_src_root>")

path = Path(sys.argv[1]) / "com/sktpj/gbmoder/MainActivity.java"
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    "    private boolean pendingStartAfterAccessibility = false;\n",
    "    private boolean pendingLiveStartAfterPaywall = false;\n"
    "    private boolean pendingStartAfterAccessibility = false;\n",
    "live paywall pending field",
)

replace_once(
    "        composeUiState = new GbModerUiState();\n",
    "        LiveModeBillingManager.initialize(this);\n"
    "        composeUiState = new GbModerUiState();\n",
    "billing initialization",
)

replace_once(
    "                uiTextRecognitionEnabled = textRecognitionEnabled;\n"
    "                beginStartFlow();\n",
    "                uiTextRecognitionEnabled = textRecognitionEnabled;\n"
    "                if (LiveModeBillingManager.isEntitled()) {\n"
    "                    beginStartFlow();\n"
    "                } else {\n"
    "                    pendingLiveStartAfterPaywall = true;\n"
    "                    LiveModeBillingManager.clearPaywallResult();\n"
    "                    startActivity(new Intent(MainActivity.this, LiveModePaywallActivity.class));\n"
    "                }\n",
    "live start entitlement gate",
)

replace_once(
    "    protected void onResume() {\n"
    "        super.onResume();\n",
    "    protected void onResume() {\n"
    "        super.onResume();\n"
    "        LiveModeBillingManager.refreshEntitlement();\n"
    "        int paywallResult = LiveModeBillingManager.consumePaywallResult();\n"
    "        if (pendingLiveStartAfterPaywall) {\n"
    "            if (paywallResult == 1 && LiveModeBillingManager.isEntitled()) {\n"
    "                pendingLiveStartAfterPaywall = false;\n"
    "                postUiDelayed(this::beginStartFlow, 100L);\n"
    "            } else if (paywallResult == 2) {\n"
    "                pendingLiveStartAfterPaywall = false;\n"
    "            }\n"
    "        }\n",
    "resume entitlement reconciliation",
)

path.write_text(text)
print("v0.1.35 live-mode billing gate applied")
