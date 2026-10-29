# Prijscontrole voor twee personen

Locatie: Bleiswijk. Winkels: AH, Jumbo en Lidl. De productfeed bevat landelijke
bronprijzen, geen bevestigde schapprijzen van de drie plaatselijke filialen.

## Hersteld op 29 oktober 2026

- 211 van 225 HelloFresh-records opnieuw uit de aangeleverde bron-PDF's gelezen.
  Daarbij zijn 1.277 ontbrekende ingrediëntregels teruggevonden. Het rapport
  `hellofresh_table_repair.json` vermeldt per record de oude en nieuwe telling.
- Alle zes hoeveelheidkolommen bewaard. De 2p-kolom wordt rechtstreeks gebruikt;
  hele verpakkingen worden opnieuw berekend voor twee personen.
- 14 tabellen met onduidelijke kolommen blijven afgewezen. De oude gegevens
  daarvan blijven zichtbaar als ongecontroleerde extractie. Het herstelproces
  kent geen verificatie toe aan OCR of automatisch herstelde gegevens.
- Oorspronkelijke ingrediëntregels blijven als auditspoor beschikbaar.
- Decimale verpakkingen zoals 1,5 liter worden als 1.500 ml gelezen. Multipacks
  en samengestelde gewichten worden afgewezen zolang hun betekenis niet vaststaat.
- Droge eetlepels worden niet omgezet naar milliliters. Peper en zout worden
  niet langer stilzwijgend als gratis voorraad geteld.
- Dubbele ingrediëntregels worden gemeld en niet stilzwijgend weggegooid.
- Mogelijke acties vereisen alle ingrediëntwoorden en bekende begin/einddatums.
  Paprikachips, tomatensoep en knoflookchampignons zijn geen match voor de rauwe
  ingrediënten paprika, tomaat en knoflook. Dit blijft slechts een suggestie;
  exacte productvariant en actievoorwaarden zijn nog niet doorgerekend.
- Ontbrekende prijssnapshots tonen ontbrekende ingrediënten, geen nul ontbrekend.
  Een onbekende ingrediëntenlijst wordt expliciet als onbekend weergegeven.
- De hoofdproteïne in de titel krijgt voorrang boven bijvoorbeeld kippenbouillon
  in een rundvleesgerecht. Een onbekend gerecht wordt niet standaard vega genoemd.

## Nog niet voltooid

Er zijn nog **nul volledig geverifieerde receptprijzen**. Er is dus nog geen
bewezen goedkoopste recept of bewezen top 10. De uitgevoerde tests bewijzen
reken- en weergaveregels; zij vervangen geen inhoudelijke broncontrole.

Voor de definitieve rangschikking ontbreken nog:

1. Controle van ingrediënten, hoeveelheden en uitgangsporties per recept.
2. Controle van de 14 afgewezen tabellen en de scanrecepten.
3. Exacte productkeuzes en betrouwbare conversies voor tenen, zakjes, pakjes,
   blikjes en ingrediënten die in stuks maar per gewicht verkocht worden.
4. Een vastgelegde hoeveelheid voor ingrediënten 'naar smaak', of een expliciet
   overeengekomen voorraadbeleid dat naast de prijs wordt getoond.
5. Controle van prijsactualiteit en beschikbaarheid per product en winkel.
6. Doorrekening van exacte actieproducten met kaartvoorwaarden, bundelaantallen,
   verpakkingseenheden en geldigheidsdatums.
7. Inhoudelijk gevalideerde Plated-recepten voordat zij prijsranglijsten mogen
   binnengaan. De lopende Plated-import wordt door deze reparatie niet aangepast.

De huidige 'Top 10' blijft uitsluitend volledig gevalideerde prijzen toelaten.
Ontbrekende prijzen worden nooit als nul euro gerangschikt.

## Herhalen

```sh
python repair_hellofresh_tables.py /pad/naar/bron-pdfs
python sync_prices.py
PYTHONPATH=. pytest -q
node --test tests/test_recipe_logic.cjs
node --check hellofresh/app.js
```

De prijsverversing blijft dagelijks draaien. De tabelreparatie is een expliciete
bronbewerking en wordt niet automatisch bij iedere prijssync herhaald.
