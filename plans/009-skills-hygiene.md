# Plan 009: Skills hygiene — fix the paper-plan slug typo + restore pyzotero i18n parity

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in the index (`plans/README.md`).
>
> **Drift check (run first)**: `git -C . log --oneline -1` should be
> `95c581b` or later; `.agents/.current-lang` must read `en`. The typo lines
> must still be present (grep below). If anything differs, STOP and report.

## Status

- **Priority**: P1 (tiny, fixes a real execution bug)
- **Effort**: S
- **Risk**: LOW (two mechanical fixes + regen)
- **Depends on**: none (recommended BEFORE 008 so its regen picks these fixes up cleanly)
- **Category**: correctness / tech-debt
- **Planned at**: autosci `autosci-codex` @ `95c581b`, 2026-10-02

## Why this matters

Two audit findings (2026-10-02):

1. **Real bug in `paper-plan`**: the add-edge commands use
   `--from "outputs$paper-plan-{slug}-{date}"`. In bash, `$paper` expands
   (empty) → the slug becomes `outputs-plan-{slug}-{date}` instead of
   `outputs/paper-plan-{slug}-{date}` → the graph edge points at a wrong or
   missing node. Present in all 3 tracked copies (active + en + zh), 2 lines each.
2. **pyzotero drift**: the `pyzotero` skill (15 files) exists only in the
   generated `.agents/skills/`, not in `i18n/en/skills/` or `i18n/zh/skills/`.
   The i18n trees are the source of truth (`AGENTS.md`); `setup.sh` regenerates
   active from them. The skill survives today only because `.agents/skills` is
   committed and setup.sh never deletes — switching language or a fresh
   regeneration is inconsistent, and `$pyzotero` is referenced by `ingest` in
   BOTH languages.

## Current state

- Typo sites (exact): `.agents/skills/paper-plan/SKILL.md:300,305`,
  `i18n/en/skills/paper-plan/SKILL.md:300,305`,
  `i18n/zh/skills/paper-plan/SKILL.md:300,305`.
  Intended string: `outputs/paper-plan-{slug}-{date}` (see line 29 of the same
  file: `wiki/outputs/paper-plan-{slug}-{date}.md` — the page path).
- `pyzotero` active files: `.agents/skills/pyzotero/` — `SKILL.md` + 14
  `references/*.md` (third-party, MIT, from K-Dense AI per its frontmatter
  `metadata.github-*`). Frontmatter has `name:` and `description:` (name is at
  line 25 inside the frontmatter block — valid, Codex only requires presence).
- `i18n/en/skills` and `i18n/zh/skills` each have 29 dirs; neither has
  `pyzotero`. `.agents/skills` has 31 dirs (29 + `pyzotero` +
  `shared-references`; `shared-references` is regenerated from
  `i18n/$LANG/shared-references` by setup.sh — expected, not drift).
- Regen command: `./setup.sh --lang en` (current marker `.agents/.current-lang`
  = `en`). It copies `i18n/en/skills/*` over `.agents/skills/*` and
  `i18n/en/shared-references/*.md` over `.agents/skills/shared-references/`.

## Commands you will need

| Purpose | Command (cwd = autosci clone) | Expected on success |
|---|---|---|
| Typo present | `grep -rn 'outputs\$paper-plan' i18n .agents/skills` | 6 lines across 3 files |
| Typo gone | `grep -rn 'outputs\$paper-plan' i18n .agents/skills` | no matches |
| Correct form | `grep -rn 'outputs/paper-plan-{slug}-{date}"' i18n .agents/skills` | 6 lines (the `--from` args) |
| pyzotero parity | `ls i18n/en/skills/pyzotero i18n/zh/skills/pyzotero` | both exist |
| Content parity | `diff -rq i18n/en/skills/pyzotero .agents/skills/pyzotero` and same for zh | no output |
| Regenerate | `./setup.sh --lang en` | exit 0 |
| Post-regen check | `diff -rq i18n/en/skills .agents/skills --exclude=shared-references` | no output |

## Scope

**In scope**: the 3 paper-plan `SKILL.md` files (typo fix);
`.agents/skills/pyzotero/` copied INTO `i18n/en/skills/pyzotero/` and
`i18n/zh/skills/pyzotero/`; the regenerated `.agents/skills/` after
`./setup.sh --lang en`; commit on branch `site/skills-hygiene` (worktree under
`/private/tmp`).

**Out of scope**: everything else in the skill trees; `references/*.md` of
other skills; `site/`; the sync step for writers (plan 008 owns that);
translating pyzotero content (English copy in both trees is acceptable for a
third-party vendored skill — note it in the commit message; translation is a
separate task if wanted).

## Steps

### Step 1: Fix the typo in the i18n sources

Fix `i18n/en/skills/paper-plan/SKILL.md` and
`i18n/zh/skills/paper-plan/SKILL.md`: replace the two occurrences each of
`"outputs$paper-plan-{slug}-{date}"` → `"outputs/paper-plan-{slug}-{date}"`.
Do not touch other lines.

**Verify**: `grep -rn 'outputs\$paper-plan' i18n` → no matches;
`grep -c 'outputs/paper-plan-' i18n/en/skills/paper-plan/SKILL.md` → 3
(the doc path line + 2 fixed command lines, as in zh).

### Step 2: Add pyzotero to both i18n trees

Copy the tracked active skill into both sources (it is currently the only
copy): `cp -R .agents/skills/pyzotero i18n/en/skills/pyzotero` and
`cp -R .agents/skills/pyzotero i18n/zh/skills/pyzotero`.

**Verify**: `diff -rq .agents/skills/pyzotero i18n/en/skills/pyzotero` → no
output; same for zh; `ls i18n/en/skills | wc -l` → 30 and zh → 30.

### Step 3: Regenerate the active tree

`./setup.sh --lang en`.

**Verify**: exit 0. Then `grep -rn 'outputs\$paper-plan' .agents/skills` → no
matches (regen applied the typo fix to the active copy);
`diff -rq i18n/en/skills .agents/skills --exclude=shared-references` → only
`shared-references` excluded, no other output.

### Step 4: Commit

Commit `i18n/en`, `i18n/zh`, and regenerated `.agents/skills` on
`site/skills-hygiene`. Conventional message noting pyzotero is vendored
third-party content kept in English in both trees. Report tip hash.

## Done criteria

- [ ] `grep -rn 'outputs\$paper-plan' i18n .agents/skills` → no matches
- [ ] `grep -rn 'outputs/paper-plan-{slug}-{date}"' i18n .agents/skills` → 6 lines
- [ ] pyzotero exists in `i18n/en/skills/` and `i18n/zh/skills/`, byte-identical to the active copy
- [ ] `./setup.sh --lang en` ran; post-regen diff clean (minus shared-references)
- [ ] Commit on `site/skills-hygiene`; no push
- [ ] Index status row updated

## STOP conditions

- The typo count is not 6 or the text differs from the excerpt above.
- `./setup.sh` wants to do anything beyond language activation that touches
  user state outside `.agents/`/`AGENTS.md` (report before letting it).
- pyzotero's active copy differs from what's described (15 files).

## Maintenance notes

- After this, any language switch (`./setup.sh --lang zh`) keeps pyzotero
  consistently. If the operator wants a Chinese pyzotero, that's a translation
  task — do not machine-translate third-party API docs silently.
- Plan 008's refactor depends on this ordering only for cleanliness; 009 may
  land before or after 008, but before is recommended.
