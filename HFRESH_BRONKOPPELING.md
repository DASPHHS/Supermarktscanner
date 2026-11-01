# Aanvullende receptenbron: HFresh (1 november 2026)

Broncode: https://github.com/moshetrenk/hellofresh-database  
Website: https://hfresh.info/nl-NL  
API-documentatie: https://console.hfresh.info/docs/get-started

## Waarvoor de bron bruikbaar is

Deze onafhankelijke, onofficiële databank ondersteunt Nederlandse recepttitels,
bereidingstijden, tags, PDF-verwijzingen en receptenlinks. De REST API biedt
zoekfuncties en heeft een eigen Bearer-token (account/e-mailverificatie vereist).
De naam van de repository is **geen bewijs van kant-en-klare prijsdata**.

De publieke repository bevat Laravel-broncode, geen dump met geverifieerde
Nederlandse supermarktprijzen. In de API levert de receptenlijst geen
hoeveelheden per portie; detail-`ingredients` is een lijst van ingrediënten
en evenmin een controle van gewicht, verpakking of beschikbaarheid in Bleiswijk.
Daarom koppelt deze uitbreiding **geen enkele prijs** of
`quality=verified` aan een extern recept.

## Zonder API-token: direct koppelen in de Receptenstudio

1. Open een HelloFresh-recept in [de Receptenstudio](https://dasphhs.github.io/Supermarktscanner/hellofresh/) en klik op **Prijs & acties bekijken**.
2. Bij **HFresh-receptenkoppeling** staat **Zoek dit recept direct in HFresh**. Deze link opent de publieke Nederlandse HFresh-website met de recepttitel al als zoekterm (de originele applicatie ondersteunt het URL-veld `?search=`). Er is geen account of API-token nodig om daar handmatig te zoeken.
3. Zoek het recept in HFresh en controleer de bijgerechten/ingrediënten op de originele HelloFresh-kaart. Gelijknamige recepten kunnen verschillende versies zijn.
4. Plak de **volledige HFresh-receptpagina-URL** in het veld, bijvoorbeeld `https://hfresh.info/nl-NL/recipes/receptnaam-123`, en klik **Bewaar lokale koppeling**.
5. De gekozen bron verschijnt vervolgens bij het recept. Je kunt de koppeling verwijderen of later wijzigen. De bronfilter **HFresh-koppeling** laat alleen gekoppelde of niet-gekoppelde HelloFresh-recepten zien.

De ingevoerde link wordt alleen in **de browser-opslag** bewaard; hij wordt niet automatisch naar GitHub of een server verstuurd. Met **Exporteer mijn koppelingen** kun je alle handmatige verwijzingen downloaden als JSON. Met het JSON-bestand naast **Importeren** kun je ze op een andere browser/computer importeren. De import accepteert uitsluitend veilige Nederlandse HFresh-links en IDs die al tot je eigen HelloFresh-collectie behoren. Lokale links krijgen voorrang op eventuele automatische titelmatches.

Voor de duidelijkheid: een opgeslagen link is geen bevestiging dat de twee receptvarianten, hoeveelheden of voedingswaarden gelijk zijn. De externe bron geeft **geen** productprijs, korting of verpakkingsmatch door aan de scanner. Dit is uitsluitend een navigatie- en herkomstkoppeling.

## Veilige synchronisatie

De automatische API-sync vraagt uitsluitend een roterende selectie van 12 bestaande lokale recepttitels per week op (maximaal 25 op aanvraag), niet de volledige externe databank. De module bewaart een `scan_cursor` zodat volgende weken nieuwe titels worden gecontroleerd. De zoekopdrachten worden gespreid en alleen exact overeenkomende titels leveren een bronlink op. Houd rekening met de [HFresh-gebruiksvoorwaarden](https://console.hfresh.info/terms): vermijd geautomatiseerde massale opvragingen. Deze koppeling is geen volledige HFresh-import en voegt geen recepten uit HFresh aan de prijsranglijst toe.

Voor automatische aanvullingen is een eigen HFresh-API-token nodig. De optionele importmodule `hfresh_metadata.py` vergelijkt de exacte,
accent-onafhankelijk genormaliseerde Nederlandse titels met
`recipes_extracted.json`. Een niet-unieke externe titel wordt **niet**
gekoppeld. Alleen een gevalideerde openbare HFresh-link en optionele
bereidingstijd komen in `hellofresh/hfresh_matches.json` terecht.

Met een export op schijf:

```bash
python hfresh_metadata.py --catalog hfresh_export_nl.json
PYTHONPATH=. python -m unittest tests.test_hfresh_metadata
```

Of met geregistreerde toegang, uitsluitend server-side:

```bash
HFRESH_API_TOKEN='eigen-api-token' python hfresh_metadata.py
```

Voeg voor de geplande GitHub Action het repository-secret
`HFRESH_API_TOKEN` toe; de workflow `hfresh-crossrefs.yml` draait
wekelijks of handmatig. Zonder secret gebeurt er niets. Laat het token
nooit als bestand, client-JavaScript of Pages-config publiceren.
De API kan limieten of voorwaarden hebben; raadpleeg het portaal.
Een mislukte API-call laat de vorige snapshot intact. Een succesvolle zoekbatch zonder matches kan eerder verouderde koppelingen uit juist die gecontroleerde batch verwijderen; de rest blijft staan.

Alle prijsberekeningen blijven uitsluitend uit
`recipes_extracted.json`, `recipe_prices.json`,
`weekdeals_hellofresh.json` en bestaande verificatieprocedures komen.
Er vindt geen automatische ingredient-, portie- of OCR-correctie plaats.
Externe content wordt niet gekopieerd of hergepubliceerd: de site
verwijst naar de originele openbare receptpagina.

## Voorbehoud

De MIT-licentie van het GitHub-project geldt voor de software, niet per
definitie voor de receptteksten, foto's of database-inhoud van derden.
Gebruik de links als aanvullend hulpmiddel. Niet-exacte titels en meerdere mogelijke automatische matches worden weggelaten. **Een exact gelijkende titel is geen bewijs dat ook de receptvariant identiek is**. Daarom wordt dat expliciet bij de externe link getoond.
