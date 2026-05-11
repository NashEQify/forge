---
file_type: fix-brief
task_id: 299
fix_pass: 1
phase: verify
target_agent: main-code-agent
spec_ref: docs/specs/299-fabrication-mitigation.md
brief_quality_gate: substantial  # 26 Findings + Cross-Modul + Schema-Touch
authority:
  - docs/reviews/code/299-fabrication-mitigation-verdict.md  # Chief-Authority
  - docs/reviews/code/299-fabrication-mitigation-code-review.md
  - docs/reviews/code/299-fabrication-mitigation-code-adversary.md
  - docs/reviews/code/299-fabrication-mitigation-code-spec-fit.md
  - docs/reviews/code/299-fabrication-mitigation-brief.md
  - docs/specs/299-fabrication-mitigation.md
created: 2026-05-05
---

# MCA-Fix-Brief — Task 299 Pass 1 FAIL

## §0 TL;DR

Code-Review-Board Pass 1: **FAIL (2C / 3H / 9M / 12L = 26 Cluster).** Ironischer
Dogfooding-Befund: das in 299 gebaute Pointer-System hat sich selbst beim
ersten Live-Test als unwirksam fuer real-formatierte Reviewer-Outputs
erwiesen — und genau das aufgedeckt durch das Pointer-System selbst.

**Definition-of-Done fuer Pass 1 Fix:**
1. ALLE 26 konsolidierte Findings gefixt (Skill code_review_board §5
   NICHT-VERHANDELBAR per User-Wahl A).
2. L0 clean nach Fix (ruff + mypy 0 Errors; pre-existing F401 in
   workflow_engine.py:40 darf bleiben — nicht von 299).
3. Alle 83 GREEN-Tests bleiben GREEN (regression-check).
4. Spec 299 mit Spec-Amendments updated wo Code-Fix semantische Aenderung
   verlangt (per spec-co-evolve Pattern, gleicher Block-Commit).
5. Discovery-Eintrag `docs/discoveries/2026-05-05-dogfooding-self-detection.md`
   schreiben (siehe §4).
6. Build-State-File update mit Pass 1 FAIL → Fix → Pass 2.

**Re-Review-Limit:** Pass 1 von max 2 (Foundation-Override fuer 299 als
tier2-harness milestone erlaubt per Chief-Vermerk wenn Severity messbar
droppt).

---

## §1 Authority-Stack

| Authority | Pfad | Rolle |
|---|---|---|
| **Chief Verdict** | `docs/reviews/code/299-fabrication-mitigation-verdict.md` | Konsolidierte 26 Cluster (CC-001..CC-026), Tracking-Tabelle, Fix-Scope, primary Authority |
| **code-review** | `docs/reviews/code/299-fabrication-mitigation-code-review.md` | 11 Findings (2C/0H/3M/6L) — Architektur + Correctness + Performance Lens |
| **code-adversary** | `docs/reviews/code/299-fabrication-mitigation-code-adversary.md` | 11 Findings (1C/3H/4M/3L) — Smart-but-wrong + Race + Edge-Cases Lens |
| **code-spec-fit** | `docs/reviews/code/299-fabrication-mitigation-code-spec-fit.md` | 7 Findings (0C/0H/1M/6L) + AC-Coverage-Tabelle — Spec-Konformitaet Lens |
| **Review-Brief** | `docs/reviews/code/299-fabrication-mitigation-brief.md` | Topology + Risk Assessment + Requirements Map — Context |
| **Spec 299** | `docs/specs/299-fabrication-mitigation.md` | Spec ist SoT, Code folgt |

**Pflicht-Read-Reihenfolge:**
1. Verdict-File (§3 Konsolidierte Findings + §5 Fix-Scope)
2. Bei Fragen zu konkreten Findings: jeweiligen Reviewer-File konsultieren via Tracking-Tabelle
3. Spec 299 als laufende Reference

---

## §2 Fix-Scope (NICHT-VERHANDELBAR)

Per User-Wahl **Option A (Full-Scope-Fix)** + Skill code_review_board §5:
ALLE 26 konsolidierte Findings fixen, plus Spec-Amendments dokumentieren wo
Code-Fix semantische Aenderung verlangt.

