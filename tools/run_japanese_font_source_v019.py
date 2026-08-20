#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: run_japanese_font_source_v019.py <generated_src_root>")

script_path = Path(__file__).with_name("finish_japanese_font_source_v019.py")
source = script_path.read_text()
old = '''accessibility = read("FilterAccessibilityService.java")
replacements = {
    "FontMinRenderer.getTextTileWidth(text)": "MixedGbTextRenderer.getTextTileWidth(text)",
    "FontMinRenderer.getTextTileHeight(text)": "MixedGbTextRenderer.getTextTileHeight(text)",
    "FontMinRenderer.canRenderText(text, tileX, tileY)": "MixedGbTextRenderer.canRenderText(text, tileX, tileY)",
    "FontMinRenderer.drawLogicalText(": "MixedGbTextRenderer.drawLogicalText(",
    "visible ASCII Accessibility text": "visible Unicode Accessibility text",
    "font_min is drawn": "font_min/Misaki 8x8 glyphs are drawn",
}
for old, new in replacements.items():
    if old not in accessibility:
        raise SystemExit(f"Japanese integration marker missing: {old}")
    accessibility = accessibility.replace(old, new)
write("FilterAccessibilityService.java", accessibility)
'''
new = '''accessibility = read("FilterAccessibilityService.java")
required_replacements = {
    "FontMinRenderer.getTextTileWidth(text)": "MixedGbTextRenderer.getTextTileWidth(text)",
    "FontMinRenderer.getTextTileHeight(text)": "MixedGbTextRenderer.getTextTileHeight(text)",
    "FontMinRenderer.canRenderText(text, tileX, tileY)": "MixedGbTextRenderer.canRenderText(text, tileX, tileY)",
    "FontMinRenderer.drawLogicalText(": "MixedGbTextRenderer.drawLogicalText(",
}
for marker, replacement in required_replacements.items():
    if marker not in accessibility:
        raise SystemExit(f"Japanese integration marker missing: {marker}")
    accessibility = accessibility.replace(marker, replacement)

# Documentation wording is deliberately optional: generated comments may change
# without changing the functional integration points above.
accessibility = accessibility.replace(
    "visible ASCII Accessibility text",
    "visible Unicode Accessibility text",
)
accessibility = accessibility.replace(
    "font_min is drawn",
    "font_min/Misaki 8x8 glyphs are drawn",
)
write("FilterAccessibilityService.java", accessibility)
'''
if old not in source:
    raise SystemExit("v0.1.19 integration block not found")
source = source.replace(old, new, 1)
namespace = {"__name__": "__main__", "__file__": str(script_path)}
exec(compile(source, str(script_path), "exec"), namespace, namespace)
