# Audit Plated import — 28 oktober 2026

## Gecontroleerde workflow
- `plated_drive_manifest.json` bevat een **statische** lijst Drive-bestands-ID's. Nieuwe bestanden worden niet automatisch ontdekt.
- `.github/workflows/plated-import.yml` start om de vier uur, verwerkt standaard maximaal 60 pogingen per run en slaat voortgang op GitHub op.
- `import_plated_public_drive.py` downloadt tijdelijke PDF-kopieën, haalt tekst/OCR op via `drive_plated_sync.inspect` en bewaart uitsluitend een ongeverifieerde reviewqueue.
- `plated_drive_public_progress.json` is een momentopname, **geen volledige audit van de Google Drive-map**.

## Uitgevoerde correcties
1. **Geen deduplicatie uitsluitend op bestandsnaam**. Voorheen werd alleen het eerste bestand met dezelfde genormaliseerde titel gedownload. Dit kon verschillende versies of gerechten verbergen. Nu worden alle manifest-PDF's behandeld en wordt byte-identieke inhoud pas na download samengevoegd via SHA-256.
2. **Downloadfouten blijven herprobeerbaar**. Voorheen sloot een grens van drie fouten een bron permanent uit. Nu worden eerder mislukte bestanden achteraan geplaatst, zodat werkende links doorgaan en tijdelijke fouten later opnieuw geprobeerd worden.
3. **Duidelijkere volledigheidsmetingen**. Nieuwe velden geven afgeronde bronbestanden, bekeken bronbestanden, records in de controlequeue en herprobeerbare fouten aan. Het aantal unieke titels blijft een indicatie en geen definitieve deduplicatie.
4. **Regressietests** voor twee verschillende PDF's met dezelfde titel, exact identieke inhoud en herhaalde tijdelijke downloadfouten.

## Bewuste kwaliteitsgrenzen
- Alle OCR-records houden `pricing_eligible: false`; geen automatische toelating tot de supermarktprijsvergelijking.
- In sommige bron-PDF's worden Amerikaanse cups, ounces en aantal verpakkingen gebruikt; een conversie naar grammen zonder ingrediëntdichtheid of verpakkinggewicht is niet betrouwbaar.
- OCR op de eerste drie pagina's op 170 dpi kan fouten of gemiste informatie geven; het is **een voorlopige extractie**. Visuele controle blijft nodig, met name van hoeveelheidstabellen en de uitgangsporties.
- De huidige openbare GitHub-repository kan Drive-bestands-ID's publiceren. Beperk delen van auteursrechtelijk beschermd materiaal; zet bron-PDF's niet zonder toestemming in de repository.

## Vervolgverbeteringen, niet uitgevoerd
- Voor **volledige mapdekking**: geauthenticeerde Google Drive `files.list` met `nextPageToken` en submap-traversal, daarna periodiek manifest vernieuwen. Een openbare manifestlijst geeft geen automatische ontdekking van nieuwe bestanden.
- Voor betere OCR: 300 dpi en, waar nodig, beeldcorrectie (deskew/binarisatie) als aparte gecontroleerde fallback, en vergelijk de herkenning met de originele PDF.
- Voor robuuste productie: per bron een extractie-/validatiestatus, foutcategorie en expliciete handmatige goedkeuring van hoeveelheden voordat prijsberekening is toegestaan.
- Voor opslag: scheid een publieke, minimale catalogus van een niet-publieke bronverzameling.

## Bronnen en ontwerpkeuzes
- Google Drive API v3 files.list: https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list — paginering via nextPageToken.
- Tesseract OCR ImproveQuality: https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html — minimaal ~300 dpi, correctie van scheve scans en binarisatie.
- Eigen repository: `drive_plated_sync.py`, `import_plated_public_drive.py`, `.github/workflows/plated-import.yml`, `tests/test_import_plated_public_drive.py`.

**Let op:** het aantal verwerkte PDF's kan bij de eerste run na deze wijziging toenemen omdat dezelfde titel nu meerdere verschillende bronbestanden kan vertegenwoordigen. Dit is correct gedrag, geen kunstmatige vermenigvuldiging van recepten.
