#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_debug_features_v041.py <generated_src_root>")

path = Path(sys.argv[1]) / "com/sktpj/gbmoder/MainActivity.java"
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


replace_once(
    "        LiveModeBillingManager.initialize(this);\n        composeUiState = new GbModerUiState();\n",
    "        if (BuildConfig.DEBUG_FEATURES) {\n"
    "            LiveModeBillingManager.initialize(this);\n"
    "        }\n"
    "        composeUiState = new GbModerUiState();\n",
    "debug-only billing initialization",
)

replace_once(
    "                uiTextRecognitionEnabled = textRecognitionEnabled;\n"
    "                if (LiveModeBillingManager.isEntitled()) {\n",
    "                uiTextRecognitionEnabled = textRecognitionEnabled;\n"
    "                if (!BuildConfig.DEBUG_FEATURES) {\n"
    "                    setUiStatus(\"ライブモードはデバッグビルドでのみ利用できます\");\n"
    "                    return;\n"
    "                }\n"
    "                if (LiveModeBillingManager.isEntitled()) {\n",
    "defensive live start flag gate",
)

replace_once(
    "        LiveModeBillingManager.refreshEntitlement();\n"
    "        int paywallResult = LiveModeBillingManager.consumePaywallResult();\n",
    "        int paywallResult = 0;\n"
    "        if (BuildConfig.DEBUG_FEATURES) {\n"
    "            LiveModeBillingManager.refreshEntitlement();\n"
    "            paywallResult = LiveModeBillingManager.consumePaywallResult();\n"
    "        }\n",
    "debug-only billing resume",
)

path.write_text(text)
print("v0.1.41 generated live flow gated by BuildConfig.DEBUG_FEATURES")
