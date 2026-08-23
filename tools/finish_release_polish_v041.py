#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: finish_release_polish_v041.py <generated_kotlin_root>")

path = Path(sys.argv[1]) / "com/sktpj/gbmoder/AppMenuActivity.kt"
text = path.read_text()


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    text = text.replace(old, new, 1)


for entry in (
    '        LibraryInfo("JUnit", "4.13.2", "Eclipse Public License 1.0", false),\n',
    '        LibraryInfo("Android Gradle Plugin", "9.3.0", "Build tool", false),\n',
    '        LibraryInfo("Kotlin Compose plugin", "2.3.21", "Build tool", false),\n',
):
    replace_once(entry, "", "remove development-only library entry")

replace_once(
    '''                MaterialText(
                    text = if (library.runtime) {
                        stringResource(R.string.library_scope_runtime)
                    } else {
                        stringResource(R.string.library_scope_build_test)
                    },
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
''',
    "",
    "remove internal runtime/build scope label",
)

replace_once(
    '            MaterialText(stringResource(R.string.menu_package_format, context.packageName))\n',
    "",
    "remove package identifier from release-facing app info",
)

replace_once(
    '        body = stringResource(R.string.privacy_network_body),',
    '        body = stringResource(R.string.privacy_network_body_v041),',
    "release network privacy copy",
)
replace_once(
    '        body = stringResource(R.string.privacy_retention_body),',
    '        body = stringResource(R.string.privacy_retention_body_v041),',
    "release retention privacy copy",
)

path.write_text(text)
print("v0.1.41 release menu removes development-only details and uses release privacy copy")
