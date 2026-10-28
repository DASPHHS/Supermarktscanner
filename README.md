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
