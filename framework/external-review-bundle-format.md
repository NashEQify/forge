# External Review Bundle Format Spec

**Tier:** 1 (operational, next to `agent-patterns.md`)
**Status:** Active — required format when external discipline review
is triggered (Pattern 5 + 6 in `agent-patterns.md`).

**See also:** [arch-doc/04 §25 External-Review-Bundle mechanics](../architecture-documentation/04-core-concepts.md) (concept context) ·
[Pattern: External reviewer bundle in agent-patterns.md](agent-patterns.md) (bundle mechanic)

---

## Purpose

External review bundle is the packaged artifact set an external reviewer
(claude.ai sparring partner / future Buddy / user directly) needs to
substantively (not only structurally) verify council synthesis discipline.

**Failure modes this bundle format solves:**
- reviewer has synthesis but not member files -> structural-only review
- filename conflicts across council folders -> wrong member files uploaded
- reviewer runs without self-sanity-check -> incomplete trust output

**Pattern lesson 423:** 5 of 8 anti-pattern replication checks were only
structurally verifiable because member files (388 versions instead of
423 versions) were in the upload folder. Decision-lock trust was legit
but not complete.

---

## Required format

External review bundle lives under
`docs/reviews/external/YYYY-MM-DD-<topic>-bundle/` or analogous path.

### Frontmatter (required)

```yaml
---
review_topic: <council-topic>
council_id: <council-folder-name, e.g. "2026-05-02-388-d5-recouncil">
created: YYYY-MM-DD
maintainer: <who prepared bundle>
upload_inventory_verified: <YYYY-MM-DD by name>
---
```

### Body — 5 sections (required)

#### §1 Required upload list (unambiguous per file)

```markdown
## §1 Required Upload List

Reviewer needs ALL files below in the upload folder. Paths are explicit.
If there is filename conflict with other council folders, reviewer MUST
use the council-id subfolder.

| # | File | Path | Purpose |
|---|---|---|---|
| 1 | synthesis.md | `docs/reviews/council/<council-id>/synthesis.md` | synthesis output (primary) |
| 2 | briefing.md | `docs/reviews/council/<council-id>/briefing.md` | council briefing (context) |
| 3 | pipeline-architect.md | `docs/reviews/council/<council-id>/pipeline-architect.md` | member 1 output |
| 4 | dse.md | `docs/reviews/council/<council-id>/dse.md` | member 2 output |
| 5 | pcc.md | `docs/reviews/council/<council-id>/pcc.md` | member 3 output |
| 6 | opsrel.md | `docs/reviews/council/<council-id>/opsrel.md` | member 4 output |
| 7 | adversary.md | `docs/reviews/council/<council-id>/adversary.md` | adversary member (required role) |
| 8 | (for inversion pattern) erst-synthesis.md | `docs/reviews/council/<erst-id>/synthesis.md` | compare first-lean vs re-lean |
```

**Required member files per council mode:**
- architectural council: 4 domain members + 1 adversary = 5 member files
- re-council (post NEW INPUTS): same 5 + first-council synthesis

#### §2 Reviewer self-sanity-check (required pre-step)

```markdown
## §2 Reviewer Self-Sanity-Check

First required action BEFORE any discipline review. Reviewer checks per
member file:

1. **Header/date check:** does date in file header match `council_id` from §1?
2. **Topic check:** does file address the council topic? (read first 10 lines)
3. **Council-ID check:** when file header names council ID explicitly,
   does it match bundle frontmatter?

On mismatch (e.g. 388 member file instead of 423 member file):
- **Reviewer pre-marks:** "member file from wrong context — structural
  pattern review instead of substantive"
- **Verdict reflects this:** all checks requiring member-file content
  become `PASS structural`, not `PASS substantive`.

**Output of this section:** one entry per member file with
`Sanity-Check: PASS / FAIL (mismatch detail)`.
```

#### §3 Reviewer output format (substantive vs structural)

```markdown
## §3 Reviewer Output Format

Reviewer verdict per anti-pattern check has two tiers:

| Tier | When |
|---|---|
| `PASS substantive` | member-file content itself verifies synthesis claim (e.g. grep on citation range in member file matches) |
| `PASS structural` | synthesis contains required pattern (e.g. citations) but member-file content is not directly verifiable (self-sanity-check FAIL or member file unavailable) |
| `FAIL` | required pattern missing OR member-file content contradicts synthesis claim |
| `N/A` | anti-pattern check not relevant for this council mode |

**Decision-lock trust** is proportional to substantive pass rate,
not structural pass rate. Example:
- 8/8 substantive PASS -> trust HIGH
- 5/8 substantive PASS + 3/8 structural PASS -> trust MEDIUM (worth re-bundle with correct member files)
- 0/8 substantive PASS, 8/8 structural PASS -> trust LOW (bundle prep error, external review essentially blind)
```

#### §4 Anti-pattern check list (required by council mode)

