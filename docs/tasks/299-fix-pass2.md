---
file_type: fix-brief
task_id: 299
fix_pass: 2
phase: verify
target_agent: main-code-agent
spec_ref: docs/specs/299-fabrication-mitigation.md
brief_quality_gate: cherry-pick  # User-Override per Chief-Empfehlung; nur 2 Blocker
authority:
  - docs/reviews/code/299-fabrication-mitigation-verdict-pass2.md  # Chief-Authority
  - docs/reviews/code/299-fabrication-mitigation-code-adversary-pass2.md  # C2-004 Source
  - docs/reviews/code/299-fabrication-mitigation-code-review-pass2.md     # C2-002 Source
  - docs/specs/299-fabrication-mitigation.md
created: 2026-05-05
---

# MCA-Fix-Brief Pass 2 — Task 299 (Cherry-Pick: 2 Blocker)

## §0 TL;DR

Pass-2 Verdict: **PASS_WITH_RISKS**, Chief-Empfehlung **PASS_3** (nicht ESCALATE).
Severity-Drop messbar: Pass 1 (2C/3H/9M/12L=26) → Pass 2 (0C/1H/3M/3L=7) =
~3.7x Reduktion, CRITICAL vollstaendig weg.

**User-Wahl Option A (Cherry-Pick mit Override):** fixe nur die 2 Blocker:

1. **C2-004 [HIGH, REGRESSION]** — Pre-commit Filter `^schema_version:\s*1$` rejects legitime quoted/whitespace/comment v1 Forms.
2. **C2-002 [MEDIUM]** — `_normalize_fm_indent` lebt noch im hot path mit DEPRECATED-Doc-Status.

Die anderen **5 Findings** (1H verschoben, 3M, 3L) gehen ins Backlog als
Folge-Task. Buddy legt diesen Folge-Task nach deinem Return separat an.

**Pflicht-Reihenfolge:** Verdict-File pruefen (Pflicht, dort sind die genauen Lines + Pointer pro Cluster), dann fixen, dann L0 + Tests.

---

## §1 Authority

Primaere Authority: **`docs/reviews/code/299-fabrication-mitigation-verdict-pass2.md`** §3 (NEW Findings konsolidiert) — dort sind die Cluster IDs C2-001..C2-007 mit Pointer-Block + Recommendation.

Bei Cluster-Detail-Bedarf: Adversary-File (`code-adversary-pass2.md`) fuer C2-004 + Code-Review-File (`code-review-pass2.md`) fuer C2-002.

## §2 Fix-Scope (NICHT-VERHANDELBAR fuer diese 2)

### §2.1 C2-004 [HIGH, REGRESSION] — Pre-commit Filter zu eng

**Problem:** Filter `^schema_version:\s*1$` matched NUR plain `schema_version: 1`. Legitime YAML-Forms werden silent gedropped:
- `schema_version: "1"` (quoted)
- `schema_version: 1   ` (trailing whitespace)
- `schema_version: 1  # comment` (inline comment)
- `schema_version:1` (kein Space — eher unueblich aber YAML-valid)

Validator selbst akzeptiert via `isdigit()` alle Forms. Filter und Validator sind asymmetrisch. Konsequenz: Pre-commit Check 13 schleift legitime Reviewer-Outputs durch ohne sie zu pruefen — Backstop unwirksam fuer N% Files.

**Source:** `orchestrators/claude-code/hooks/pre-commit.sh` Filter-Block (~Z.551-565 per Pass-1-Fix-Anchor).

**Fix-Hinweis:** Filter zu Validator-Symmetrie bringen. Optionen:
- Robustere Regex: `^schema_version:\s*[\"\']?1[\"\']?\s*(\#.*)?$`
- Oder: Filter-Logik in Python umlagern (Validator-import statt grep)
- Oder: weichmaschiger Filter `grep -E "schema_version:.*1"` + Validator-Lese-und-Parse-Authority

Entscheidung dem MCA, aber Test-Coverage muss saemtliche 4 oben genannte Forms abdecken.

**Test-Pflicht (NEW):** Add Test in `tests/fabrication_mitigation/test_hook.py` oder `test_validator.py`: pro Form (`schema_version: 1`, `"1"`, trailing whitespace, inline comment) ein Test der pre-commit-Filter durchlaesst + Validator korrekt validiert.

### §2.2 C2-002 [MEDIUM] — `_normalize_fm_indent` Hot-Path-Drift

**Problem:** Pass-1-Fix CC-008 hat `_normalize_fm_indent` als deprecated dokumentiert + conftest.py auf explizite Frontmatter-Konstruktion umgebaut. **ABER:** der Helper lebt noch in `_parse_frontmatter()` (production hot path) und wird weiter aufgerufen. 2-Reviewer-Konvergenz (code-review F-CR2-002 + code-adversary F-CA-PASS2-003 identische Root-Cause).

**Source:** `scripts/validate_evidence_pointers.py:325-338` per Pass-1-Anchor.

**Fix-Hinweis:** Helper aus `_parse_frontmatter()` entfernen. Per code-review-Befund: conftest.py wurde umgebaut, also ist Helper im Production-Pfad nicht mehr noetig. Bei Real-World-File mit mixed-indent: der ist eh kaputtes YAML und sollte parse-error nicht silent-fix bekommen.

**Test-Pflicht:** existing Tests muessen weiter PASS. Wenn Helper-Removal einen Test bricht: dieser Test war auf Symptom-Patch-Verhalten verlassen — Test umbauen auf intended Behavior (parse-error bei mixed-indent oder explizite Frontmatter-Form-Pflicht).

