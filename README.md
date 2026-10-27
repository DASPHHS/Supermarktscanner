# Supermarktscanner

Eerste uitvoerbare versie voor AH, Jumbo en Lidl met **datumvalidatie** van aanbiedingen, **vier porties** per recept en berekening op basis van **hele verpakkingen**.

## Starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open de lokale URL die Streamlit toont. Upload een CSV met de kolommen `store,product,price_eur,quantity_g,valid_from,valid_until,source_url`. Gebruik exacte ingrediëntnamen uit de app, bijvoorbeeld `broccoli`, `kipfilet` en `paprika`. `store` is exact `AH`, `Jumbo` of `Lidl`.

## Status en beperkingen

- De applicatie werkt met door de gebruiker aangeleverde CSV-prijzen. **Geen live prijsfeed** en **geen automatisch opgehaalde aanbiedingen**; het zou misleidend zijn die te claimen.
- De geplande dagelijkse GitHub Action draait **tests**, geen prijsupdate.
- Vijf voorbeeldrecepten zijn opgenomen. Drive-import, 20 recepten per supermarkt, volledige voedingswaardeberekening, persoonlijke eiwitdoelen en snacks met ≥20 g eiwit moeten nog worden gerealiseerd.
- Alleen volledige ingredientdekking levert een volledige receptprijs. Niet-geprijsde ingrediënten worden expliciet gemeld.
- Bronlinks worden als CSV-veld bewaard maar niet geverifieerd. Controleer ze voor gebruik.

## Tests

```bash
pip install -r requirements.txt pytest
pytest -q
```

Voor openbare hosting kan dit Streamlit-project worden verbonden met Streamlit Community Cloud. Hosting is nog niet ingericht.
