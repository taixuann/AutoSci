# Zotero source path

Use this path when `source` is a Zotero item reference:

- 8-char item key: `ABCD1234`
- prefixed key: `zotero:ABCD1234`
- item URL: `https://zotero.org/users/<id>/items/<key>` (groups work too:
  `https://zotero.org/groups/<id>/items/<key>`)

Anything else is rejected before any network call (exit 2).

## Preconditions

- `ZOTERO_LIBRARY_ID` and `ZOTERO_API_KEY` in `.env` (see the Zotero block in
  `.env.example`; create both at https://www.zotero.org/settings/keys).
  `ZOTERO_LIBRARY_TYPE` defaults to `user`.
- Credentials are loaded automatically by `tools/_env.py` when the tool runs.
  Missing credentials → exit 2 with a message on stderr; report it to the user
  and stop. Do not fabricate metadata.

## Steps

1. Fetch normalized metadata (also useful for Step 2 identity fields when no
   arXiv ID is involved):

   ```bash
   "$PYTHON_BIN" tools/zotero_fetch.py item <ref> -o raw/tmp/zotero/<key>.json
   ```

2. Download the PDF attachment:

   ```bash
   "$PYTHON_BIN" tools/zotero_fetch.py download <ref>
   ```

   Success prints a JSON record on stdout:

   - `source_path` — PDF under `raw/tmp/zotero/`
   - `metadata_path` — normalized metadata JSON
   - `record` — `title`, `creators` (`Family, Given`), `year`, `doi`,
     `publication_title`, `tags`, `collections`, ...

3. Hand `source_path` to the normal local-PDF pipeline:

   ```bash
   "$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <source_path>
   ```

   Then continue with Step 2 of the main workflow (identity, enrichment,
   page writing) exactly as for a direct `.pdf` drop. Use `record` as a
   cross-check for title/creators/year; S2/DeepXiv enrichment still applies
   when an arXiv ID or DOI is available.

## Failure modes

All failures are fail-closed: non-zero exit, machine-readable JSON on stderr,
nothing half-written (the PDF is staged as `*.part` and renamed only after a
complete, magic-validated write).

| exit | error | meaning | what to do |
|---|---|---|---|
| 2 | (message, not JSON) | malformed reference or missing `ZOTERO_*` credentials | fix the ref form or fill `.env`, then retry |
| 3 | `no_pdf_attachment` | item has no PDF child attachment | ask the user to attach the PDF in Zotero or supply a local path |
| 3 | `file_not_on_server` | attachment record exists but its bytes are not stored on zotero.org (storage sync off, or a metadata-only import) | tell the user to enable file sync / re-attach, retry with `download <ref> --from-attachment-url`, or pass a local path |
| 3 | `attachment_url_fetch_failed` | the `--from-attachment-url` fallback did not return a PDF (dead link, paywall/login HTML, oversize) | report the message; ask for a local path |
| 3 | `zotero_api_error` | item not found (404), auth, or rate limit | verify the key/URL and `.env` credentials |

## Notes

- `--from-attachment-url` is **opt-in**: only after the stored file 404s does
  it fetch the attachment's recorded URL, requiring real PDF magic bytes
  (`%PDF`) under a 200 MB cap.
- Artifacts land under `raw/tmp/zotero/` (skill-writable). Never write Zotero
  artifacts into `raw/{papers,notes,web}` — those are user-owned read-only.
- For anything beyond single-item resolution (collections, tags, exports,
  creating/updating items), use the standalone `$pyzotero` skill.
- Sandbox: inside Codex this tool exits 126 with a SANDBOX GATE banner;
  rerun escalated with the prefix rule from the AGENTS.md table.
