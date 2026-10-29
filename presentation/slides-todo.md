# Slides: what to change before the pitch

The deck (`pitch.pdf`, Canva export of 29 Oct) is the story. The app is the source of truth for the
name and for what is on screen. These are the places where the two still differ, slide by slide.
Screenshots for the slides are in `screenshots/` (see its README for which file is for which slide).

## Slide 7 · "2026 Start evaluating now"
- Replace the app screenshot: it shows an old build on a desktop map with five chips. The app now has
  seven report types (Zu laut, Zu heiß, Schlechte Luft, Kein Schatten, Müll, Kaputte Straße, Anderes)
  and the sheet looks different on a phone. Use the phone screenshot of the report sheet.
- Optional second shot: the "Gemeldet" card right after a report, the answer is the feature.

## Slide 8 · "RANKING PAGE"
- The app has no separate ranking page. The ranking is the status filter in the Ebenen sheet:
  "Ohne Sensor" shows only the spots without a sensor, numbered by reports, and the card of the
  biggest one says "Platz 1 von 8 Stellen ohne Sensor, nach Meldungen." Use that screenshot and
  call the slide "Where the next sensor goes" rather than "Ranking page".

## Slide 9 · "We actually measured it"
- Picture of NoiseNode: a real photo of the printed case with the lid on, taken by the team.
- Graph of measurements: the NoiseNode's sensor card from the app (7 Tage and Alles), screenshot
  provided. The series before 28 Oct is seeded demo data (see `backend/README.md`), say "example
  week" if asked.

## Slide 10 · "We don't need to reinvent the wheel"
- "Heilbronn Meldet" is wrong. The product is called **Sag's Heilbronn** everywhere in the app
  (title, icon, manifest, about sheet). Replace the text with the leaf logo plus "Sag's Heilbronn"
  (`screenshots/logo-leaf.png`, or `app/static/favicon.svg`).

## Slide 4 · "40,200"
- Fine as is. The figure is the action plan's (Lärmaktionsplan Stufe IV, 2024). The underlying
  mapping report says 40,100; do not mix the two on stage.

## Slides 2–3 · Mängelmelder reports, "Status: Ungeprüft"
- Fine as is. Our loop closes it: the city's form gets conditions nobody can check, our app checks
  them against sensors and sends incidents (Müll, Schlagloch, Laterne) back to the Mängelmelder with
  a link. If you want a line for it: "Conditions come to us, incidents go back to the city."

## Before the demo (not slides)
- The deployed app at greencity.parsalotfi.com is an old build. Deploy the branch.
- The local database `backend/reports.db` still holds test texts ("Baustelle ab 6 Uhr (phone)",
  "kek", "kek2") on the Hauptbahnhof bubble. Back it up, then delete them (SQL in `agents/REPORT.md`).
- Handout: `handout/handout-de.pdf` and `handout-en.pdf`, print double-sided, 100 %.
- QR code stickers and the table code: `../resources/qr/print-sheet.pdf`, print at 100 %.
