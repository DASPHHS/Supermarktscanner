"""Optionele HFresh-receptverwijzingen, nooit een prijs- of ingrediëntenbron.

HFresh is een onafhankelijke, onofficiële verzameling. De openbare site mag
zonder account bezocht worden; de REST API gebruikt een eigen Bearer-token.
Dit script importeert bewust uitsluitend metadata bij exact overeenkomende
Nederlandse titels, zonder porties of productprijzen aan te passen.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path


def title_key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).lower()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def safe_recipe_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return None
    if (parsed.scheme != "https" or parsed.hostname not in {"hfresh.info", "www.hfresh.info"}
            or parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment
            or not re.fullmatch(r"/nl-NL/recipes/[a-z0-9-]+-[0-9]+/?", parsed.path)):
        return None
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def build_crossrefs(recipes: list[dict], external: list[dict]) -> dict:
    """Fail closed for ambiguous titles, unknown hosts and missing source IDs."""
    by_title: dict[str, list[dict]] = defaultdict(list)
    for row in external:
        if not isinstance(row, dict):
            continue
        key = title_key(row.get("name"))
        url = safe_recipe_url(row.get("url"))
        if key and url and isinstance(row.get("id"), int):
            by_title[key].append(row)
    matched = {}
    ambiguous = 0
    for r in recipes:
        if not isinstance(r, dict) or not r.get("id") or not r.get("title_extracted"):
            continue
        key = title_key(r["title_extracted"])
        options = by_title.get(key, [])
        if len(options) > 1:
            ambiguous += 1
            continue
        if len(options) != 1:
            continue
        ext = options[0]
        # No quantities, ingredient substitutions, prices or verification flags.
        entry = {"url": safe_recipe_url(ext["url"]), "source_id": ext["id"],
                 "title": ext["name"], "match": "exact_title_only"}
        for field in ("prep_time", "total_time"):
            value = ext.get(field)
            if type(value) is int and 0 < value <= 600:
                entry[field] = value
        matched[str(r["id"])] = entry
    return {"schema_version": 1, "source": "HFresh — onofficieel",
            "match_policy": "exact_title_only; no price/portion/ingredient verification",
            "matched": len(matched), "ambiguous": ambiguous,
            "recipe_links": matched}


def read_catalog(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    raise ValueError("HFresh-catalogus moet een lijst of een API-pagina met data[] zijn")


def fetch_catalog(api_url: str, token: str, max_pages: int = 40) -> list[dict]:
    """Server-side only. Never put the token in GitHub Pages or browser JS."""
    parsed = urllib.parse.urlsplit(api_url)
    if parsed.scheme != "https" or parsed.hostname != "api.hfresh.info" or parsed.username or parsed.password:
        raise ValueError("API-URL moet op https://api.hfresh.info staan")
    if parsed.path != "/nl-NL/recipes":
        raise ValueError("Alleen de Nederlandse recepten-API is toegestaan")
    url = api_url + ("&" if parsed.query else "?") + "perPage=200"
    rows: list[dict] = []
    seen: set[str] = set()
    for _ in range(max_pages):
        if url in seen:
            raise ValueError("Paginatie bevat een lus")
        seen.add(url)
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token, "Accept": "application/json",
            "User-Agent": "Supermarktscanner-HFreshCrossrefs/1.0"})
        with urllib.request.urlopen(req, timeout=25) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("HFresh API-schema onbekend; bestaande output behouden")
        rows.extend(payload["data"])
        nxt = payload.get("links", {}).get("next") if isinstance(payload.get("links"), dict) else None
        if not nxt:
            return rows
        parsed_next = urllib.parse.urlsplit(nxt)
        if parsed_next.scheme != "https" or parsed_next.hostname != "api.hfresh.info" or parsed_next.path != "/nl-NL/recipes":
            raise ValueError("Onveilige vervolglink in HFresh-paginatie")
        url = nxt
    raise ValueError("Maximum aantal API-pagina's bereikt; geen onvolledige output publiceren")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipes", type=Path, default=Path("recipes_extracted.json"))
    parser.add_argument("--output", type=Path, default=Path("hellofresh/hfresh_matches.json"))
    parser.add_argument("--catalog", type=Path, help="Bestaande JSON-export; geen token nodig")
    parser.add_argument("--api-url", default="https://api.hfresh.info/nl-NL/recipes")
    args = parser.parse_args()

    local = json.loads(args.recipes.read_text(encoding="utf-8"))
    if not isinstance(local, dict) or not isinstance(local.get("recipes"), list):
        raise ValueError("Lokale receptenindex ontbreekt of is ongeldig")
    if args.catalog:
        external = read_catalog(args.catalog)
    else:
        token = os.getenv("HFRESH_API_TOKEN", "")
        if not token:
            raise SystemExit("HFRESH_API_TOKEN ontbreekt; output niet gewijzigd")
        external = fetch_catalog(args.api_url, token)
    result = build_crossrefs(local["recipes"], external)
    if not result["matched"]:
        raise SystemExit("Geen ondubbelzinnige bronmatches; bestaande output behouden")
    result["updated_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"HFresh: {result['matched']} exacte titelmatches, {result['ambiguous']} ambigue titels")


if __name__ == "__main__":
    main()
