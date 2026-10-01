#!/usr/bin/env python3
"""Fetch Zotero item metadata and PDF attachments for $ingest.

Usage:
    python3 tools/zotero_fetch.py item <ref>            # normalized metadata JSON to stdout
    python3 tools/zotero_fetch.py item <ref> -o raw/tmp/zotero/<key>.json
    python3 tools/zotero_fetch.py download <ref>        # PDF + metadata under raw/tmp/zotero/
    python3 tools/zotero_fetch.py download <ref> --from-attachment-url
                                                         # fall back to the attachment's URL when
                                                         # the bytes are not stored on zotero.org

<ref> is an 8-char Zotero item key, "zotero:<key>", or a
https://zotero.org/(users|groups)/<id>/items/<key> URL.

Requires ZOTERO_LIBRARY_ID and ZOTERO_API_KEY (ZOTERO_LIBRARY_TYPE defaults
to "user"); set them in .env — see the Zotero block in .env.example.

Exit codes: 0 ok, 2 bad reference / missing credentials, 3 Zotero API error
(item not found, no PDF attachment, download failed).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Mapping

import _env  # noqa: F401 — load .env files for ZOTERO_* credentials

KEY_PATTERN = re.compile(r"^[A-Z0-9]{8}$")
URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?zotero\.org/(?:users|groups)/\d+"
    r"/items/([A-Za-z0-9]{8})/?(?:\?.*)?$"
)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
PUBLICATION_FIELDS = (
    "publicationTitle",
    "bookTitle",
    "proceedingsTitle",
    "institution",
    "publisher",
)
MAX_PDF_BYTES = 200 * 1024 * 1024


class DownloadError(Exception):
    """Attachment-URL download failed (bad status, not a PDF, too large)."""


def parse_item_ref(ref: str) -> str:
    """Return the 8-char Zotero item key from a supported reference form.

    Accepts a bare key, ``zotero:<key>``, or a zotero.org user/group item URL.
    Raises ValueError (fail-closed) for anything else.
    """
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError("empty Zotero item reference")
    ref = ref.strip()
    if ref.lower().startswith("zotero:"):
        candidate = ref.split(":", 1)[1].strip()
    elif ref.startswith(("http://", "https://")):
        match = URL_PATTERN.match(ref)
        if not match:
            raise ValueError(f"unrecognized Zotero item URL: {ref!r}")
        candidate = match.group(1)
    else:
        candidate = ref
    key = candidate.upper()
    if not KEY_PATTERN.match(key):
        raise ValueError(
            f"unrecognized Zotero item reference: {ref!r} "
            "(expected an 8-char key, 'zotero:<key>', or a "
            "https://zotero.org/users/<id>/items/<key> URL)"
        )
    return key


def normalize_item(item: dict) -> dict:
    """Turn a raw Zotero item (with or without the 'data' wrapper) into a record."""
    if not isinstance(item, dict):
        raise ValueError(f"unexpected Zotero item shape: {type(item).__name__}")
    data = item.get("data") if isinstance(item.get("data"), dict) else item
    creators = []
    for creator in data.get("creators") or []:
        if not isinstance(creator, dict):
            continue
        if creator.get("lastName"):
            given = creator.get("firstName") or ""
            creators.append(
                f"{creator['lastName']}, {given}".rstrip(", ")
                if given
                else str(creator["lastName"])
            )
        elif creator.get("name"):
            creators.append(str(creator["name"]))
    date = data.get("date") or ""
    year_match = YEAR_PATTERN.search(str(date))
    publication_title = next(
        (data.get(field) for field in PUBLICATION_FIELDS if data.get(field)),
        None,
    )
    tags = [
        tag["tag"]
        for tag in data.get("tags") or []
        if isinstance(tag, dict) and tag.get("tag")
    ]
    return {
        "item_key": item.get("key") or data.get("key") or "",
        "item_type": data.get("itemType") or "",
        "title": data.get("title") or "",
        "creators": creators,
        "year": year_match.group(0) if year_match else None,
        "date": str(date) if date else None,
        "doi": data.get("DOI") or None,
        "publication_title": publication_title,
        "abstract": data.get("abstractNote") or None,
        "url": data.get("url") or None,
        "tags": tags,
        "collections": list(data.get("collections") or []),
    }


def select_pdf_attachment(children: list) -> dict | None:
    """Pick the best PDF attachment among child items; None when there is none.

    Prefers linkMode 'imported_file' (stored bytes) over URL-linked copies.
    """
    ranked = []
    for index, child in enumerate(children or []):
        if not isinstance(child, dict):
            continue
        data = child.get("data") if isinstance(child.get("data"), dict) else child
        if data.get("itemType") != "attachment":
            continue
        content_type = str(data.get("contentType") or "").lower()
        filename = str(data.get("filename") or "")
        is_pdf = content_type == "application/pdf" or (
            not content_type and filename.lower().endswith(".pdf")
        )
        if not is_pdf:
            continue
        preference = 0 if data.get("linkMode") == "imported_file" else 1
        ranked.append((preference, index, child))
    if not ranked:
        return None
    ranked.sort(key=lambda entry: (entry[0], entry[1]))
    return ranked[0][2]


def read_capped(chunks, limit: int = MAX_PDF_BYTES) -> bytes:
    """Accumulate byte chunks up to limit; DownloadError when it would overflow."""
    buffer = bytearray()
    for chunk in chunks:
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise DownloadError(f"attachment exceeds the {limit}-byte size cap")
    return bytes(buffer)


def looks_like_pdf(content: bytes) -> bool:
    """True only for real PDF magic bytes (blocks login/paywall HTML)."""
    return content.startswith(b"%PDF")


def attachment_url(attachment: dict) -> str | None:
    """Return the attachment's http(s) source URL, or None (fail-closed)."""
    if not isinstance(attachment, dict):
        return None
    data = attachment.get("data") if isinstance(attachment.get("data"), dict) else attachment
    url = str(data.get("url") or "").strip()
    if url.lower().startswith(("http://", "https://")):
        return url
    return None