### §2.1 Top-3 (CRITICAL + HIGH-Cluster, Buddy-Highlight)

**CC-001 [CRITICAL] Per-Finding Parser-Bug — Dogfooding-Win:**
Per-Finding-Parser matched `- evidence:` Bullet-List-Item NICHT (matched
nur `evidence:` als Block-Header). Convergenz F-CR-002 + F-CA-001. Live-
reproduziert. Konsequenz: per_finding-Defense fuer Reviewer-Outputs
strukturell unwirksam.

**Fix-Hinweis (Buddy):** Parser-Regex muss optional `- ` Prefix matchen.
Plus: alle 3 Reviewer-Protokolle (`spec/code/ux-reviewer-protocol.md`)
auf eindeutige Form pruefen — wenn Spec sagt `- evidence:` Bullet, dann
muss Parser das matchen. Wenn beides erlaubt sein soll, beides matchen.

**CC-002 [CRITICAL] Validator repo_root falsch:**
`validate_evidence_pointers.py` CLI default `repo_root = p.parent.resolve()`
macht Pre-commit Check 13 + CC-Hook strukturell falsch — pointer mit
repo-relativem path resolved in `<repo>/docs/reviews/<dir>/scripts/...`.
~100% false-positive-Rate, Promotion zu BLOCK strukturell unerreichbar.

**Fix-Hinweis (Buddy):** Default-`repo_root` muss git-root via
`git rev-parse --show-toplevel` oder upward-search nach `.git`/`pyproject.toml`
sein. Plus: CLI-Argument `--repo-root` Override-Option fuer Tests.

**CC-005 [HIGH] Pre-commit Filter Coverage-Gap:**
Filter excludiert `docs/reviews/code/`. Self-defeating Coverage — der
dogfooded Live-Test ist genau im uncovered Pfad.

**Fix-Hinweis (Buddy):** Pre-commit Check 13 Filter-grep-Pattern erweitern
um `docs/reviews/code/`. Plus: pruefen ob noch andere `docs/reviews/*/`
Pfade fehlen (architecture, sectional, amendment).

### §2.2 Restliche 23 Cluster

Aus Verdict-File §3 lesen, alle adressieren. Severity-Reihenfolge:
1. 2 CRITICAL (CC-001, CC-002) → erst, weil andere Findings darauf
   aufbauen koennen
2. 3 HIGH → naechste
3. 9 MEDIUM → dritte
4. 12 LOW → vierte

**Cherry-Pick verboten** per Skill §5. MEDIUM/LOW sind Follow-Up-Schulden,
kein Free-Pass.

### §2.3 Spec-Amendments durch Fixes (per spec-co-evolve Pattern)

Wenn ein Code-Fix Spec-semantische Aenderung verlangt:
1. Spec 299 in same block-commit anpassen
2. Spec-Aenderung im Commit-Body als `SPEC: <section>` Marker erwaehnen
3. spec-amendment-verification (Step 15) wird das im naechsten Pass-Cycle
   verifizieren

Voraussichtlich Spec-Amendment-relevant:
- CC-005 / CC-006 / CC-013 / CC-014 / CC-022 / CC-026 (per Chief-Verdict-Hinweis)

Per Verdict-File §3 lesen welche genau.

---

## §3 Implicit-Decisions-Surfaced (Pflicht-Section per Brief-Quality-Gate)

### §3.1 schema_shape

- locked: yes-§spec
- value: Pointer-Schema bleibt §1.2 (4 kinds, Quote-Cap, Schema-Version 1).
  Bei CC-001-Fix moeglicherweise Schema-Doku §1.5 erweitern um
  Layout-Detection-Detail (`- evidence:` Bullet vs `evidence:` Block).
  Spec-Amendment in same commit wenn ja.

### §3.2 error_handling

- locked: yes-§spec
- value: CLI-Exit-Codes 0/1/2 unveraendert. Bei CC-002-Fix:
  `repo_root`-Resolution-Fail (kein git-root, kein pyproject.toml) →
  exit 2 (parse-error-Klasse) + clear Fehlermeldung statt silent-falsch.

### §3.3 layer_discipline

