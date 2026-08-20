#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_startup_source_v021.py <generated_src_root>")

root = Path(sys.argv[1])
path = root / "com/sktpj/gbmoder/MainActivity.java"
text = path.read_text()

old_import = "import android.app.Activity;\n"
new_import = "import androidx.activity.ComponentActivity;\n"
old_class = "public class MainActivity extends Activity {"
new_class = "public class MainActivity extends ComponentActivity {"

if text.count(old_import) != 1:
    raise SystemExit(f"ComponentActivity import migration expected 1 Activity import, got {text.count(old_import)}")
if text.count(old_class) != 1:
    raise SystemExit(f"ComponentActivity migration expected 1 Activity base class, got {text.count(old_class)}")

text = text.replace(old_import, new_import, 1)
text = text.replace(old_class, new_class, 1)
path.write_text(text)
print("startup lifecycle owner fix v0.1.21 applied")
