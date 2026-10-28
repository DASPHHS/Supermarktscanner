# Plated: automatische PDF-import

De workflow [Plated recepten automatisch importeren](https://github.com/DASPHHS/Supermarktscanner/actions/workflows/plated-import.yml) voert dagelijks een **hervatbare batchimport** uit. De geüploade ZIP van 2,12 GB is niet nodig: de workflow gebruikt de losse pdf-bestanden in Google Drive.

## Eenmalig toegang geven (vereist)

1. Open Google Cloud Console, kies een project en schakel de **Google Drive API** in.
2. Maak een **serviceaccount** aan en maak voor dit account een JSON-sleutel. Bewaar deze sleutel privé; zet hem nooit in een publieke repository, issue of chat.
3. Deel de Google Drive-map **RECEPTEN / Plated recipes from Marc Hummel [Download folder]** met het e-mailadres van het serviceaccount als *Lezer*. Alleen deze map hoeft gedeeld te worden.
4. Ga naar GitHub → **DASPHHS/Supermarktscanner** → **Settings → Secrets and variables → Actions → New repository secret**. Maak een secret met exact de naam `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON` en plak de **volledige JSON-inhoud** van de sleutel in het geheime waardeveld.
5. Optioneel: stel bij **Variables** `PLATED_DRIVE_FOLDER_ID` in op de ID van de nieuwe map: `1gXrQK_EM3QvWPMYvGDze8TmpvD0MZP3K`. Zonder die variabele gebruikt het script dezelfde standaardmap.
6. Start via **Actions → Plated recepten automatisch importeren → Run workflow** de eerste batch. De daaropvolgende batches draaien dagelijks om 04:40 UTC. Een GitHub-schedule is best effort, niet op de minuut gegarandeerd.

## Werking en controle

- Haalt via Google Drive API alle pagina's van de folderlijst op, en verwerkt standaard 12 nieuwe unieke titels per batch.
- Herkent identieke reeds gedownloade bestanden via SHA-256 en bestandsnaamvarianten via titel-normalisatie.
- Leest pdf-tekst met Poppler; bij scans wordt OCR via Tesseract uitgevoerd.
- Probeert oorspronkelijke serveergrootte, ingrediëntenregels en voorlopige hoeveelheden voor vier personen te bepalen.
- Bewaart voortgang in `plated_sync_state.json`, OCR-resultaten in `plated_review_queue.json` en statistiek in `plated_sync_progress.json`; vervolgruns pakken de volgende documenten.
- **Kwaliteitsgrens:** OCR is niet foutloos. Elke voorlopige ingrediëntenregel krijgt `quality: unverified_ocr`, ieder automatisch geïmporteerd recept blijft `pricing_eligible: false`. Er worden dus geen onjuiste kassabedragen gepresenteerd.
- De zes eerder visueel gecontroleerde Plated-recepten blijven apart in `plated_recipes.json`, zonder ze door nieuwe OCR-output te overschrijven.
- De dagelijkse winkelprijsvergelijking draait apart; zonder gecontroleerde ingrediënten en productgewichten kan deze niet betrouwbaar op alle Plated-recepten worden toegepast.

## Fouten oplossen

Als de actie bij het controleren van de Drive-koppeling stopt, ontbreekt de secret. Bij een HTTP 403 is doorgaans de map niet met het serviceaccount gedeeld of is de Drive API niet ingeschakeld. Bij een OCR-fout verschijnt het betreffende bestand in de voortgangsrapportage; die kaart blijft voor latere controle beschikbaar.

De workflow gebruikt alleen de read-only Drive-scope; de GitHub write-token is uitsluitend bedoeld voor de JSON-voortgangsbestanden. Controleer iedere scan voordat je definitieve vierportiehoeveelheden en een winkelprijs accepteert.