- locked: yes-§spec
- value: Per Spec §6.5 Re-Use-Pfade — Library-Import bevorzugt fuer Speed,
  Subprocess als Fallback. CC-002-Fix darf NICHT Library/CLI-Trennung
  brechen — beide Konsumenten (Engine via Import, Hook + Pre-commit via
  CLI) muessen kompatibel bleiben.

### §3.4 naming_collisions

- locked: yes-§spec
- value: Keine neuen Symbole. Bei CC-005-Fix: Pre-commit Filter-Pfad-Liste
  erweitert, kein neues Symbol.

### §3.5 return_format_spec

- locked: derivable
- value: RETURN-SUMMARY pro Phase (siehe §6) mit:
  - Phase + Status (`done` | `blocked` | `partial`)
  - Findings-Adressiert (Liste mit Cluster-ID + Status)
  - Files-changed (mit Pfad + Op)
  - Test-Status-Diff (alle 83 noch GREEN? Welche neuen?)
  - Spec-Amendments (Liste mit Section + Begruendung)
  - L0-Status post-Fix (ruff + mypy)
  - Stop-Reason wenn nicht alle 26 fixbar

### §3.6 stop_conditions

- locked: yes-§adversary
- value: STOP + escalate wenn:
  - **CC-001 Fix bricht existing per_finding-Tests** → STOP, Parser-Aenderung
    diagnostizieren bevor weiter
  - **CC-002 Fix bricht repo_root-Resolution in CI/external-Setup** → STOP,
    Default-Logik nochmal entscheiden
  - **L0 nach Fix produziert >5 neue ruff/mypy Errors** → STOP, refactor
  - **Test-Regression: vorher GREEN-Tests werden RED** → STOP sofort,
    Fix-Pfad re-evaluieren
  - **Spec-Amendment widerspricht §11.2 Pass-2 Resolution** → STOP, User-
    Decision noetig
  - **Findings-Cluster-Adressierung > 80% MCA-Effort und nur ~50% adressiert
    nach Token-Budget-Limit** → STOP, partial RETURN-SUMMARY mit Verlust-
    Liste, User-Decision ueber Pass-2-Scope

---

## §4 Doku-Update-Pflicht (User-Add zu Fix-Scope)

**Per User-Anweisung 2026-05-05:** zusaetzlich zur Code-Fix:

### §4.1 Discovery-Eintrag (NEW)

`docs/discoveries/2026-05-05-dogfooding-self-detection-299.md`:

Inhalt: 2 CRITICAL Findings aus Pass 1 betreffen das Pointer-System selbst —
Parser-Bug + Validator-Default-Logik. Beide live-reproduzierbar via
`python3 scripts/validate_evidence_pointers.py <reviewer-file>`.

Kernaussage: Dogfooding bei selbst-verifizierendem System ist Pflicht-Test,
nicht kosmetisch. Schema-Conformance allein faengt das nicht — Source-
Grounding mit Pointer-Mechanik schon.

Format: per `docs/discoveries/README.md`-Konvention pruefen + folgen.

### §4.2 Build-State-File Update

`docs/build/2026-05-04-task-299-fabrication-mitigation.md` updaten mit:
- Pass 1 FAIL Eintrag (Datum, Reviewer-Liste, Verdict, Cluster-Counts)
- Fix-Cycle Status (in_progress, MCA-Run, Files-changed)
- Pass 2 placeholder
- Lesson: Dogfooding-Self-Detection-Pattern

### §4.3 Spec 299 Updates wo noetig

Per §2.3: Code-Fix-induzierte Spec-Amendments im selben Block-Commit.
Beispiele moeglich:
- §1.5 Layout-Detection-Detail (CC-001-Fix)
- §6.1 CLI-Interface `--repo-root` Override-Option (CC-002-Fix)
- §5 Filter-Liste-Erweiterung (CC-005-Fix)

Konkret pruefen pro Fix.

### §4.4 KEINE eigenstaendigen Architektur-Doku-Updates jetzt

Per User-Constraint Build 299 L2 (OSS-readable): keine BuddyAI/Repo-
spezifische Forensik in Skills, keine Session-Refs in Capability-Files.
Dogfooding-Discovery ist OK weil sie generisches Pattern dokumentiert,
nicht eine Session.

`architecture-documentation/`-Updates erst nach Pass-2 PASS und
Knowledge-Processor-Run (Step 19).

