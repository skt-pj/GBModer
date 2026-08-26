#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_route_insets_source_v025.py <generated_src_root>")

root = Path(sys.argv[1])
package = root / "com/sktpj/gbmoder"


def read(name: str) -> str:
    return (package / name).read_text()


def write(name: str, text: str) -> None:
    (package / name).write_text(text)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


main = read("MainActivity.java")

main = replace_once(
    main,
    '''        LinearLayout routeRoot = new LinearLayout(this);
        routeRoot.setOrientation(LinearLayout.VERTICAL);
        routeRoot.setPadding(dp(12), dp(20), dp(12), 0);

        TextView routeLabel = text("処理ルート", 13, true);
''',
    '''        LinearLayout routeRoot = new LinearLayout(this);
        routeRoot.setOrientation(LinearLayout.VERTICAL);
        routeRoot.setPadding(0, 0, 0, 0);

        // This Java route selector sits outside the Compose Scaffold, so Compose's
        // WindowInsets.safeDrawing does not protect it. Keep the intended 20dp
        // visual margin, but add the actual system-bar/display-cutout safe inset.
        final int routeSideMargin = dp(12);
        final int routeTopMargin = dp(20);
        LinearLayout routeControls = new LinearLayout(this);
        routeControls.setOrientation(LinearLayout.VERTICAL);
        routeControls.setPadding(
                routeSideMargin,
                routeTopMargin,
                routeSideMargin,
                0
        );
        routeControls.setOnApplyWindowInsetsListener((view, windowInsets) -> {
            int safeLeft = Math.max(0, windowInsets.getSystemWindowInsetLeft());
            int safeTop = Math.max(0, windowInsets.getSystemWindowInsetTop());
            int safeRight = Math.max(0, windowInsets.getSystemWindowInsetRight());
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P
                    && windowInsets.getDisplayCutout() != null) {
                safeLeft = Math.max(
                        safeLeft,
                        windowInsets.getDisplayCutout().getSafeInsetLeft()
                );
                safeTop = Math.max(
                        safeTop,
                        windowInsets.getDisplayCutout().getSafeInsetTop()
                );
                safeRight = Math.max(
                        safeRight,
                        windowInsets.getDisplayCutout().getSafeInsetRight()
                );
            }
            view.setPadding(
                    safeLeft + routeSideMargin,
                    safeTop + routeTopMargin,
                    safeRight + routeSideMargin,
                    0
            );
            return windowInsets;
        });

        TextView routeLabel = text("処理ルート", 13, true);
''',
    "route controls safe inset container",
)

main = replace_once(
    main,
    "        routeRoot.addView(routeLabel, matchWrap());\n",
    "        routeControls.addView(routeLabel, matchWrap());\n",
    "route label container",
)
main = replace_once(
    main,
    "        routeRoot.addView(captureRouteSpinner, matchWrap());\n",
    "        routeControls.addView(captureRouteSpinner, matchWrap());\n",
    "route spinner container",
)
main = replace_once(
    main,
    '''        routeRoot.addView(textRecognitionSwitch, matchWrap());
        routeRoot.addView(
                composeView,
''',
    '''        routeControls.addView(textRecognitionSwitch, matchWrap());
        routeRoot.addView(routeControls, matchWrap());
        routeRoot.addView(
                composeView,
''',
    "route switch and compose container order",
)
main = replace_once(
    main,
    '''        setContentView(routeRoot);
    }
''',
    '''        setContentView(routeRoot);
        routeControls.post(routeControls::requestApplyInsets);
    }
''',
    "request route insets after attach",
)

write("MainActivity.java", main)
print("v0.1.25 Pixel 10a-safe route UI insets applied")
