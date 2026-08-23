#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (
    root
    / "app/build/generated/gbmoderGpu/java/com/sktpj/gbmoder/MainActivity.java"
).read_text()


def need(value: str, label: str) -> None:
    if value not in main:
        raise SystemExit(f"FAIL {label}: {value}")
    print(f"PASS {label}")


need("LinearLayout routeControls = new LinearLayout(this);", "dedicated route control container")
need("routeRoot.setPadding(0, 0, 0, 0);", "root does not use fixed top padding")
need("routeControls.setOnApplyWindowInsetsListener", "window inset listener")
need("windowInsets.getSystemWindowInsetTop()", "status bar top inset")
need("windowInsets.getDisplayCutout().getSafeInsetTop()", "display cutout top inset")
need("safeTop + routeTopMargin", "safe top plus intended margin")
need("safeLeft + routeSideMargin", "safe left plus intended margin")
need("safeRight + routeSideMargin", "safe right plus intended margin")
need("routeControls.addView(routeLabel, matchWrap());", "route label inside safe container")
need("routeControls.addView(captureRouteSpinner, matchWrap());", "route spinner inside safe container")
need("routeControls.addView(textRecognitionSwitch, matchWrap());", "text switch inside safe container")
need("routeRoot.addView(routeControls, matchWrap());", "safe controls attached before compose")
need("routeControls.post(routeControls::requestApplyInsets);", "insets requested after attach")

if "routeRoot.setPadding(dp(12), dp(20), dp(12), 0);" in main:
    raise SystemExit("FAIL fixed routeRoot top padding still present")
print("PASS fixed top padding removed")

controls_pos = main.find("routeRoot.addView(routeControls, matchWrap());")
compose_pos = main.find("routeRoot.addView(\n                composeView,", controls_pos)
if controls_pos < 0 or compose_pos <= controls_pos:
    raise SystemExit("FAIL safe route controls are not before Compose content")
print("PASS route controls before Compose content")
print("ROUTE INSETS AUTOMATED GATE: PASS")