---

## §5 L0-Pflicht nach Fix

```bash
# Vor Re-Review-Dispatch
ruff check scripts/ orchestrators/claude-code/hooks/
mypy scripts/

# Erwartung: 0 Errors (1 pre-existing F401 in workflow_engine.py:40 ist OK)

# Plus Test-Regression-Check
pytest tests/fabrication_mitigation/ -v 2>&1 | tail -50
# Erwartung: 83 PASS + 2 SKIP, keine neuen FAIL

# Plus Engine-Validierung (workflows.yaml-Schema-Check)
python3 scripts/workflow_engine.py --validate
# Erwartung: PASS: All workflows valid.

# Plus Validator-Self-Test mit aktuellem Reviewer-Output (Dogfooding!)
python3 scripts/validate_evidence_pointers.py docs/reviews/code/299-fabrication-mitigation-code-review.md
# Erwartung post-CC-001-Fix: exit 0 (oder dokumentierte Begruendung)
```

---

## §6 RETURN-SUMMARY-Format (Pflicht pro Fix-Phase-Boundary)

Nach jedem substantiellen Fix-Block (z.B. nach CRITICAL-Cluster, nach HIGH-
Cluster, etc.):

```markdown
## RETURN-SUMMARY — Fix-Block <N> (<scope>)

**Phase-Status:** done | blocked | partial

**Findings-Adressiert:**
| Cluster | Status | Files-Touched |
|---|---|---|
| CC-001 | FIXED | scripts/validate_evidence_pointers.py:NN-NN |
| ... | ... | ... |

**Files-Changed:**
- created: <pfad>
- edited: <pfad>
- deleted: <pfad>

**Spec-Amendments:** (wenn welche)
- §X.Y: <was geaendert + warum>

**L0-Status:** PASS (ruff + mypy clean) | FAIL (Liste der Errors)

**Test-Status:** 83 PASS + 2 SKIP unveraendert | Regression: <Liste der RED-Tests>

**Stop-Reason:** (wenn partial/blocked)

**Naechster-Schritt-Empfehlung:** Fix-Block <N+1> (<scope>) | L0-Re-Run | User-Konsultation
```

Final RETURN-SUMMARY nach allen 26 Cluster:
- alle 4 Severity-Level abgehakt
- Doku-Update §4 erfuellt
- L0 + Test-Regression clean
- bereit fuer Re-Review (Pass 2)

---

## §7 Stop-Conditions (re-iteration of §3.6 fuer Klarheit)

STOP + RETURN-SUMMARY mit `partial` wenn:
- Eine der Stop-Conditions §3.6 trifft
- Token-Budget vor 80% Cluster-Adressierung erschoepft → partial Liste
- 2+ aufeinander folgende Fix-Versuche an demselben Cluster scheitern
- Test-Regression > 5 neue RED-Tests
- Spec-Amendment-Konflikt mit existing §11.2 Resolution

Nicht STOP fuer:
- routine Findings-Fix
- Spec-Amendment im Same-Block-Commit (erlaubt + erwartet)
- L0 1-2 neue Errors (ruff/mypy fixable)

---

## §8 Cross-References

- Spec: `docs/specs/299-fabrication-mitigation.md`
- Pass 1 Verdict (Authority): `docs/reviews/code/299-fabrication-mitigation-verdict.md`
- 3 Pass 1 Reviewer-Files: `docs/reviews/code/299-fabrication-mitigation-{code-review,code-adversary,code-spec-fit}.md`
- Pass 1 Brief: `docs/reviews/code/299-fabrication-mitigation-brief.md`
- Build-State: `docs/build/2026-05-04-task-299-fabrication-mitigation.md`
- Original Delegation: `docs/tasks/299-delegation.md`
- Test-Plan v1: `docs/tasks/299-test-plan.md`
- Test-Plan v2 (Adversary): `docs/tasks/299-test-plan-adversary.md`
- Tests: `tests/fabrication_mitigation/`
- Discovery (zu schreiben): `docs/discoveries/2026-05-05-dogfooding-self-detection-299.md`
- Discoveries-README (Format): `docs/discoveries/README.md`
- Skill code_review_board (Fix-Scope-Regel): `skills/code_review_board/SKILL.md` §5
