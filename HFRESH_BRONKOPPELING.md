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

## Veilige synchronisatie

De automatische API-sync vraagt uitsluitend een roterende selectie van 12 bestaande lokale recepttitels per week op (maximaal 25 op aanvraag), niet de volledige externe databank. De module bewaart een `scan_cursor` zodat volgende weken nieuwe titels worden gecontroleerd. De zoekopdrachten worden gespreid en alleen exact overeenkomende titels leveren een bronlink op. Houd rekening met de [HFresh-gebruiksvoorwaarden](https://console.hfresh.info/terms): vermijd geautomatiseerde massale opvragingen. Deze koppeling is geen volledige HFresh-import en voegt geen recepten uit HFresh aan de prijsranglijst toe.

De optionele importmodule `hfresh_metadata.py` vergelijkt de exacte,
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
Een mislukte API-call of nul matches laat de vorige snapshot intact.

Alle prijsberekeningen blijven uitsluitend uit
`recipes_extracted.json`, `recipe_prices.json`,
`weekdeals_hellofresh.json` en bestaande verificatieprocedures komen.
Er vindt geen automatische ingredient-, portie- of OCR-correctie plaats.
Externe content wordt niet gekopieerd of hergepubliceerd: de site
verwijst naar de originele openbare receptpagina.

## Voorbehoud

De MIT-licentie van het GitHub-project geldt voor de software, niet per
definitie voor de receptteksten, foto's of database-inhoud van derden.
Gebruik de links als aanvullend hulpmiddel. Niet-exacte titels, andere
varianten en onduidelijke matches worden bewust weggelaten.