def fetch_pdf_from_url(url: str) -> bytes:
    """Download an attachment URL and validate it is a PDF (capped, fail-closed)."""
    import requests

    try:
        response = requests.get(
            url,
            stream=True,
            timeout=30,
            headers={"User-Agent": "AutoSci-zotero_fetch/1.0"},
        )
    except requests.RequestException as exc:
        raise DownloadError(f"attachment URL request failed: {exc}") from exc
    if response.status_code != 200:
        raise DownloadError(
            f"attachment URL returned HTTP {response.status_code}"
        )
    content_type = str(response.headers.get("Content-Type") or "").lower()
    try:
        content = read_capped(response.iter_content(chunk_size=65536))
    finally:
        response.close()
    if not looks_like_pdf(content):
        raise DownloadError(
            "attachment URL did not return a PDF"
            + (f" (Content-Type: {content_type})" if content_type else "")
        )
    return content


def require_credentials(env: Mapping[str, str]) -> tuple[str, str, str]:
    """Return (library_id, api_key, library_type); SystemExit(2) when missing/invalid."""
    library_id = str(env.get("ZOTERO_LIBRARY_ID") or "").strip()
    api_key = str(env.get("ZOTERO_API_KEY") or "").strip()
    library_type = str(env.get("ZOTERO_LIBRARY_TYPE") or "user").strip() or "user"
    missing = [
        name
        for name, value in (
            ("ZOTERO_LIBRARY_ID", library_id),
            ("ZOTERO_API_KEY", api_key),
        )
        if not value
    ]
    if missing:
        print(
            f"error: missing Zotero credentials: {', '.join(missing)} — set them "
            "in .env (see the Zotero block in .env.example; keys come from "
            "https://www.zotero.org/settings/keys)",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if library_type not in ("user", "group"):
        print(
            f"error: ZOTERO_LIBRARY_TYPE must be 'user' or 'group', got "
            f"{library_type!r}",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return library_id, api_key, library_type


def safe_filename(name: str, fallback: str = "item.pdf") -> str:
    """Reduce an untrusted filename/title to a single safe '.pdf' component."""
    name = (name or "").strip()
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[^\w.\- ]+", "_", name, flags=re.UNICODE).strip(" .")
    if not name:
        name = fallback
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def build_client():
    """Construct an authenticated pyzotero client (network path; sandbox-gated)."""
    import _sandbox  # noqa: F401 — sandbox gate, exits 126 if blocked
    from pyzotero import Zotero

    library_id, api_key, library_type = require_credentials(os.environ)
    return Zotero(
        library_id=library_id, library_type=library_type, api_key=api_key
    )


def _dump_json(payload: dict, path: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")


def _emit_error(error: str, key: str, message: str) -> None:
    """Write one machine-readable error object to stderr."""
    print(
        json.dumps(
            {"ok": False, "error": error, "item_key": key, "message": message},
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )


def cmd_item(args: argparse.Namespace) -> int:
    from pyzotero.errors import PyZoteroError

    key = parse_item_ref(args.ref)
    zot = build_client()
    try:
        item = zot.item(key)
    except PyZoteroError as exc:
        _emit_error("zotero_api_error", key, str(exc))
        return 3
    record = normalize_item(item)
    _dump_json(record, Path(args.out) if args.out else None)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    from pyzotero.errors import PyZoteroError, ResourceNotFoundError

    key = parse_item_ref(args.ref)
    zot = build_client()
    dest_dir = Path(args.raw_root) / "tmp" / "zotero"
    try:
        item = zot.item(key)
        data = item.get("data") if isinstance(item.get("data"), dict) else item
        if data.get("itemType") == "attachment":
            attachment = item
        else:
            attachment = select_pdf_attachment(zot.children(key))
        if attachment is None:
            _emit_error(
                "no_pdf_attachment",
                key,
                "no PDF attachment on this Zotero item — attach the PDF in "
                "Zotero or pass a local path instead",
            )
            return 3
        attachment_key = (
            attachment.get("key")
            or (attachment.get("data") or {}).get("key")
            or ""
        )
        if not attachment_key:
            _emit_error(
                "attachment_missing_key", key, "attachment item has no key"
            )
            return 3
        try:
            payload = zot.file(attachment_key)
        except ResourceNotFoundError:
            url = attachment_url(attachment) if args.from_attachment_url else None
            if url is None:
                _emit_error(
                    "file_not_on_server",
                    key,
                    "attachment record exists but the PDF bytes are not stored "
                    "on zotero.org (storage sync off or metadata-only import) — "
                    "enable file sync in Zotero, re-attach the PDF, pass a local "
                    "PDF path to $ingest, or retry with --from-attachment-url",
                )
                return 3
            print(
                f"warning: file not stored on zotero.org; "
                f"fetching attachment URL instead: {url}",
                file=sys.stderr,
            )
            try:
                payload = fetch_pdf_from_url(url)
            except DownloadError as exc:
                _emit_error("attachment_url_fetch_failed", key, str(exc))
                return 3
        if not isinstance(payload, (bytes, bytearray)):
            _emit_error(
                "unexpected_file_payload",
                key,
                f"expected bytes, got {type(payload).__name__}",
            )
            return 3
    except PyZoteroError as exc:
        _emit_error("zotero_api_error", key, str(exc))
        return 3

    record = normalize_item(item)
    attachment_name = (
        (attachment.get("data") or {}).get("filename")
        if isinstance(attachment.get("data"), dict)
        else None
    ) or record["title"] or key
    filename = f"{key}_{safe_filename(str(attachment_name))}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = dest_dir / f"{key}.json"
    dest = dest_dir / filename
    _dump_json(record, metadata_path)
    part = dest.with_name(dest.name + ".part")
    try:
        part.write_bytes(bytes(payload))
        part.replace(dest)
    except OSError as exc:
        part.unlink(missing_ok=True)
        _emit_error("write_failed", key, str(exc))
        return 3
    print(
        json.dumps(
            {
                "ok": True,
                "item_key": key,
                "source_path": str(dest),
                "metadata_path": str(metadata_path),
                "record": record,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    item_parser = subparsers.add_parser(
        "item", help="fetch and normalize one item's metadata"
    )
    item_parser.add_argument("ref", help="item key, zotero:<key>, or item URL")
    item_parser.add_argument(
        "-o", "--out", default="", help="also write the metadata JSON here"
    )
    download_parser = subparsers.add_parser(
        "download", help="download the item's PDF attachment under raw/tmp/zotero/"
    )
    download_parser.add_argument("ref", help="item key, zotero:<key>, or item URL")
    download_parser.add_argument(
        "--raw-root", default="raw", help="raw root (default: raw)"
    )
    download_parser.add_argument(
        "--from-attachment-url",
        action="store_true",
        help="when the PDF is not stored on zotero.org, fetch the attachment's "
        "URL instead (fails closed if it is not a PDF)",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "item":
            return cmd_item(args)
        return cmd_download(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
