# Plan 007: Sync script wiki/ → site/content/ + full mapped build

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in the index (`plans/README.md`).
>
> **Drift check (run first)**: In `/Users/tai/workspace/research-projects/autosci`,
> branch `spike/quartz-site` must exist locally (tip `09ddf07` unless reconciled).
> `site/SITE-SPEC.md` and `site/SPIKE-NOTES.md` must be present on it. If missing,
> STOP and report.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW (new branch, local-only unless told otherwise)
- **Depends on**: 006 (spike + spec)
- **Category**: direction / build
- **Planned at**: autosci `spike/quartz-site` @ `09ddf07`, 2026-10-02

## Why this matters

The spike proved 5 sample pages render with zero rewrites, but `site/content/`
is still 5 hand-copied files. The operator wants: ingest writes `wiki/` →
one script syncs → site rebuilds, all on one branch. This plan builds that
sync script and validates the FULL mapped wiki through the build. It does NOT
publish or deploy anything (privacy Q1 still open — full build stays local).

## Current state

- Work happens in the autosci clone (`origin` = fork `taixuann/AutoSci`,
  PUBLIC — see STOP conditions). New branch `site/full-sync` off
  `spike/quartz-site`; worktree under `/private/tmp`.
- Content mapping (from `site/SITE-SPEC.md`, reuse verbatim):
  PUBLISH: `wiki/papers/` (6), `wiki/concepts/` (6), `wiki/methods/` (1),
  `wiki/index.md` + `wiki/log.md` (index needs rework into a landing page).
  EXCLUDE: `wiki/outputs/` (internal reports), `wiki/graph/` (working notes +
  `edges.jsonl`; quartz generates its own graph), `wiki/canvases/*.canvas`
  (untested with v5), empty dirs (experiments/foundations/ideas/topics/Summary —
  `.gitkeep` only), `wiki/.obsidian/`, repo-root `raw/` (ingestion scratch).
  REVIEW-GATED: `wiki/people/` (8 md, names/affiliations — default EXCLUDE
  until the operator approves; the script takes an allowlist flag for it).
- `wiki/` entity files are gitignored in the fork (private-by-default). The
  script reads them from disk — no `git add -f` on wiki files in this plan.
- Quartz v5, node ≥ 22 (local v22.22.3). Sample build: ~9 s for 6 files.
  Full mapped content = 15 files (6 papers + 6 concepts + 1 method + index.md
  + log.md) — expect well under a minute.

## Commands you will need

| Purpose | Command (cwd = worktree `site/`) | Expected on success |
|---|---|---|
| Install deps | `npm install` (fresh worktree has no `node_modules`) | exit 0; first-time plugin phase can take ~25–30 min — see `SPIKE-NOTES.md`, run it with a long timeout or backgrounded; do NOT kill it early |
| Sync | `./scripts/sync-content.sh` (or the python equivalent you write) | exit 0, `content/` mirrors mapping |
| Build | `npx quartz build` (v5; see spike notes for exact invocation) | exit 0, HTML emitted |
| Idempotency | run sync twice, `diff -r` content snapshot | no differences second run |

## Scope

**In scope**: new `site/scripts/sync-content.*`, `site/content/` snapshot for the
mapped subtrees, `site/SYNC.md` (usage doc, 10 lines), branch `site/full-sync`.

**Out of scope**: deploying anywhere; editing any `wiki/` file; touching
`people/` (excluded by default); `skyllwt/AutoSci`; pushing the branch
(default local-only, state your choice); `research-projects` monorepo.

## Steps

### Step 1: Write the sync script

Script behavior (implement exactly):
1. Source = `../wiki/` (repo-relative, no absolute paths).
2. Mirror the publish set into `site/content/`:
   - subtree files: `wiki/papers/*.md`, `wiki/concepts/*.md`, `wiki/methods/*.md`
     → same relative paths under `site/content/`;
   - top-level files: `wiki/index.md` → `site/content/index.md`,
     `wiki/log.md` → `site/content/log.md`;
   - delete files under `site/content/` whose wiki source no longer exists
     (keeps the snapshot fresh after deletions, e.g. `$reset`).
   NOTE: `wiki/index.md` is a YAML slug registry and SITE-SPEC Q4 says it needs
   rework into a real landing page — that rework is OUT of scope here. Copying
   it as-is is acceptable for this plan; add a `TODO(index-rework)` comment in
   the script and say so in the report. Do not delete the stock quartz scaffold
   `content/index.md` until that rework exists.
3. `people/` only when invoked with `--include-people` (default off).
4. Everything else ignored. Script prints `copied N, removed M, skipped K`.
5. Exit non-zero with a clear message if `../wiki` is missing (wrong cwd guard).

**Verify**: run twice → second run prints `copied 0, removed 0` (idempotent);
`diff` a copied file against its wiki source → identical bytes.

### Step 2: Full mapped build

Run sync, then `npx quartz build`. If `node_modules` is missing (fresh
worktree), run `npm install` first — its plugin phase is slow (~25–30 min,
see `SPIKE-NOTES.md`); use a long timeout / background run. Record new
incompatibilities (if any) in `site/SPIKE-NOTES.md` (append, don't rewrite
the spike's notes).

**Verify**: build exit 0; count emitted HTML ≈ mapped md count.

### Step 3: Commit on `site/full-sync`

Commit script + content snapshot + `SYNC.md` + notes. Conventional message.
Report tip hash. Local-only unless remote CI is needed (default: don't push).

## Done criteria

- [ ] `site/scripts/sync-content.*` exists, idempotent (second run zero-change)
- [ ] Full mapped build exits 0 (evidence in report)
- [ ] `people/` excluded by default, included only with explicit flag
- [ ] No `wiki/` file modified; no push without instruction
- [ ] Index status row updated

## STOP conditions

- Full content needs systematic rewrites (beyond 2–3 front-matter tweaks) — document, STOP.
- Any step wants to `git add -f` a wiki file or push to the PUBLIC fork — STOP, privacy gate (Q1) belongs to the operator.
- Scaffold build breaks on full content but passed on samples — bisect to the file, report, don't rewrite content.

## Maintenance notes

- Plan 008 wires this script as the final step of every wiki-writing skill.
  Keep the script's CLI stable (`--include-people` contract included).
- Reviewer focus: the publish/exclude list must match SITE-SPEC.md exactly;
  any drift between them is a bug.
