# Plated PDF-invoer

GitHub Actions leest PDF-bestanden in deze map met `import_plated_from_repo.py`. Een upload of wijziging start automatisch de workflow **Plated pdfs scannen**. Er is geen Google Drive-secret nodig.

**Waarschuwing:** dit is een **openbare** repository. Zet hier alleen bestanden neer waarvoor je toestemming hebt om ze publiek te verspreiden. Voor de volledige privé Plated-collectie is een privébron of privérepository geschikter; een publieke GitHub Pages-website kan uitsluitend de afgeleide, gecontroleerde ingrediëntgegevens presenteren.

In de GitHub-webinterface kun je bestanden per batch uploaden, met limieten van 25 MiB per bestand en 100 bestanden per keer. GitHub accepteert in een gewoon Git-repository geen bestanden boven 100 MiB, en beveelt repositorygrootten onder 1 GB aan; deze map is daarom niet geschikt om zonder nadenken het hele 2,12 GB archief te hosten.

Na import staan de ruwe OCR-resultaten in `plated_local_review_queue.json` en de aantallen in `plated_local_progress.json`. Voorlopige ingrediënten en vierportiehoeveelheden zijn **niet automatisch gevalideerd** of prijsbaar. Het officiële bestand `plated_recipes.json` blijft gescheiden.
