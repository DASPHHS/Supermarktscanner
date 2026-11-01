"""Regression tests: published Plated PDFs must preserve original source bytes."""
import hashlib
import io
import json
import zipfile

from pypdf import PdfWriter

import render_plated_cards


def test_original_pdf_is_byte_identical_and_legacy_cards_are_migrated(tmp_path, monkeypatch):
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": "Source PDF metadata must survive"})
    buf = io.BytesIO()
    writer.write(buf)
    source = buf.getvalue()

    archive = tmp_path / "plated.zip"
    member = "Plated/example.pdf"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(member, source)

    identity = "test-archive::" + member
    queue = tmp_path / "queue.json"
    queue.write_text(json.dumps({"recipes": [
        {"source_identity": identity, "source_member": member}
    ]}), encoding="utf-8")

    calls = []
    def fake_raster(pdf, page, target):
        calls.append(page)
        target.write_bytes(b"test preview")
    monkeypatch.setattr(render_plated_cards, "raster", fake_raster)

    root = tmp_path / "output"
    render_plated_cards.run(archive, queue, root=root, batch=1)
    manifest_path = root / "plated_preview_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["recipes"]["plated-release-" + identity]
    published = root / entry["original_pdf"]
    assert published.read_bytes() == source
    assert entry["source_sha256"] == hashlib.sha256(source).hexdigest()
    assert manifest["metadata"]["byte_identical_originals"] == 1
    assert calls == [1]

    # Simulate a legacy card whose PDF had been reserialized by PdfWriter.
    published.write_bytes(b"legacy reconstruction")
    del manifest["recipes"]["plated-release-" + identity]["source_sha256"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    render_plated_cards.run(archive, queue, root=root, batch=1)
    assert published.read_bytes() == source
    assert calls == [1]  # Existing preview remains untouched.

    # A completed card is skipped without rewriting its source or preview.
    render_plated_cards.run(archive, queue, root=root, batch=1)
    assert published.read_bytes() == source
    assert calls == [1]
