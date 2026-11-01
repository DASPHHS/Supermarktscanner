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
import time
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


def fetch_titles(api_url: str, token: str, titles: list[str], pause_seconds: float = 1.1) -> list[dict]:
    """Only a small number of exact-title searches; no mass database download."""
    parsed = urllib.parse.urlsplit(api_url)
    if (parsed.scheme != "https" or parsed.hostname != "api.hfresh.info"
            or parsed.username or parsed.password or parsed.path != "/nl-NL/recipes"):
        raise ValueError("Alleen https://api.hfresh.info/nl-NL/recipes is toegestaan")
    if len(titles) > 25:
        raise ValueError("Maximum 25 titelzoekopdrachten per synchronisatie")
    base_query = dict(urllib.parse.parse_qsl(parsed.query))
    rows: list[dict] = []
    for i, title in enumerate(titles):
        if i:
            time.sleep(pause_seconds)
        # Current API implementation uses perPage, though its docs say per_page.
        query = urllib.parse.urlencode({**base_query, "search": title, "perPage": "200", "page": "1"})
        url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token, "Accept": "application/json",
            "User-Agent": "Supermarktscanner-HFreshCrossrefs/1.0"})
        with urllib.request.urlopen(req, timeout=25) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("HFresh API-schema onbekend; bestaande output behouden")
        meta = payload.get("meta", {})
        current = meta.get("current_page") if isinstance(meta, dict) else None
        last = meta.get("last_page") if isinstance(meta, dict) else None
        if type(current) is not int or type(last) is not int or current != 1 or last < 1:
            raise ValueError("HFresh API-paginatie onvolledig; bestaande output behouden")
        # More than one page for a precise title is unsafe to treat as unique.
        if last == 1:
            rows.extend(payload["data"])
    return rows


def incremental_batch(recipes: list[dict], previous: dict, batch_size: int) -> tuple[list[dict], int]:
    """Return a stable rotation of the local titles; only these are queried."""
    selected = [r for r in recipes if isinstance(r, dict) and r.get("id") and title_key(r.get("title_extracted"))]
    if not selected:
        raise ValueError("Geen lokale brontitels beschikbaar")
    if not 1 <= batch_size <= 25:
        raise ValueError("Batchgrootte moet 1 t/m 25 zijn")
    cursor = previous.get("scan_cursor", 0)
    if type(cursor) is not int or cursor < 0:
        cursor = 0
    start = cursor % len(selected)
    batch = [selected[(start + i) % len(selected)] for i in range(min(batch_size, len(selected)))]
    return batch, (start + len(batch)) % len(selected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipes", type=Path, default=Path("recipes_extracted.json"))
    parser.add_argument("--output", type=Path, default=Path("hellofresh/hfresh_matches.json"))
    parser.add_argument("--catalog", type=Path, help="Bestaande JSON-export; geen token nodig")
    parser.add_argument("--api-url", default="https://api.hfresh.info/nl-NL/recipes")
    parser.add_argument("--batch-size", type=int, default=12, help="Maximum 25 zoekopdrachten per run")
    args = parser.parse_args()

    local = json.loads(args.recipes.read_text(encoding="utf-8"))
    if not isinstance(local, dict) or not isinstance(local.get("recipes"), list):
        raise ValueError("Lokale receptenindex ontbreekt of is ongeldig")
    previous = {}
    if args.output.exists():
        try:
            previous = json.loads(args.output.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            raise ValueError("Bestaande matches onleesbaar; niet overschrijven")
        if previous.get("schema_version") != 1:
            raise ValueError("Onbekende bestaande matches; niet overschrijven")
    if args.catalog:
        external = read_catalog(args.catalog)
        result = build_crossrefs(local["recipes"], external)
        if not result["matched"]:
            raise SystemExit("Geen exacte bronmatches in export; output behouden")
    else:
        token = os.getenv("HFRESH_API_TOKEN", "")
        if not token:
            raise SystemExit("HFRESH_API_TOKEN ontbreekt; output niet gewijzigd")
        batch, next_cursor = incremental_batch(local["recipes"], previous, args.batch_size)
        external = fetch_titles(args.api_url, token, [r["title_extracted"] for r in batch])
        fresh = build_crossrefs(batch, external)
        links = dict(previous.get("recipe_links") or {})
        # Rechecked titles must not retain a stale old match.
        for r in batch:
            links.pop(str(r["id"]), None)
        links.update(fresh["recipe_links"])
        result = {**fresh, "recipe_links": links, "matched": len(links),
                  "scan_cursor": next_cursor, "scanned_this_run": len(batch)}
    result["updated_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"HFresh: {result['matched']} exacte titelmatches, {result['ambiguous']} ambigue titels")


if __name__ == "__main__":
    main()
