# Plan 008: Audit wiki-writing skills, add sync as final step

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in the index (`/Users/tai/.opencode/plan/README.md`).
>
> **Drift check (run first)**: Plan 007 must show DONE and its sync script must
> exist on branch `site/full-sync` (or reconciled equivalent). `site/scripts/sync-content.*`
> usage: `./scripts/sync-content.sh` from `site/`, `--include-people` flag contract.
> If the script or its CLI differs, STOP and report.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED (edits skill definitions — behavior-changing; mitigated by review + dry run)
- **Depends on**: 007
- **Category**: tech-debt / behavior
- **Planned at**: autosci `autosci-codex` @ `feca5e0`, 2026-10-02

## Why this matters

The operator's model: ingest (or any pipeline) writes `wiki/` → site must follow
on the same branch. Today no skill knows the site exists, so content and site
drift apart after every run. This plan finds every skill that writes wiki
content and appends one final step — run the plan-007 sync script — so the
site snapshot stays fresh by construction. (Build/serve stays manual or
deploy-time; the skill step is sync only, per operator's words.)

## Current state

- Skills live in `autosci/.agents/skills/` (31 dirs: ask, check, daily-arxiv,
  discover, edit, exp-*, hiera-experiment, ideate, ingest, init, novelty,
  paper-*, poster, prefill, pyzotero, rebuttal, refine, research, reset, review,
  setup, shared-references, survey, visualize, ...). ~15 reference `wiki/`
  somewhere; referencing ≠ writing — the audit below decides.
- Writer candidates (unconfirmed — verify each): `ingest`, `daily-arxiv`,
  `discover`, `research`, `paper-draft`, `visualize` (earlier commit restyled
  its Obsidian export — check whether it writes wiki-adjacent files).
- Skill convention (match it): `SKILL.md` holds the procedure; references live
  under `references/`. Keep edits in the same voice/structure as the file.
- Work on a new branch `site/skills-sync-step` off `autosci-codex`
  (NOT off the site branches — skill edits are independent of site content).
  Worktree under `/private/tmp`. Local-only unless told otherwise.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Find writers | `grep -rl 'wiki/' .agents/skills/ --include='*.md'` then read each hit | writer list with evidence |
| Sync dry run | `cd site && ./scripts/sync-content.sh` (from the 007 worktree/branch — read-only use; do NOT copy the script, reference its path) | exit 0 |
| Verify edits | `grep -rn 'sync-content' .agents/skills/ --include='*.md'` | one hit per writer skill, zero elsewhere |

## Scope

**In scope**: `SKILL.md` (and where the procedure actually lives, its
`references/*.md`) of confirmed wiki-writing skills — one appended final step each.

**Out of scope**: the sync script itself (007 owns it — do not modify);
`site/` content; deploying; `people/` policy (007's default stands);
`skyllwt/AutoSci`; pushing (default local-only).

## Steps

### Step 1: Audit — who writes wiki/?

For each of the ~15 grep hits, read the surrounding procedure and classify:
WRITER (creates/overwrites files under `wiki/`) vs READER (only reads/links).
Record the verdict per skill with a one-line evidence quote (file:line).

**Verify**: a table in your report: skill → WRITER/READER → evidence. If a
skill's role is ambiguous after reading, mark UNCERTAIN and STOP for that
skill only (continue the rest, list it in the report).

### Step 2: Append the sync step

For each WRITER skill, append a final step in the file's own structure:

```text
Final step — sync the public site snapshot: run the site sync script
(site/scripts/sync-content.sh from the site/ dir on branch site/full-sync).
Do not build or deploy; do not touch people/ content.
```

Adapt wording to each file's voice; keep it to 2–3 lines. Same step text
everywhere (consistency is the point — a reviewer should be able to grep it).

**Verify**: `grep -rn 'sync-content' .agents/skills/ --include='*.md'` shows
exactly the writer set from Step 1, nothing else.

### Step 3: Dry run

Pick the smallest WRITER skill (likely `ingest` init-mode or `daily-arxiv`
single-paper path — your call, state it). Walk its procedure up to but NOT
including any network/API call (no fetches, no writes to wiki/), then execute
only the new final step for real (sync script run, exit 0 expected). This
proves the step is runnable as written.

**Verify**: sync exit 0; `git status` in the site worktree shows only expected
content-snapshot changes (or none, if wiki unchanged since last sync).

### Step 4: Commit on `site/skills-sync-step`

Conventional commit, local-only. Report tip hash + the writer table.

## Done criteria

- [ ] Writer/reader table for all ~15 candidates, evidence-backed
- [ ] Each WRITER skill ends with the sync step; `grep` shows exact writer set
- [ ] Dry run of one skill's final step: sync exit 0
- [ ] No sync-script modifications; no pushes; no `people/` content touched
- [ ] Index status row updated

## STOP conditions

- A writer skill's procedure can't accommodate a terminal sync step without
  restructuring (e.g. its writes happen inside nested sub-flows) — mark it,
  skip it, report; don't redesign the skill.
- The dry run reveals the sync script CLI differs from plan 007's contract —
  STOP (007 drifted; reconcile first).
- Any UNCERTAIN classifications remain — list them, don't guess.

## Maintenance notes

- New skills that write `wiki/` must include the sync step — add this to the
  skill-authoring checklist (or propose it to the operator as a convention).
- If the sync script's CLI ever changes, this plan's grep becomes the migration
  checklist (every hit must be revisited).
- Reviewer focus: wording consistency across skills + no behavior change to
  existing steps (append-only diffs).
