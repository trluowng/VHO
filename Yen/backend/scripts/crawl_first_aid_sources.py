"""Download only allow-listed first-aid references with provenance metadata.

This is intentionally not a general web crawler. It follows no links, does not submit
forms, and only downloads an explicit URL from source_registry.json after its licence
has been recorded. Rules must still be clinically reviewed before use.
"""
from __future__ import print_function

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "first_aid"
DEFAULT_REGISTRY = DATA_DIR / "source_registry.json"
DEFAULT_OUTPUT = DATA_DIR / "corpus"
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
USER_AGENT = "VHO-FirstAidSourceCollector/1.0 (provenance-only; contact: project-maintainer)"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def select_sources(registry, requested_ids):
    sources = registry.get("sources", [])
    if requested_ids:
        requested = set(requested_ids)
        missing = requested - set(source.get("id") for source in sources)
        if missing:
            raise ValueError("Unknown source id(s): {}".format(", ".join(sorted(missing))))
        return [source for source in sources if source.get("id") in requested]
    return [source for source in sources if source.get("enabled")]


def validate_download_url(source):
    url = source.get("download_url")
    if not url:
        raise ValueError("Source has no download_url")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Only absolute HTTPS download URLs are allowed")
    domain = parsed.netloc.lower().split(":", 1)[0]
    allowed_domains = {item.lower() for item in source.get("allowed_domains", [])}
    if domain not in allowed_domains:
        raise ValueError("Download domain {} is not allow-listed".format(domain))
    return url


def extension_for(source):
    if source.get("format") == "pdf":
        return ".pdf"
    if source.get("format") == "html":
        return ".html"
    return ".bin"


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def download(url):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.1"})
    with urlopen(request, timeout=30) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_DOWNLOAD_BYTES:
            raise ValueError("Source is larger than {} bytes".format(MAX_DOWNLOAD_BYTES))
        payload = response.read(MAX_DOWNLOAD_BYTES + 1)
        if len(payload) > MAX_DOWNLOAD_BYTES:
            raise ValueError("Source exceeded {} bytes".format(MAX_DOWNLOAD_BYTES))
        return payload, response.headers.get_content_type(), response.headers.get("ETag"), response.geturl()


def extract_pdf(pdf_path):
    try:
        from pypdf import PdfReader
    except ImportError:
        return None, "pypdf is not installed; raw PDF was saved but text was not extracted"

    reader = PdfReader(str(pdf_path))
    text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
    return text, None


def write_json(path, payload):
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def crawl_source(source, output_dir, extract):
    record = {
        "source_id": source.get("id"),
        "title": source.get("title"),
        "publisher": source.get("publisher"),
        "landing_url": source.get("landing_url"),
        "license": source.get("license"),
        "license_url": source.get("license_url"),
        "fetched_at": now_iso(),
        "fetch_mode": source.get("fetch_mode"),
        "requires_clinician_review": bool(source.get("requires_clinician_review")),
    }

    if source.get("fetch_mode") != "download_and_extract":
        record.update({"status": "metadata_only", "reason": "Registry forbids text ingestion for this source"})
        return record

    url = validate_download_url(source)
    payload, content_type, etag, final_url = download(url)
    raw_path = output_dir / "raw" / (source["id"] + extension_for(source))
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload)

    record.update({
        "status": "downloaded",
        "download_url": url,
        "final_url": final_url,
        "content_type": content_type,
        "etag": etag,
        "sha256": sha256_bytes(payload),
        "bytes": len(payload),
        "raw_file": str(raw_path.relative_to(output_dir)),
    })

    if extract and source.get("format") == "pdf":
        text, extraction_error = extract_pdf(raw_path)
        if extraction_error:
            record["extraction_error"] = extraction_error
        else:
            text_path = output_dir / "text" / (source["id"] + ".txt")
            text_path.parent.mkdir(parents=True, exist_ok=True)
            text_path.write_text(text, encoding="utf-8")
            record.update({
                "text_file": str(text_path.relative_to(output_dir)),
                "text_sha256": sha256_bytes(text.encode("utf-8")),
                "characters_extracted": len(text),
            })
    return record


def main():
    parser = argparse.ArgumentParser(description="Allow-list first-aid source collector with provenance manifest")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-id", action="append", dest="source_ids", help="Collect one source id; repeatable")
    parser.add_argument("--dry-run", action="store_true", help="Validate registry selection without network or file writes")
    parser.add_argument("--extract", action="store_true", help="Extract text from approved PDFs; requires pypdf")
    args = parser.parse_args()

    registry = read_json(args.registry)
    selected = select_sources(registry, args.source_ids)
    if not selected:
        raise ValueError("No enabled sources selected")

    if args.dry_run:
        for source in selected:
            line = "{}: {} ({})".format(source["id"], source["fetch_mode"], source["license"])
            if source.get("fetch_mode") == "download_and_extract":
                validate_download_url(source)
            print(line)
        return 0

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for source in selected:
        try:
            record = crawl_source(source, output, args.extract)
        except Exception as exc:
            record = {
                "source_id": source.get("id"),
                "title": source.get("title"),
                "fetched_at": now_iso(),
                "status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        records.append(record)
        print("{}: {}".format(record.get("source_id"), record.get("status")))

    manifest = {
        "schema_version": "1.0",
        "generated_at": now_iso(),
        "registry": str(args.registry.resolve()),
        "records": records,
    }
    write_json(output / "manifest.json", manifest)
    return 0 if all(record.get("status") in {"downloaded", "metadata_only"} for record in records) else 1


if __name__ == "__main__":
    sys.exit(main())
