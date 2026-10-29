# QR code → https://greencity.parsalotfi.com/

Plain static QR of the bare URL (level M, 29×29 modules). No redirect service,
nothing expires: as long as the domain stays, every printed copy keeps working.

- `print-sheet.pdf` – A4, **print at 100 % / "actual size"**, cut on the dashed lines.
  - 7 × 24.5 mm case stickers: glue one into the 25 mm pocket on the lid
    (`3d-model/CreateLeafMacro.py`, `rebaje_qr`). No text, the case is the context.
  - 6 × 40 mm handout tiles with the URL printed underneath.
  - 1 × 80 mm for the presentation table.
- `greencity-qr.svg` – master vector (100 mm, quiet zone included) for slides, posters, anything else. Scale freely, keep black on white, never invert.
- `make.py` – regenerates everything (`python3 resources/qr/make.py`, needs `qrencode` + google-chrome).

Smallest safe print: about 20 mm. Scan distance ≈ 10 × code width.
