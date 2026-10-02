# Plan 008: Append the site-sync step to every wiki-writing skill (audit + edit)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in the index (`plans/README.md`).
>
> **Drift check (run first)**: Plan 007 must show DONE and its sync script must
> exist at `site/scripts/sync-content.sh` with usage `./scripts/sync-content.sh`
> (`--include-people` flag included). Also: `git -C . log --oneline -1` should
> be `95c581b` or later; `.agents/.current-lang` must read `en`.
> If any of these differ, STOP and report.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED (edits 24 skill definitions × 2 languages — mechanical but wide; mitigated by grep-verifiable append-only diffs)
- **Depends on**: 007
- **Category**: tech-debt / behavior
- **Planned at**: autosci `autosci-codex` @ `95c581b`, 2026-10-02

## Why this matters

The operator's model: any skill that changes `wiki/` → the site snapshot must
follow on the same branch. Today no skill knows the site exists, so content and
site drift apart after every run. This plan appends one final step — run the
plan-007 sync script — to every skill that writes to `wiki/`, so the snapshot
stays fresh by construction. Build/serve stays manual or deploy-time; the step
is sync only.

## Current state (verified by audit on 2026-10-02)

### Source-of-truth rule (load-bearing)

`AGENTS.md` (active and i18n) states: **"The source for the active skill tree is
`i18n/<lang>/skills`. When changing a workflow, edit the localized source
files, keep English and Chinese copies aligned, then run setup to regenerate
active files."** and **"Codex requires each `SKILL.md` frontmatter to include
both `name` and `description`."**

So: **edit `i18n/en/skills/...` AND `i18n/zh/skills/...`, then run
`./setup.sh --lang en`** (current lang is `en`) to regenerate `.agents/skills/`.
Never edit `.agents/skills/` as the primary source — regeneration overwrites it.

`setup.sh` skill regen block (lines ~157–167): copies every
`"$I18N_DIR/skills"/*` into `.agents/skills/$name/`, then copies
`i18n/$LANG/shared-references/*.md` into `.agents/skills/shared-references/`.
It does not delete stale dirs.

### Verified writer classification (24 writers / 5 non-writers)

Evidence command (repeat per skill to reconfirm; a hit on any of these is a
write): `research_wiki.py (log|set-meta|add-edge|add-citation|transition|init|rebuild-[a-z-]+)`.

- **Content writers (15)** — write pages/edges/metadata:
  `ask`, `exp-design`, `exp-eval`, `exp-pilot-eval`, `exp-run`, `exp-status`,
  `ideate`, `ingest`, `init`, `novelty`, `paper-plan`, `prefill`, `refine`,
  `research`, `survey`
- **Log / appendix writers (8)** — primarily append `wiki/log.md`; some also
  touch published surfaces: `reset` deletes/rewrites pages (`wiki/<entity>/*`,
  `index.md`, graph), `rebuttal` appends `wiki/ideas/*` + `wiki/methods/*`.
  All still get the sync step (published content changes, or `log.md` which is
  published):
  `check`, `discover`, `paper-compile`, `paper-draft`, `poster`, `rebuttal`,
  `reset`, `visualize`
