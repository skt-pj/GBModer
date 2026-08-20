# Third-party notices

## Misaki font

GBModer uses 8x8 Japanese bitmap glyph data derived from Misaki font for live Japanese text replacement in Game Boy 160x144 mode.

- Original font: Misaki font / Misaki Gothic
- Copyright (C) 2002-2015 Num Kadoma
- Source used by the build: `aloseed/misaki`
- Pinned commit: `44f702b209233175663050cbd0b6b58a531ebacb`
- `src/misaki.hpp` Git blob SHA-1: `b480a5c48b31092937731f6293e9bfad384c9aca`

Font license text from the source distribution:

> These fonts are free software. Unlimited permission is granted to use, copy, and distribute them, with or without modification, either commercially or noncommercially. THESE FONTS ARE PROVIDED "AS IS" WITHOUT WARRANTY.

The `aloseed/misaki` library code is MIT licensed. GBModer's build reads the pinned font tables and generates a compact Java representation; it does not copy the library implementation.
