#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: prepare_all_sources_v020.py <source_java_root> <generated_java_root>")

repo = Path(__file__).resolve().parents[1]
source_root = Path(sys.argv[1]).resolve()
generated_root = Path(sys.argv[2]).resolve()

commands = [
    [sys.executable, str(repo / "tools/prepare_gpu_source.py"), str(source_root), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_gpu_source_v015.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_capture_source_v016.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_font_min_source_v017.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_font_min_source_v018.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/run_japanese_font_source_v019.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_compose_ui_source_v020.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_startup_source_v021.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_text_route_source_v022.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_text_layout_source_v023.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_text_scroll_sync_source_v024.py"), str(generated_root)],
    [sys.executable, str(repo / "tools/finish_route_insets_source_v025.py"), str(generated_root)],
]

for command in commands:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=repo, check=True)

print("all generated sources prepared for v0.1.25", flush=True)
