# Receptenextractie: betrouwbaarheidsstandaard

Laatst bijgewerkt: 28 oktober 2026. Broncode: `drive_plated_sync.py`, `rescan_plated_ingredients.py`, `plated_translate_nl.py`, `audit_recipe_quality.py`.

## Waarom een tweede extractie?
Plated-receptkaarten gebruiken een meerkoloms lay-out. De globale tekstvolgorde van een PDF is niet noodzakelijk dezelfde als de visuele leesvolgorde. Dat blijkt uit praktijkervaringen rond meervoudige kolommen in Reddit /r/LocalLLaMA en uit de Docling-issues #2204 en #2067. Een volledige OCR-run is evenmin altijd betrouwbaarder dan een aanwezige tekstlaag.

- Eerste poging: brontekst per PDF en herkenbare ingrediëntenlijst.
- Tweede poging: de tekstlaag van pagina 2 (en indien nodig pagina 1/3), gericht op de ingrediënten.
- Bij onvoldoende resultaten: 300dpi-Tesseract-OCR op de linker ingrediëntenkolom, met andere paginasegmentatie.
- Vervolgens: numerieke kandidaten parsèn, zonder ontbrekende porties of verpakkingsgewichten te verzinnen.
- Daarna: Engelse bronnaam en Nederlandse productnaam apart vastleggen. Alleen exacte gewichtseenheden (oz/lb) mogen zonder ingrediëntafhankelijkheid naar gram; cups en lepels niet.
- Nooit de oorspronkelijke PDF, ruwe extractie of bestaande handmatige correcties overschrijven.

## Formele kwaliteitsstatussen
1. **bron_gevonden**: originele PDF en paginakoppeling bekend.
2. **tekst_geextraheerd**: OCR of PDF-tekst gevonden; niet voldoende voor prijs.
3. **ingredient_kandidaten**: ingrediënten met originele bronregels, niet per se volledig.
4. **bron_gecontroleerd**: ingrediënten, hoeveelheid, eenheid en oorspronkelijke portiegrootte handmatig met originele kaart vergeleken.
5. **prijs_klaar**: alleen als de ingrediëntenlijst compleet is, exact of expliciet onderbouwd omgerekend naar doelporties, en gekoppeld aan een correcte supermarktproductvariant. Een aanbieding moet geldig zijn.
6. **prijs_gepubliceerd**: totaal is reproduceerbaar met bronlinks, prijsdatum en ontbrekende componenten nul.

Een Nederlandse woordenlijst of een groene GitHub Action geeft **nooit** automatisch status 4, 5 of 6.

## Meetplan
Gebruik een representatieve steekproef van minstens 30 afzonderlijke originele kaarten: PDF's met tekstlaag en scans, twee- en vierportieskaarten, ingewikkelde breuken (¼, ½, 1½), verpakkingen, producten met dezelfde naam en lange stappenlijsten. Registreer per kaart de echte ingrediëntregels en aantallen **vanaf de originele afbeelding**, onafhankelijk van OCR.

Meet:
- precisie van gevonden ingrediënten (geen onterechte ingrediënten);
- recall van aanwezige ingrediënten (geen gemiste regels);
- nauwkeurigheid van hoeveelheden en eenheden;
- correctheid van porties;
- correcte Nederlandse productidentiteit;
- exactheid van bronpagina en PDF-download.

Doel voor verdere verbeteringen: ingrediëntenprecisie/recall ≥ 98% en **100% handmatige bevestiging van porties en hoeveelheden** voordat een recept het keurmerk 'bron gecontroleerd' of een definitieve prijs krijgt. De doelwaarden zijn nog **geen gemeten prestaties**.

## Actuele automatische veiligheidscontroles
Het JSON-rapport `recipe_quality_audit.json` controleert nu op dubbele bron-ID's, onmogelijke aantallen, verschillen met de queue en foutief als prijs-goedgekeurd gemarkeerde OCR-records. Het vermeldt expliciet hoeveel bronporties, ingrediëntennamen en bronkaarten nog onvolledig zijn. Bij structurele fouten faalt GitHub CI.

## Onderzoeksbronnen
- Tesseract ImproveQuality: https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- PyMuPDF tekstblokken en OCR: https://github.com/pymupdf/PyMuPDF/blob/main/docs/recipes-text.rst
- Docling layout / tabelherkenning: https://github.com/docling-project/docling
- Docling issue over twee kolommen: https://github.com/docling-project/docling/issues/2204
- Reddit lokale PDF-extractie en meerkolomskwesties: https://www.reddit.com/r/LocalLLaMA/comments/1tuqsn4/
- Reddit PDF-extractie en tabellen: https://www.reddit.com/r/LocalLLaMA/comments/1nn1elw/
