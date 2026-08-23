#!/usr/bin/env python3
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

UPSTREAM_REPOSITORY = "https://github.com/skt-pj/2048TD.git"
UPSTREAM_COMMIT = "2fa62d4b636e3e403466256dc452bf72fe6fda42"
UPSTREAM_VERSION_NAME = "0.1.7"
UPSTREAM_VERSION_CODE = "8"

if len(sys.argv) != 2:
    raise SystemExit("usage: prepare_2048td_content_v043.py <generated_kotlin_root>")

output_root = Path(sys.argv[1]).resolve()
if output_root.exists():
    shutil.rmtree(output_root)
output_root.mkdir(parents=True, exist_ok=True)

with tempfile.TemporaryDirectory(prefix="gbmoder-2048td-") as temporary_directory:
    checkout = Path(temporary_directory) / "2048TD"
    checkout.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(
        ["git", "-C", str(checkout), "remote", "add", "origin", UPSTREAM_REPOSITORY],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(checkout), "fetch", "-q", "--depth=1", "origin", UPSTREAM_COMMIT],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(checkout), "checkout", "-q", "--detach", "FETCH_HEAD"],
        check=True,
    )

    resolved_commit = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if resolved_commit != UPSTREAM_COMMIT:
        raise SystemExit(f"unexpected 2048TD commit: {resolved_commit}")

    version_properties = {}
    for line in (checkout / "version.properties").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            version_properties[key.strip()] = value.strip()
    if version_properties.get("VERSION_NAME") != UPSTREAM_VERSION_NAME:
        raise SystemExit("unexpected 2048TD VERSION_NAME")
    if version_properties.get("VERSION_CODE") != UPSTREAM_VERSION_CODE:
        raise SystemExit("unexpected 2048TD VERSION_CODE")

    source = checkout / "app/src/main/java/com/sktpj/td2048"
    destination = output_root / "com/sktpj/td2048"
    shutil.copytree(source, destination)

    standalone_activity = destination / "MainActivity.kt"
    if standalone_activity.exists():
        standalone_activity.unlink()

    game_screen = destination / "GameScreen.kt"
    game_text = game_screen.read_text()
    old = '''    BackHandler(enabled = true) {
        // System back key / back gesture is intentionally disabled.
    }
'''
    new = '''    BackHandler(enabled = false) {
        // Embedded in GBModer: system back exits the content activity.
    }
'''
    count = game_text.count(old)
    if count != 1:
        raise SystemExit(f"2048TD back-handler patch: expected exactly one match, got {count}")
    game_screen.write_text(game_text.replace(old, new, 1))

print(
    f"2048TD content prepared: version={UPSTREAM_VERSION_NAME} "
    f"versionCode={UPSTREAM_VERSION_CODE} commit={UPSTREAM_COMMIT}",
    flush=True,
)
