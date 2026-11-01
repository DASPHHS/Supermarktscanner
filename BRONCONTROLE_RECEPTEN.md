# Broncontrole van alle recepten · 1 november 2026

De officiële HelloFresh-receptenbibliotheek is een aanvullende bron:
https://www.hellofresh.nl/recipes

**Een automatische broncontrole is geen handmatige inhoudelijke bevestiging.** Het nieuwe scripts/audit_recipe_library.py leest ieder HelloFresh- en Plated-bronrecord, vergelijkt de aanwezigheid van de titel, bronidentiteit, originele PDF, ingrediëntnamen en hoeveelheidsvelden, en registreert onzekere porties, dubbele titels en ontbrekende gegevens.

De geplande GitHub Action library-source-audit.yml maakt na de merge een controleverslag met alle bronrecords in hellofresh/library_source_audit.json. De interactieve rapportage staat in hellofresh/source-audit.html. De originele bron-PDF is vanuit ieder record bereikbaar als de preview aanwezig is.

## Hoe de officiële bron wordt gebruikt

De officiële site heeft meerdere versies van gelijknamige recepten. Bijvoorbeeld Schnitzel met knoflook-gemberrijst:

- https://www.hellofresh.nl/recipes/schnitzel-met-knoflook-gemberrijst-6311cb3128a4b6cde308087a
- https://www.hellofresh.nl/recipes/schnitzel-met-knoflook-gemberrijst-65f991ba473c4f42771d07c0
- https://www.hellofresh.nl/recipes/schnitzel-met-knoflook-gemberrijst-63c841f86ab9cacaa3738d06

Deze links en de officiële pagina voor Kipfilet in mosterdroomsaus zijn als **titelkandidaten** opgenomen in hellofresh/official_recipe_candidates.json. De website toont expliciet dat de variant en de ingrediënten nog niet bevestigd zijn. Een overeenkomstige titel is onvoldoende: controleer ook alle hoeveelheden, de portiebasis, de bijgerechten en zelf toe te voegen ingrediënten tegen de aangeleverde PDF.

## Wat nog niet als gecontroleerd mag worden gemarkeerd

De bronindex bevat 225 HelloFresh-receptrecords en 504 Plated-bronrecords. De Plated-recepten behoren niet tot de HelloFresh-bibliotheek en kunnen niet via HelloFresh.nl worden bevestigd. De 61 beeldpagina's uit de extra bundel Hellofresh recepten.pdf zijn nog niet als volledige, betrouwbaar gecontroleerde nieuwe recepten geïmporteerd. Ook bij bestaande OCR-/vertaalrecords kan de naam of hoeveelheid onjuist zijn ondanks een technisch gevuld veld.

**Handmatige bevestiging** vereist per recept een gecontroleerde originele kaart, juiste variant, alle ingrediëntnamen, hoeveelheden en porties. De audit voert deze visuele vergelijking niet automatisch uit en wijzigt nooit de bestaande bronvalidatie, prijsraming of prijsranglijst. Een nieuw bronrecord wordt evenmin uitsluitend op basis van een website-titel aangemaakt.

## Testen

- PYTHONPATH=. python -m unittest discover -s tests -p test_audit_recipe_library.py
- python scripts/audit_recipe_library.py --output /tmp/library_source_audit.json
- npm test

Het aantal automatisch doorgelopen receptrecords, ingevulde hoeveelheden en nog onbevestigde recepten wordt op de website rechtstreeks uit de laatste uitgevoerde audit getoond. Ontbreekt die publicatie, dan wordt dat expliciet vermeld.