```markdown
## §4 Anti-Pattern Checks

For architectural re-council with inversion pattern (e.g. 388/421/423):

| # | Anti-pattern | Required check |
|---|---|---|
| 1 | argument-decisive override (388 H2) | §4.4 STOP check visible in synthesis; override against voting majority only when argument-decisive converges |
| 2 | §1 position-map consolidation visibility (421 #4) | §1 has secondary-argument carrier per member; §3 convergence claims carry member-file range citations |
| 3 | adversary sole-found pattern (388/423 replicated) | discovery in synthesis correlates with adversary output |
| 4 | NEW-V-001 test-confirms-spec | re-lean reasons are risk-cap self-triggering, not first-position confirmation |
| 5 | external-reviewer member-file access (423 #5) | self-sanity-check §2 executed; substantive-vs-structural markers set |
```

#### §5 Audit trail (optional but recommended)

```markdown
## §5 Audit-Trail

- 2026-05-02T10:00 — bundle created, 8 files in §1 required upload list
- 2026-05-02T10:15 — maintainer inventory check: all 8 files present
  in source paths, filename conflict with 388 council avoided by
  council-id subfolder
- 2026-05-02T10:30 — reviewer dispatch via sparring partner session
- 2026-05-02T11:00 — reviewer output: 7/8 substantive PASS + 1 PASS
  with sub-observation
```

---

## Filename disambiguation convention

Three options depending on bundle distribution path:

1. **Subfolder per council** (current convention):
   - `docs/reviews/council/<date>-<topic>/<role>.md`
   - OK if user uploads from correct subfolder
   - failure mode: user does flat uploads across multiple subfolders -> filename conflict

2. **Filename prefix with council ID** (more fail-safe):
   - `<council-id>-<role>.md`, e.g. `423-pipeline-architect.md`
   - unambiguous even for flat uploads
   - trade-off: verbose names, subfolder becomes redundant

3. **Both combined** (max disambiguation):
   - subfolder AND prefix
   - strict but fail-safe

**Recommendation:** subfolder by default. During external-review prep
(bundle maintainer step §5.4), maintainer MUST check for filename
conflicts with other active council folders. If conflicts exist,
temporarily rename files with prefix in the bundle subfolder.

---

## Maintainer requirement: upload inventory verification pre-dispatch

Bundle creator MUST verify pre-dispatch:

```bash
# 1. Required upload list complete?
for file in $REQUIRED_UPLOAD_LIST; do
  test -f "$file" || echo "MISSING: $file"
done

# 2. Filename conflict check?
basenames=$(echo "$REQUIRED_UPLOAD_LIST" | xargs -n1 basename | sort)
duplicates=$(echo "$basenames" | uniq -d)
[ -n "$duplicates" ] && echo "DUPLICATE filenames: $duplicates"

# 3. Date consistency check?
# Per member-file: scan first 10 lines for date/council-id consistency
```

On failure: do not dispatch bundle, fix first.

---

## Consumers

| Consumer | How external-review bundle is used |
|---|---|
| User-explicit external-review trigger | prepare bundle by this format + reviewer dispatch |
| `skills/council/SKILL.md` architectural council | optional Pattern 5 + 6 when argument-decisive-override decision occurs |

---

## Anti-patterns

- **DO NOT** dispatch a bundle without §1 required-upload-list verification.
  **INSTEAD** run maintainer inventory check pre-dispatch. **Why:** 423
  showed empirically that upload-folder content can differ from maintainer
  expectation (old council files with identical names).

- **DO NOT** run reviewer without self-sanity-check step.
  **INSTEAD** require §2 as pre-step in reviewer prompt. **Why:**
  self-sanity-check catches filename-conflict issues maintainer inventory
  check cannot catch (e.g. reviewer-side upload conflicts).

- **DO NOT** accept reviewer output without substantive-vs-structural markers.
  **INSTEAD** require §3 output format. **Why:** decision-lock trust is
  proportional to substantive pass rate; structural-only pass can create
  false high trust.

- **DO NOT** decide filename disambiguation ad hoc.
  **INSTEAD** document convention per bundle. **Why:** inconsistent filename
  conventions make cross-bundle comparison and future re-audits harder.

---

## Relation to Pattern 5 + 6 (`agent-patterns.md`)

- Pattern 5 (external discipline review): WHEN external review is worth it
  (4 trigger conditions). This format spec becomes relevant when trigger fires.
- Pattern 6 (external-reviewer bundle mechanics): HOW the bundle must be
  prepared. This format spec implements those mechanics.

Plus Pattern 4 (§1 position-map consolidation visibility): synthesis must
include secondary argument carriers so bundle reviewers can spot-check via
member-file range citations.

---

**End of spec.** Format is binding when external discipline review is
triggered. Compliance is not mechanically enforced (no hook), but
bundle-maintainer upload inventory verification and reviewer self-sanity
check enforce compliance through their own mechanics.
