## Indicatieve prijsranglijst met normgewichten (29 oktober 2026)

De HelloFresh-pagina toont nu complete **prijsramingen voor twee personen**.
Bij elk recept staan gebruikte normgewichten, productkeuzes, kassabedragen en
restanten. Alleen volledige ramingen tellen mee. De kaartoptie schakelt
herkenbare Bonus-/kaartacties mee; bundels worden als hele verpakkingen berekend.
De oude exacte verificatiestatus blijft los daarvan bestaan.

Lees [de rekenmethodiek](PRIJSRAMING_METHODIEK.md). Voor controles:
`PYTHONPATH=. pytest -q` en `npm ci && npm test`.

# Supermarktscanner × HelloFresh

Statische browser op **https://dasphhs.github.io/Supermarktscanner/**, plus het bestaande Streamlit-project (`app.py`).

## Live onderdelen

- `index.html`: doorzoekbare HelloFresh-receptenindex, bronverwijzingen, ingrediënten voor vier porties en gecontroleerd prijsdekkingslabel.
- `recipes_extracted.json`: 225 voorlopig unieke, automatisch uit 14 tekst-pdf's afgeleide receptrecords (332 kaarten vóór titel-deduplicatie). **Alle records moeten nog handmatig gecontroleerd worden.**
- `sync_prices.py`: strikte prijsvergelijker per supermarkt. Hij vergelijkt alleen producten met passende namen, eenheden en werkelijk te kopen hele verpakkingen. Ontbrekende matches blijven ontbrekend, geen verzonnen kassabedragen.
- `recipe_prices.json`: door GitHub Actions geproduceerde schapprijssnapshot. Alleen bruikbaar met actuele datum; maximaal drie dagen oud in de browser.
- `.github/workflows/daily-prices.yml`: automatische prijsverversing, dagelijks om 06:15 UTC, plus bij wijziging van import/workflow. Controleert eerst de matchingtests.
- Prijssync gebruikt [Checkjebon open product data](https://github.com/supermarkt/checkjebon). **Dit is géén officiële supermarkt-API en geen bewijs van een lopende Bonus-/Jumbo-/Lidl-actie.** AH/Jumbo worden beter gedekt dan Lidl; prijzen verschillen per filiaal.

## Eerlijke status

1. De pdf-import is een **conceptdatabase**, geen complete gecertificeerde verzameling. Het extra bestand `Hellofresh recepten.pdf` heeft 61 beeldpagina's zonder leesbare tekstlaag. Deze zijn nog niet betrouwbaar geïmporteerd. 
2. Ingrediënten uit de andere 14 pdf's kunnen door dubbele tekstlagen, afwijkende tabelopmaak of eenheden fout bevatten; daarom `quality=needs_manual_verification`. Originele titel, bestandsnaam, paginanummer en bronstappen zijn opgenomen voor controle.
3. Voor een betrouwbaar totaal moeten **alle ingrediënten matchen**, inclusief stuks/grammen/volume; anders komt er bewust `prijs onbekend` te staan. Productmatch en prijsdekking zijn dus nog zeer beperkt.
4. De dagelijkse Checkjebon-data bevat actuele supermarktprijzen, maar geen onafhankelijk geverifieerde aanbieding/van-voor-prijs. Een *vandaag goedkoopste recept* mag pas geclaimd worden na volledige matching, controle van porties én controle van relevante acties.
5. De originele HelloFresh-kaarten moeten mogelijk auteursrechtelijk beschermd zijn. Let op dat deze repository **openbaar** is; publiceer alleen inhoud waarvoor je toestemming hebt.

## Lokaal gebruiken

```sh
python -m http.server 8000
# open http://localhost:8000
```

De GitHub Pages-site heeft géén Streamlit-server nodig. Voor handmatige prijsinvoer ondersteunt de webapp een CSV:
`store,product,price_eur,quantity_g,valid_from,valid_until,source_url`.

Voor de oude Streamlit-weergave:

```sh
pip install -r requirements.txt
streamlit run app.py
```

Voor tests en live prijssynchronisatie:

```sh
PYTHONPATH=. pytest -q
python sync_prices.py
```

**Geen prijs claimen wanneer de controle ontbreekt.** Het uiteindelijke doel is een betrouwbare ranglijst van voordelige, gezonde HelloFresh-recepten voor 2 personen × 2 dagen (4 porties) bij Lidl, Jumbo en AH.

## Plated (Marc Hummel): gecontroleerde import in uitvoering

De tweede bron staat in de gekoppelde Google Drive-map `Plated recipes from Marc Hummel [Download folder]`. De website ondersteunt nu een bronfilter voor **HelloFresh** en **Plated**. `plated_recipes.json` bevat voorlopig één handmatig nagekeken *voorbeeldrecord* van de zalm-kokoscurry, met ingrediënten opgeschaald van 2 naar 4 porties, bronverwijzing en expliciete kwaliteitsstatus `needs_manual_verification`. Omdat Amerikaanse maateenheden en productmatches nog niet gecontroleerd zijn, heeft dit record `pricing_eligible: false` en verschijnt er dus geen verzonnen supermarktprijs.

De map bevat veel dubbele PDF-bestanden (`dupe_`) en deels gescande documenten die nog geen uitleesbare tekst opleveren. Om alles correct te importeren moeten de documenten op bestandsinhoud en recepttitel worden gededupliceerd, gescande bestanden gecontroleerd worden, hoeveelheden naar consistente metrische eenheden worden vertaald en alle ingrediënten voor vier porties gevalideerd worden. **De volledige Plated-catalogus is nog niet geïmporteerd.** Een automatische Google Drive-sync in GitHub Actions vereist aparte authenticatie en is hier nog niet geconfigureerd. Publiceer geen gekopieerde volledige receptinstructies uit derden-PDF's in de publieke repository; de website verwijst terug naar het bronbestand.

### Plated-index en hercontrole, 28 oktober 2026

- `plated_catalog_pending.json` inventariseert de eerste 1.000 bestanden van de gekoppelde Google Drive-map: 936 PDF's, voorlopig 861 unieke op titel gebaseerde groepen en 75 mogelijke duplicaten. **Dit is geen volledige mapinventaris en geen inhoudelijke deduplicatie.**
- De publieke website laat voorlopige Plated-titels apart zien als **controle nodig** wanneer bron = Plated. Ze komen niet in het overzicht met volledig geprijsde gerechten.
- `plated_import.py` kan de lokaal gedownloade PDF-map omzetten naar een overzicht met originele bestandsnamen, OCR-tekstfragmenten en review-status. Benodigd: `pdftotext`, `pdftoppm` (Poppler) en `tesseract` met Engels taalpakket. Voorbeeld: `python plated_import.py /pad/naar/plated-pdfs --out plated_import_queue.json`.
- **Belangrijk:** deze importer leest nog geen vierportiehoeveelheden automatisch foutloos uit. OCR levert bij oude scans vaak verkeerd herkende breuken, maateenheden en tekens. Daarom blijft `pricing_eligible: false` totdat elke receptkaart zorgvuldig gecontroleerd en de Amerikaanse maateenheden naar metrisch zijn vertaald.
- De Google Drive-connector waarmee in deze conversatie de map is gelezen, verleent niet automatisch toegang vanuit GitHub Actions. Voor echt dagelijkse import is een afzonderlijke beveiligde Drive-API-koppeling of export van de map nodig.

### Plated-kwaliteitscontrole (28 oktober 2026)

Zes echte Plated-recepten staan nu met ingrediënten voor vier porties in `plated_recipes.json`, waarvan vijf vanaf twee gescande pagina's visueel zijn gecontroleerd. Alle zes staan terecht op `pricing_eligible: false`: stuks, blikjes of zakjes hebben nog onduidelijke netto gewichten en kunnen nog niet verantwoord automatisch worden geprijsd. De originele vierportiekaart Teriyaki Salmon Tacos is niet opnieuw verdubbeld.

`plated_validation.py` verwerkt Amerikaanse breuken, onderscheidt gewichts-oz van fl oz en cups, controleert de uitgangsporties en detecteert identieke pdf's met SHA-256. Tests draaien met `PYTHONPATH=. pytest -q`. Cups zijn volumes, geen generieke grammen. De circa 2,12 GB Drive-ZIP overschrijdt de huidige connectorlimiet van 256 MiB. De mapinventaris met 510 voorlopige titelgroepen omvat niet alle inhoudelijk gecontroleerde recepten; volledige bulkimport vergt een aparte downloadroute.