### §2.3 NICHT zu fixen in Pass 2 (Folge-Task Backlog)

Per User-Override-Pattern (Skill code_review_board §5): die folgenden 5 Findings gehen als 1 Sammel-Folge-Task ins Backlog. Buddy legt nach deinem Return an.

- C2-001 [HIGH] — Tier-1-Multi-Workflow-Drift: 4 Skill-Refs in workflow.yaml ohne `pointer_check`-Schutz
- C2-003 [MEDIUM, adversary F-CA-PASS2-002] — CC-004 empty-string-Resolution umgeht HARD-policy mit falscher Error-Klasse
- C2-005 [MEDIUM, adversary F-CA-PASS2-005] — CC-020 single-read-pattern unvollstaendig
- C2-006 [MEDIUM, adversary F-CA-PASS2-004] — Per-Finding-Counter (CC-009 Option b) nicht impl
- C2-007 [LOW, code-review F-CR2-003 + spec-fit F-CF-008] — Layer-Drift `scripts/` vs `scripts/lib/` ohne Phase-2-Trigger + §11.3 Tabelle CC-013-Spec-Drift-Heilungsrichtung Doku

(Genauer Inhalt + Pointer im Verdict-File §3.)

---

## §3 Doku-Update-Pflicht (User-Add aus Pass 1 weiter gueltig)

- **Build-State-File update:** `docs/build/2026-05-04-task-299-fabrication-mitigation.md` mit Pass 2 PASS_WITH_RISKS Eintrag + Fix-Cycle Pass 2 (2 Blocker) + Pass 3 placeholder + 5-Folge-Task-Liste.
- **Spec 299 §11.3 NEW Tabelle Update:** wenn die 2 Pass-2-Fixes Spec-Amendment verlangen (vermutlich C2-004 ja, weil §5 Filter-Spec ggf. Spec-Form-Klarstellung braucht): same block-commit.
- **KEINE Discovery diesmal** — Pass-2-Fix ist klein + scoped, nicht discovery-wuerdig.

---

## §4 L0-Pflicht NACH Fix

```bash
# In MCA-Shell (falls verfuegbar):
ruff check scripts/ orchestrators/claude-code/hooks/
mypy scripts/

# Sicher verfuegbar:
python3 -m py_compile scripts/validate_evidence_pointers.py scripts/workflow_engine.py
bash -n orchestrators/claude-code/hooks/pre-commit.sh
python3 -m pytest tests/fabrication_mitigation/ -v 2>&1 | tail -30
python3 scripts/workflow_engine.py --validate

# Plus Filter-Coverage-Test (NEW fuer C2-004):
# 4 Forms muessen Filter durchlaufen + Validator korrekt validieren
```

Erwartung post-Fix:
- 91 PASS + 2 SKIP (von Pass 1) + neue Tests aus C2-004 Fix → 93+ PASS + 2 SKIP
- engine --validate PASS
- C2-002: existing Tests weiter PASS oder explizit umgebaut
- C2-004: 4 NEW Tests (Filter + Validator-Symmetrie)

---

## §5 RETURN-SUMMARY-Format

```markdown
## RETURN-SUMMARY — Pass 2 Fix (2 Blocker)

**Phase-Status:** done | partial | blocked

**Findings-Adressiert:**
| Cluster | Status | Files-Touched |
|---|---|---|
| C2-004 | FIXED | orchestrators/claude-code/hooks/pre-commit.sh:NN-NN, tests/.../test_NN.py NEW |
| C2-002 | FIXED | scripts/validate_evidence_pointers.py:NN-NN |

**Files-Changed:**
- edited: <liste>

**Spec-Amendments:** (wenn welche)
- §X.Y: <was geaendert + warum>

**L0-Status:** PASS / FAIL (Errors Liste)
**Test-Status:** N PASS + 2 SKIP + M neue (von 91 → ?)
**Engine-Validate:** PASS
**Validator-Self-Test (Dogfooding):** exit 0 gegen Pass-2-Verdict-File
**Stop-Reason:** keine
**Naechster-Schritt:** Pass 3 Re-Review (L1 Focused, kleiner Scope)
```

---

## §6 Stop-Conditions

STOP wenn:
- C2-004 Fix bricht legitime non-v1-Files (Filter zu permissiv jetzt)
- C2-002 Helper-Removal bricht > 2 existing Tests
- Spec-Amendment widerspricht §11.2 Pass-2 Resolution
- Anderes Pass-2-Finding (C2-001/003/005/006/007) wird durch dein Fix verschlimmert

Nicht STOP fuer:
- routine Fix-Touchpoints
- Spec-Amendment im Same-Block-Commit (erlaubt)
- 1-2 neue Tests die initial RED sind und durch Fix GREEN werden

---

## §7 Cross-References

- Pass-2-Verdict (Authority): `docs/reviews/code/299-fabrication-mitigation-verdict-pass2.md`
- Pass-2-Reviewer-Files: `docs/reviews/code/299-fabrication-mitigation-{code-review,code-adversary,code-spec-fit}-pass2.md`
- Pass-2-Brief: `docs/reviews/code/299-fabrication-mitigation-brief-pass2.md`
- Pass-1-Verdict (Tracking-Tabelle 26 Cluster): `docs/reviews/code/299-fabrication-mitigation-verdict.md`
- Pass-1-Fix-Brief: `docs/tasks/299-fix-pass1.md`
- Spec: `docs/specs/299-fabrication-mitigation.md` (mit 7 Pass-1-Amendments)
- Build-State: `docs/build/2026-05-04-task-299-fabrication-mitigation.md`
