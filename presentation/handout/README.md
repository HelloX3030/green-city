# Handout – Sag's Heilbronn (table sheet, DE + EN)

One A4 sheet per language, two pages (front: team + story + QR, back: how it works + what exists + the ask), styled after the pitch deck (navy/lime, IBM Plex Mono) and the app (grey cards, green leaf, Inter).

- `handout-de.pdf`, `handout-en.pdf` – print these. A4, **double-sided, flip on long edge**, 100 % / "actual size" (no "fit to page"), colour if you can; the greyscale fallback was checked.
- `handout-de.html`, `handout-en.html` – the self-contained sources (inline CSS, leaf and QR); open in a browser to proofread.
- `make.py` – regenerates all four: `python3 presentation/handout/make.py` (needs google-chrome; `--virtual-time-budget` waits for the Google Fonts, offline it falls back to DejaVu Sans Mono / system sans). Texts are in the `TEXT` dict, layout and CSS below it.
- QR: 44 mm, taken from `resources/qr/greencity-qr.svg`, links to https://greencity.parsalotfi.com/ .
