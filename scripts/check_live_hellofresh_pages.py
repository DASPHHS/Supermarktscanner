"""Check the *published GitHub Pages URLs*, not repository-local fixtures.

A green local test does not prove that HTML/JS/data or original source cards
were actually published. Fail visibly on stale HTML, incomplete JSON, 404s
and a source-audit/recipe-catalog mismatch.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

DEFAULT_BASE = "https://dasphhs.github.io/Supermarktscanner/hellofresh/"
REQUIRED_APP_VERSION = "20261103-coverage-v17"


def get(url: str, *, max_bytes: int = 9_000_000, timeout: int = 25) -> tuple[bytes, str]:
    request = Request(
        url, headers={"User-Agent": "Supermarktscanner-Pages-Smoketest/1.0", "Accept": "*/*"}
    )
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as exc:
        raise ValueError(f"HTTP {exc.code} for public resource: {url}") from exc
    with response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}: {url}")
        size = response.headers.get("Content-Length")
        if size and int(size) > max_bytes:
            raise ValueError(f"Response exceeds {max_bytes} bytes: {url}")
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError(f"Response exceeds {max_bytes} bytes: {url}")
        return data, response.headers.get("Content-Type", "")


def load_json(url: str) -> dict:
    raw, _ = get(url)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {url}")
    return data


def check_site(base: str) -> dict:
    base = base.rstrip("/") + "/"
    parsed = urlparse(base)
    if parsed.scheme != "https" or parsed.netloc != "dasphhs.github.io":
        raise ValueError("Only the official project GitHub Pages hostname is accepted")
    if parsed.path != "/Supermarktscanner/hellofresh/":
        raise ValueError("Wrong Pages deployment root")
    problems = []
    html_bytes, _ = get(base)
    html = html_bytes.decode("utf-8")
    audit_html = get(urljoin(base, "source-audit.html"))[0].decode("utf-8")
    if "library-coverage-status" not in html:
        problems.append("The live index does not include the coverage status widget")
    if "source-audit-status" not in html:
        problems.append("The live index does not include the recipe audit status")
    if "library_source_audit.json" not in audit_html:
        problems.append("The published audit page does not request the source-audit JSON")
    scripts = re.findall(r'<script\s+defer\s+src="([^"]+)"', html)
    if not scripts:
        problems.append("No JavaScript modules referenced by the published HTML")
    found_latest_app = False
    for script in scripts:
        src = urljoin(base, script)
        resolved = urlparse(src)
        if resolved.scheme != "https" or resolved.netloc != parsed.netloc:
            problems.append(f"Unexpected JavaScript origin: {script}")
            continue
        code = get(src, max_bytes=150_000)[0].decode("utf-8")
        if not code.strip():
            problems.append(f"Empty published JavaScript: {script}")
        if script.startswith("./app.js"):
            found_latest_app = REQUIRED_APP_VERSION in script
            if "compareLoadedWithAudit" not in code:
                problems.append("Published app.js is missing the live audit coverage check")
            if "String(r.id||'')" not in code:
                problems.append("Published app.js still collapses distinct same-title recipes")
    if not found_latest_app:
        problems.append(f"The browser HTML does not reference app.js version {REQUIRED_APP_VERSION}")
    audit = load_json(urljoin(base, "library_source_audit.json"))
    original = load_json(urljoin(base, "../recipes_extracted.json"))
    plated = load_json(urljoin(base, "../plated_release_review_queue.json"))
    scans = load_json(urljoin(base, "scanned_recipe_candidates.json"))
    preview = load_json(urljoin(base, "preview_manifest.json"))
    plated_preview = load_json(urljoin(base, "plated_preview_manifest.json"))
    original_count = len(original.get("recipes", []))
    plated_count = len(plated.get("recipes", []))
    scan_count = len(scans.get("recipes", []))
    audit_count = audit.get("summary", {}).get("records_audited")
    expected = original_count + plated_count + scan_count
    if (original_count, plated_count, scan_count) != (225, 504, 60):
        problems.append(
            f"Published source records differ from expected 225/504/60: "
            f"{original_count}/{plated_count}/{scan_count}"
        )
    if audit_count != expected or len(audit.get("records", [])) != expected:
        problems.append(f"Published audit differs from live records: {audit_count} vs {expected}")
    source_ids = set()
    duplicates = []
    for source, items in (("HelloFresh", original.get("recipes", []) + scans.get("recipes", [])),
                          ("Plated", plated.get("recipes", []))):
        for item in items:
            rid = str(item.get("id") if source == "HelloFresh" else
                      "plated-release-" + str(item.get("source_identity") or ""))
            key = (source, rid)
            if not rid or key in source_ids:
                duplicates.append(key)
            source_ids.add(key)
    if duplicates:
        problems.append(f"Duplicate/missing source identity in published sources: {duplicates[:5]}")
    audited = {(str(r.get("source")), str(r.get("id"))) for r in audit.get("records", [])}
    if audited != source_ids:
        problems.append(
            f"Live source IDs do not match published audit: "
            f"{len(source_ids - audited)} missing, {len(audited - source_ids)} extra"
        )
    cards = list((preview.get("recipes") or {}).values())
    plated_cards = list((plated_preview.get("recipes") or {}).values())
    for card in (cards[:1] + plated_cards[:1]):
        for attr in ("front", "original_pdf"):
            path = card.get(attr)
            if not isinstance(path, str) or not re.fullmatch(
                r"(?:previews|plated-previews)/[A-Za-z0-9_-]+(?:-front\.webp|-origineel\.pdf)", path
            ):
                problems.append(f"Preview manifest has an unsafe/missing {attr} path")
                continue
            # Read only header bytes to validate 200 and actual original/preview signature.
            req = Request(urljoin(base, path), headers={"Range": "bytes=0-15",
                                                        "User-Agent": "Supermarktscanner-Pages-Smoketest/1.0"})
            try:
                response = urlopen(req, timeout=25)
            except HTTPError as exc:
                raise ValueError(f"HTTP {exc.code} for original source file: {path}") from exc
            with response:
                header = response.read(16)
                if response.status not in (200, 206):
                    problems.append(f"Source card HTTP {response.status}: {path}")
                if attr == "original_pdf" and not header.startswith(b"%PDF"):
                    problems.append(f"Original source PDF is invalid: {path}")
                if attr == "front" and not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
                    problems.append(f"Source preview is not WebP: {path}")
    return {
        "status": "PASS" if not problems else "FAIL",
        "base": base,
        "scripts_checked": len(scripts),
        "hello_fresh": original_count,
        "plated": plated_count,
        "image_only_scans": scan_count,
        "live_index_count": len(source_ids),
        "audit_count": audit_count,
        "sample_original_pdf_and_previews": len(cards[:1] + plated_cards[:1]) * 2,
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    args = parser.parse_args()
    try:
        report = check_site(args.base_url)
    except (HTTPError, URLError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        report = {"status": "FAIL", "base": args.base_url, "problems": [str(exc)]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