- **Direct writer (1)** — writes wiki files directly (not via research_wiki.py
  write cmds): `edit` (its SKILL.md Outputs: "Updated wiki files, `index.md`,
  `log.md`").
- **Do NOT touch (6)**: `daily-arxiv` (orchestrator; delegates to `$ingest`),
  `exp-pilot-run` (verified 2026-10-02: writes under root-level `experiments/`
  — `experiments/pilot/code/{slug}/`, gitignored `experiments/code/` — NOT
  under `wiki/`; if that ever changes, STOP and report), `hiera-experiment`
  (sidecar; leaves wiki unchanged per its README), `pyzotero` (third-party
  library skill, no wiki writes), `review` (verified 2026-10-02: its Writes
  section says "**None** — read-only query"), `setup` (runs before/wiki-less;
  explicitly "does not touch the wiki").

**Because `wiki/log.md` is in the site publish set (plan 007 mapping), the
log-only writers need the sync step too** — log.md is published content.

### Counts

- `i18n/en/skills` + `i18n/zh/skills`: 29 skill dirs each before plan 009; 30
  each after (pyzotero added). The writer classification above is unaffected —
  pyzotero stays excluded. File lists are identical en↔zh.
- `.agents/skills`: 31 dirs before 009 (29 + `pyzotero` + `shared-references`);
  after 009, 31 (30 + `shared-references`). `shared-references` is regenerated
  from `i18n/$LANG/shared-references` by `setup.sh` — expected.

### Sync step text (canonical — use verbatim)

English (append to `i18n/en/skills/<skill>/SKILL.md`):

```text
## Final step: sync the site snapshot

After the wiki changes above are complete, run the site sync script so the
public site snapshot follows: `site/scripts/sync-content.sh` from the `site/`
directory. Do not build or deploy; do not touch `people/` content.
```

Chinese (append to `i18n/zh/skills/<skill>/SKILL.md`):

```text
## 最后一步：同步站点快照

完成上述 wiki 变更后，运行站点同步脚本，使公开站点快照同步更新：在 `site/`
目录执行 `site/scripts/sync-content.sh`。不要构建或部署；不要触碰 `people/` 内容。
```

Keep it as an appended final section; do not restructure existing steps.
Append-only diffs are a review requirement.

## Commands you will need

| Purpose | Command (cwd = autosci clone) | Expected on success |
|---|---|---|
| Reconfirm writers | `grep -lE "research_wiki.py (log\|set-meta\|add-edge\|add-citation\|transition\|init\|rebuild-[a-z-]+)" i18n/en/skills/*/SKILL.md` + same for `i18n/zh` | the 23 command-list writers above (plus classify `edit`/`exp-pilot-run`/`review` by reading) |
| Append check (en) | `grep -rln 'Final step: sync the site snapshot' i18n/en/skills/` | 24 files |
| Append check (zh) | `grep -rln '最后一步：同步站点快照' i18n/zh/skills/` | 24 files |
| Parity | `diff <(grep -rln 'sync-content' i18n/en/skills \| sed 's\|i18n/en/\|\|') <(grep -rln 'sync-content' i18n/zh/skills \| sed 's\|i18n/zh/\|\|')` | no output |
| Regenerate | `./setup.sh --lang en` | exits 0; `.agents/skills` refreshed |
| Spot-check regen | `grep -rln 'sync-content' .agents/skills/` | 24 files |
| Dry run sync | `cd /private/tmp/rv-exec-007/site && ./scripts/sync-content.sh` (007 worktree) | exit 0 |

## Scope

**In scope**: the 24 writer skills' `i18n/en/skills/<skill>/SKILL.md` and
`i18n/zh/skills/<skill>/SKILL.md` (append-only). Regenerated `.agents/skills/`
(commit it too — the active tree is tracked).

**Out of scope**: `site/` and the sync script (007 owns it); `people/` policy;
non-writer skills; `pyzotero`/`shared-references` hygiene (plan 009); any
`references/*.md` content changes (SKILL.md append only); pushing (default
local-only).

## Git workflow

- New worktree in the autosci clone: `git worktree add -b site/skills-sync-step /private/tmp/rv-exec-008 autosci-codex` (branch is already in use only if repeated — then reuse it).
- Conventional commits; do not push.

## Steps

### Step 1: Reconfirm the writer list (read-only)

Re-run the commands above over `i18n/en/skills/*/SKILL.md` (not just
`.agents/skills`) and reconcile with the classified list. Where the grep list
differs (e.g. a skill writes via direct file edits, like `edit`), read the
skill's Writes/Outputs section and classify. Record the final writer table in
your report. If `exp-pilot-run` or `review` turns out to write under `wiki/`,
STOP and report before continuing.

**Verify**: report table: skill → writer class (content/log/direct/none) →
evidence (file:line or grep hit).

### Step 2: Append the sync step — English tree

For each of the 24 writers, append the canonical English text at the end of
`i18n/en/skills/<skill>/SKILL.md`.

**Verify**: `grep -rln 'Final step: sync the site snapshot' i18n/en/skills/` → 24 files, and `git diff --stat` shows only additions.

### Step 3: Append the sync step — Chinese tree

Same 24 skills, Chinese text, into `i18n/zh/skills/<skill>/SKILL.md`.

**Verify**: `grep -rln '最后一步：同步站点快照' i18n/zh/skills/` → 24 files;
parity command above → no output.

### Step 4: Regenerate the active tree

Preferred: `./setup.sh --lang en` (current lang marker `.agents/.current-lang`
is `en`).

**If `./setup.sh` fails before its language-activation step** (its Step 1–2
check Codex, Python, and install dependencies — unavailable in some
environments), replicate only the activation block (setup.sh lines ~157–168)
by hand:

```sh
for d in i18n/en/skills/*/; do n=$(basename "$d"); mkdir -p ".agents/skills/$n"; cp -R "$d"/. ".agents/skills/$n/"; done
mkdir -p .agents/skills/shared-references
cp i18n/en/shared-references/*.md .agents/skills/shared-references/
```

State in your report which path you used.

**Verify**: exits 0; `grep -rln 'sync-content' .agents/skills/` → 24 files;
`git status --short` shows the regenerated `.agents/skills/*/SKILL.md` modified
(plus nothing unexpected — review before committing).

### Step 5: Dry run the sync step

From the plan-007 worktree (locate it with `git worktree list`; e.g.
`/private/tmp/rv-exec-007/site`), run `./scripts/sync-content.sh`. This proves
the appended instruction is runnable.

**Verify**: exit 0; report its printed counts.

### Step 6: Commit

Commit `i18n/en`, `i18n/zh`, and the regenerated `.agents/skills` on
`site/skills-sync-step`. Conventional message. Report tip hash.

## Done criteria

- [ ] Writer table in report; `exp-pilot-run`/`review` verified as non-writers (or STOP)
- [ ] 24 EN + 24 ZH files contain the canonical step; parity grep empty
- [ ] `./setup.sh --lang en` ran; `.agents/skills` regenerated
- [ ] Dry-run sync exit 0
- [ ] `git diff` is append-only on SKILL.md files (no restructuring)
- [ ] No sync-script modifications; no `people/` content touched; no push
- [ ] Index status row updated

## STOP conditions

- `exp-pilot-run` or `review` writes under `wiki/` (classification surprise).
- The writer grep over `i18n/` disagrees with the table above by more than the
  two direct-writer cases — reconcile before appending.
- `./setup.sh` errors or asks for elevated actions mid-run.
- The dry-run sync script CLI differs from plan 007's contract — reconcile 007 first.
- A skill's structure makes a clean terminal section impossible — skip it, list it, report.

## Maintenance notes

- New skills that write `wiki/` must include the sync step in BOTH i18n trees —
  it belongs in the skill-authoring checklist (operator decision pending).
- If the sync script's CLI changes, this plan's `grep sync-content` list is the
  migration checklist.
- Plan 009 (hygiene: paper-plan typo, pyzotero i18n parity) should land before
  or with this plan so the regen doesn't paper over drift; ordering in the
  index.
- Reviewer focus: append-only diffs; both languages present; exact writer set
  (24), nothing else.
