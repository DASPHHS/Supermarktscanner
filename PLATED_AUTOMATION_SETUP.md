# Plated automatisch scannen vanuit Google Drive (actuele methode)

**De huidige GitHub-workflow vereist geen serviceaccount, geen sleutel en geen handmatige upload van de PDF's.** De map heeft al de instelling 'iedereen met de link: lezer'. GitHub downloadt bestanden uit het op 28 oktober 2026 vastgelegde manifest in batches naar de tijdelijke GitHub Actions-runner.

De workflow **Plated pdfs scannen** gebruikt `plated_drive_manifest.json` (533 PDF-id's), `import_plated_public_drive.py` en OCR met Tesseract. De originele PDF-bytes komen niet in de GitHub-repository, alleen de voorlopige OCR-resultaten en voortgangsgegevens. Alle automatisch geëxtraheerde gerechten blijven `pricing_eligible: false` totdat de ingrediënten en de vierportiehoeveelheden gecontroleerd zijn.

**Let op:** dit is een openbare repository. Het manifest bevat Drive-bestands-ID's; omdat de map leesbaar is voor iedereen met de link, kunnen de bronbestanden daardoor mogelijk ook voor anderen bereikbaar zijn. Wie dit privé wil houden moet de map delen met beperktere rechten en een privébron met passende authenticatie gebruiken.

Nieuwe PDF's die later aan de Drive-map worden toegevoegd komen **niet automatisch** in het huidige manifest. De manifestlijst moet dan opnieuw ververst worden. Als de Drive-downloads worden geblokkeerd of beperkt, meldt de workflow deze fouten. De acties zijn te bekijken op https://github.com/DASPHHS/Supermarktscanner/actions/workflows/plated-import.yml.

## Alternatief: PDF's uploaden naar GitHub

PDF's die expliciet in `plated_pdfs/` worden geplaatst, worden door dezelfde workflow automatisch gescand. **Let op**: deze repository is openbaar en kan daarom ongeschikt zijn om auteursrechtelijk beschermde PDF's te uploaden. GitHub accepteert doorgaans maximaal 25 MiB per bestand via de webinterface en maximaal 100 MiB per bestand via regulier Git. De volledige collectie van ruim 2 GB hoort niet zomaar in de openbare broncoderepository.
