---
task_id: 299
spec: docs/specs/299-fabrication-mitigation.md
spec_version: v1
test_plan_v1_ref: docs/tasks/299-test-plan.md
test_plan_v1_tc_count: 62
adversary_pass: 1
adversary_persona: code-adversary
created: 2026-05-04
status: active
adv_tc_count: 18
mode: design-extend
---

# Test-Plan Adversary-Extension — Task 299 Fabrication-Mitigation

Erweiterung von `docs/tasks/299-test-plan.md` (v1, 62 TCs).

**Cross-Reference-Pflicht:** jedes ADV-TC referenziert (a) den v1-TC den es
NICHT abdeckt (oder explizit `v1_gap: ja`) und (b) das Spec-Section/Engine-Code-
Lokus mit `evidence:`-Pointer (Schema dogfooded).

**Source-Grounding-Disziplin:** alle File-Lines verifiziert via Read-Tool.
Engine-Lokus `workflow_engine.py:121, 264, 343-449`, `yaml_loader.py:59-62, 73-109`.
Spec-Lokus per `docs/specs/299-fabrication-mitigation.md`. Keine erfundenen
Linecounts oder Variablen.

---

## Reviewer-Reasoning-Trace

- **Intent:** v1 (62 TCs) deckt 9/9 ACs + 6/6 Eval + 10/10 1st-Order-Adversary-
  Targets ab. Diese Extension haertet 2nd-Order: Stellen wo v1-Coverage
  *aussieht* wie Coverage, aber Implementer-Bias systematisch durchschluepfen
  laesst (NEW-V-001-Replikation, Compensation, Cycle, Smart-but-Wrong).
  Adversary-Coverage-Ziel: Test-Plan ist *nicht* tester-Spec-Derivativ-only —
  Tests beweisen Verhalten das in der Spec *nicht steht* aber zwingend
  richtig sein muss.
- **Plan:** (1) Engine-Code real lesen statt Spec-Behauptungen vertrauen,
  Drift Spec↔Code finden. (2) Quote-Cap-Bypass per UTF-8/Whitespace
  konstruieren. (3) Path-Boundary-Mechanik durchspielen ohne `..` (Symlink,
  Absolute-Path, NUL-Byte). (4) Race-Window zwischen `pointer_check` und
  `manual` aus Filesystem-Sicht (truncate-during-read, append-after-validate).
  (5) Fix-Pass-Cumulative-Force-Counter auseinanderhebeln (Workflow-Restart-
  Reset, Multi-Workflow). (6) Triple-Check-Reihenfolge (pre-commit + CC-Hook
  + Engine — was gewinnt bei Konflikt?). (7) Skill-Frontmatter-Mutation nach
  pointer_check-Time. Reihenfolge: Engine → Validator → Cross-Layer →
  Smart-but-Wrong-v1-Stichproben.
- **Simulate:** Konkretes Szenario fuer NEW-V-001-Replikation:
  Reviewer schreibt Output mit `evidence:` Pointer der `quote: "X"` mit
  Zero-Width-Joiner U+200D zwischen "X" und " — Source" claimt. `grep -F`
  matched literal-Bytes. Reviewer sieht Quote im Editor visuell als "X — Source"
  (200 visible chars), aber Bytes sind 240+ — Cap-Check `len(quote) <= 200`
  failed. ABER: wenn Cap-Check nur `quote.count('\n') <= 3 and len(quote) <= 200`
  zaehlt Bytes/Codepoints? Spec §1.3 sagt "200 Zeichen" — nicht spezifiziert
  ob Codepoints oder Bytes oder Grapheme-Cluster. Implementer waehlt
  `len(quote)` (Python = Codepoints). 200 Codepoints UTF-8 koennten 600 Bytes
  sein. v1 TC-016/017/054 testen *Verletzung* aber NICHT *Codepoint-vs-Byte-
  vs-Grapheme-Wahl*. Smart-but-Wrong: Cap passt aber semantisch ist Quote
  unangemessen lang.
- **Impact:** Wenn Adversary-TCs nicht greifen: Spec 299 Phase-1 ist
  "implementiert + alle v1-Tests gruen" — aber 4-Wochen-Bewaehrung-Pfad
  (§5: pre-commit WARN→BLOCK Promotion) wird auf falscher Datenbasis
  beurteilt. Promotion zu BLOCK bei 5% False-Positive-Rate basiert auf
  Tests die FP nicht aufdecken (Codepoint-vs-Byte-Drift, Symlink-Bypass,
  Race-Window-Mid-Validate). Resultat: BLOCK-Promotion in Welle 2 mit
  weiterhin offenen Bypass-Pfaden — Vertrauen in Mechanik ohne mechanisches
  Greifen.

  **SIMULATE-Bezug zu ADV-TC-008**: das Codepoint-vs-Byte-Szenario manifestiert
  sich genau in jenem Test.

---

## Reviewer-First-Principles-Drill

- **Annahme (zentral, angreifbar):** v1-Test-Plan deckt durch 10/10
  Adversary-Targets-Coverage die Adversary-Achse vollstaendig ab — Adversary-
  Pass ist redundant. (So formuliert vom v1-Author in Z.1633:
  "10/10 Adversary-Targets abgedeckt".)
- **Gegenfrage:** Welche Adversary-Pattern sind NICHT in der 10er-Liste,
  aber in der Spec mechanisch produzierbar? Genau: (1) Spec-Drift —
  Spec §2.1 Z.168 sagt `_has_unresolved_vars` braucht `source_file`-Whitelist,
  Engine `check_completion` Z.350 iteriert nur ueber `("path", "command",
  "pattern")` — `source_file` fehlt. v1 TC-022 *behauptet* das wird
  gefixt, *prueft* aber nicht den graceful-Degradation-Pfad fuer
  `source_file` selbst (nur fuer existing Felder). (2) Fix-Pass-Re-Run
  Force-Counter-State-Carryover. (3) `evidence_layout` Skill-Frontmatter-
  Mutation BETWEEN `--start` und `--complete`-Time (state-snapshot-vs-
  read-time-Drift). Kein einziger v1-TC.
- **1st-Principle-Ebene:** Klasse "Spec-sagt-X-Engine-tut-Y-implizit-Tests-
  pruefen-X-statt-Y" — generischer als Spec 299. Zweite Instanz ausserhalb
  299: jeder workflow-config-Edit der eine neue Variable einfuehrt, deren
  Whitelist-Pfad (Engine-side) nicht gleichzeitig erweitert wird, hat genau
  diese Drift-Form. Test fuer Klasse: nicht "passt Spec-Text", sondern
  "Engine-Code-Pfad behandelt diese Variable graceful". v1-Authors haben
  Spec gelesen + Tests aus Spec abgeleitet — Engine nicht parallel gelesen.

  **DRILL-Bezug zu ADV-TC-001**: Annahme "Whitelist-Erweiterung reicht"
  manifestiert sich in jenem Test als BLOCK.

---

## Coverage-Rationale

```yaml
adversary_coverage:
  patterns_covered:
    NEW-V-001:           4   # ADV-TC-001, ADV-TC-002, ADV-TC-006, ADV-TC-018
    Compensation-Bug:    2   # ADV-TC-007, ADV-TC-013
    Cycle-Entry-Point:   1   # ADV-TC-009
    Cleanup-Tx-Silent-Ack: 2 # ADV-TC-010, ADV-TC-014
    Smart-but-Wrong:     4   # ADV-TC-008, ADV-TC-011, ADV-TC-016, ADV-TC-017
    Stale-State:         2   # ADV-TC-003, ADV-TC-015
    Race-Condition:      2   # ADV-TC-004, ADV-TC-005
    Force-Bypass-Drift:  2   # ADV-TC-012, ADV-TC-013
    Path-Traversal:      1   # ADV-TC-005 (symlink-Variant)
    Quote-Cap-Bypass:    2   # ADV-TC-008, ADV-TC-016

  spec_assumption_diff:
    - "Spec §1.3 'Quote <=200 Zeichen' — Codepoint-vs-Byte-vs-Grapheme nicht entschieden (ADV-TC-008, ADV-TC-016)"
    - "Spec §1.3 'path repo-relativ' — Symlink-Aufloesung nicht spezifiziert (ADV-TC-005)"
    - "Spec §2.1 Schritt 5 'Match-Failure → return False' — was bei IO-Error/Permission-Denied/EOF-mid-read? (ADV-TC-004)"
    - "Spec §2.3 MAX_FORCE=2 'pro workflow' — was nach archive_state+restart? (ADV-TC-012)"
    - "Spec §1.5 evidence_layout per Skill-Frontmatter — Mutations-Zeitpunkt undefiniert (ADV-TC-003)"
    - "Spec §5 pre-commit WARN-only initial — was bei multi-staged-File mit MIX (legacy+v1)? (ADV-TC-014)"
    - "Spec §3.2 consistency_check Tier-1-Drift — prueft 'mindestens ein Step', aber NICHT ob compound-Reihenfolge eingehalten ist (ADV-TC-018)"
    - "Spec §4.1 PostToolUse-Hook 'liest Output-File per Pattern-Inferenz' — was wenn 2 parallele Sub-Agent-Tasks gleichen Pfad liefern? (ADV-TC-006)"

  implementer_blindspots:
    - "Engine-Code-Drift: Implementer liest Spec, schreibt pointer_check-Branch, vergisst _has_unresolved_vars-Loop in Z.350-373 um source_file zu erweitern (ADV-TC-001). v1 TC-022 prueft Whitelist, nicht Loop."
    - "Codepoint-vs-Byte-Mismatch: Implementer waehlt Python len() ohne grapheme-segmentation; UTF-8-tricks (Combining Marks, Zero-Width-Joiner) bleiben unter 200 char-count (ADV-TC-008)."
    - "Symlink/Absolute-Path-Bypass: Implementer addt '../' check, vergisst symlink-resolve und absolute-path-Block (ADV-TC-005)."
    - "Force-Counter-Reset-by-Restart: Implementer increment/check in run-loop, ohne workflow_id-stable-Persistenz nach archive (ADV-TC-012)."
    - "Compound-Order-Reverse: Spec sagt pointer_check VOR manual, aber yaml_loader.py:107 _validate_completion macht keinen Order-Check (ADV-TC-007). Tester verlaesst sich auf disziplinarisches workflow.yaml-Edit."
    - "Skill-Frontmatter-Mutation-Mid-Run: pointer_check liest evidence_layout zum Check-Zeitpunkt aus Skill-File. Wenn zwischen Step-Start und Check der Skill editiert wird, drifted die Validierung (ADV-TC-003)."
    - "evidence: [] vs evidence: ~ vs evidence: missing — drei verschiedene YAML-Repraesentationen, F-C-002-Fix faengt nur 'leere Liste' (ADV-TC-002)."
    - "kind: file_exists nicht-trivial-Discipline ist Schema-Doku-Note. Engine prueft NICHT 'min 1 non-trivial Pointer pro Finding' (ADV-TC-011)."
    - "compound check[1] is manual: User koennte File NACH pointer_check loeschen + manual-complete macht weiter (ADV-TC-004 — TOCTOU)."
    - "v1 TC-019 Stale-State-Adversary akzeptiert dass schema_version: 0 fabricated quotes nicht prueft. Aber: was wenn legacy-File mid-Run schema_version: 0 → 1 wechselt? Cache? Re-Read? (ADV-TC-015)."
```

---

## ADV-TC-Tabelle

### ADV-TC-001 — Engine-Drift: source_file im _has_unresolved_vars-Graceful-Loop fehlt

- **Pattern:** NEW-V-001 (Spec-says-X, Engine-checks-Y)
- **Phase:** C2 (workflow_engine.py)
- **Level:** L2
- **v1-Gap:** TC-022 prueft `_has_unresolved_vars` Whitelist-Erweiterung,
  ABER NICHT den `check_completion`-Loop Z.350-373 der nur ueber
  `("path", "command", "pattern")` iteriert. `source_file` ist NICHT in
  diesem Tuple — Implementer addet pointer_check-Branch + vergisst diesen
  Loop zu erweitern. Resultat: unresolved `{spec_name}` in `source_file`
  produziert IO-Error statt graceful-degrade-zu-manual.
- **Eingabe:**
  ```python
  comp = {"type": "pointer_check",
          "source_file": "docs/reviews/board/{spec_name}-consolidated-pass1.md"}
  state = {"variables": {}}  # spec_name absichtlich NICHT gesetzt
  step_state = {}
  ok, msg = check_completion(comp, state, step_state)
  ```
- **Erwartung:** `ok is True` UND `"manual" in msg` UND `"unresolved" in msg`
  (per existing Z.355-361 Pattern). Aktuell (ohne Fix): IO-Error oder
  False-Block.
- **Mechanik:** Implementer muss Z.350 Tuple `("path", "command", "pattern",
  "source_file")` erweitern ODER pointer_check-spezifischen Pre-Check addieren.
- **Adversary-Begruendung:** v1 TC-022 zitiert Spec §2.1 Z.168 ("`_has_unresolved_vars`
  Erweiterung"), nimmt aber an dass Whitelist + Variable-Discovery genug ist.
  Engine-Code-Pfad ist ein zweiter Ort (Z.350-373) den Spec-Text nicht
  erwaehnt — klassischer NEW-V-001.
- **evidence:**
  ```yaml
  - kind: file_range
    path: scripts/workflow_engine.py
    lines: 350-352
    quote: "for field in (\"path\", \"command\", \"pattern\"):"
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 168-171
    quote: "_has_unresolved_vars` (workflow_engine.py:264)"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 628-657
    quote: "TC-022: _has_unresolved_vars Whitelist enthaelt spec_name"
  ```

### ADV-TC-002 — evidence: ~  (YAML null) wird nicht als "empty" erkannt

- **Pattern:** NEW-V-001 (3 YAML-Repraesentationen, Fix faengt nur 1)
- **Phase:** C2 / C3
- **Level:** L2
- **v1-Gap:** TC-018 testet `evidence: []` (leere Liste). Spec §2.1 Schritt 4
  sagt "empty/missing evidence → fail". 3 YAML-Formen kollabieren zu 'empty':
  `evidence: []`, `evidence: ~` (null), `evidence:` (no value). v1 deckt nur
  Form 1.
- **Eingabe:** drei Source-Files, je `schema_version: 1` plus:
  - File A: `evidence: []`
  - File B: `evidence: ~`
  - File C: `evidence:` (gefolgt von Leerzeile / EOF)
- **Erwartung:** alle 3 → `ok is False` UND msg `"non-empty evidence required"`.
- **Mechanik:** Validator-Empty-Check muss `if not pointers` (Python falsy:
  `[]`, `None`, `""`) verwenden, nicht `if pointers == []`.
- **Adversary-Begruendung:** Implementer schreibt `if pointers == []: return False`
  weil Spec-Text "leeres evidence" sagt. YAML-Parser gibt fuer `evidence: ~`
  `None`, fuer `evidence:` ohne Value ebenfalls `None`. Beide schluepfen durch
  `== []`-Check (Smart-but-Wrong-Variant: Test mit Form 1 grun, Form 2+3 silent
  produzieren `False`-positiv "evidence vorhanden" weil `pointers is None`
  nicht in Pointer-Loop iteriert wird → Engine returnt `True` weil Loop leer
  ist).
- **evidence:**
  ```yaml
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 162-162
    quote: "schema_version: 1 + empty/missing evidence → return (False"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 532-550
    quote: "TC-018: pointer_check schema_version: 1 + leeres evidence: [] → block"
  ```

### ADV-TC-003 — Skill-Frontmatter `evidence_layout` Mutation zwischen Step-Start und Check

- **Pattern:** Stale-State (Cache-vs-Read-Time-Drift)
- **Phase:** C2
- **Level:** L3
- **v1-Gap:** TC-020 testet `evidence_layout`-Lookup zum Check-Zeitpunkt.
  Aber: Wenn Skill-File zwischen `--start` (Workflow-State persistiert
  workflow-snapshot) und `--complete` editiert wird (Layout flippt von
  `per_finding` zu `top_level`), liest Engine zur Check-Zeit die NEUE Version,
  Reviewer hat aber nach ALTER Version geschrieben. Mismatch → silent skip
  ODER false-block.
- **Eingabe:**
  1. Skill-File hat `evidence_layout: per_finding`
  2. Reviewer-Output mit per-Finding-evidence-Bloecken erstellt
  3. `--start board`
  4. Skill-File editiert: `evidence_layout: top_level`
  5. `--complete board`
- **Erwartung:** EITHER Engine cached Skill-Frontmatter zur `--start`-Zeit
  und nutzt `per_finding` (deterministisch), OR Engine erkennt Mismatch und
  blockiert mit klarem Error `"layout mutation between start and complete
  detected"`. NICHT: silent-skip oder confused-pass.
- **Mechanik:** Spec §1.5 + §2.1 Schritt 2 sagt "selected per Skill-Frontmatter
  evidence_layout". Aber: wann wird gelesen? Spec offen. Default-Implementer-
  Wahl: zur Check-Zeit. Folge: Mutation-Window oeffnet Drift-Pfad.
- **Adversary-Begruendung:** Implementer faengt das nie weil v1 TC-020
  Skill-File als statisch annimmt. Setup mit "Foo-SKILL.md hat Frontmatter
  evidence_layout: top_level" (TC-020 Z.579) — aber File-Mutation ueber
  Step-Lifetime ist nicht modelliert.
- **evidence:**
  ```yaml
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 105-110
    quote: "evidence_layout: per_finding | top_level"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 574-598
    quote: "TC-020: pointer_check liest evidence_layout aus Skill-Frontmatter"
  ```

### ADV-TC-004 — TOCTOU: pointer_check pass, dann File-Truncate vor manual-complete

- **Pattern:** Race-Condition (Time-of-Check-vs-Time-of-Use)
- **Phase:** C2 / D
- **Level:** L3
- **v1-Gap:** TC-024 prueft `pointer_check` VOR `manual` als Race-Mitigation
  fuer fehlende Files. Aber: was nach pointer_check pass + File-Mutation
  vor manual-complete? `compound`-Loop iteriert in Engine Z.439-447 ohne
  File-Lock — File koennte zwischen Sub-Check-Iterationen geleert werden.
- **Eingabe:**
  1. compound: [pointer_check (source_file=X), manual]
  2. File X existiert mit valid evidence zum pointer_check-Zeitpunkt
  3. Zwischen check[0] (pointer_check) und check[1] (manual) → File X
     truncate auf 0 Bytes (Reviewer overwrite)
  4. check[1] (manual) returnt True per Spec
  5. Step → complete
- **Erwartung:** EITHER pointer_check-Re-Validation am Step-Boundary
  (paranoid-mode), OR File-Lock fuer step-Lifetime, OR explizite Spec-Decision
  "TOCTOU akzeptiert" mit Test der das *dokumentiert*. NICHT: silent-pass
  ohne Annotation.
- **Mechanik:** Engine `compound`-Loop (Z.439-447) macht keine atomare
  Snapshot. File-System ist Race-Surface.
- **Adversary-Begruendung:** TC-024 prueft den OPPOSITE-Case (file-not-yet-
  exists zur pointer_check-Time). Mid-execution-Mutation ist die zweite
  Race-Half und nicht abgedeckt. Cleanup-Tx-Silent-Ack-Klasse: pointer_check
  hat "geacked" dass evidence valid war, aber State danach geaendert.
- **evidence:**
  ```yaml
  - kind: file_range
    path: scripts/workflow_engine.py
    lines: 439-447
    quote: "if ctype == \"compound\":"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 688-723
    quote: "TC-024: completion.compound mit pointer_check VOR manual"
  ```

### ADV-TC-005 — Symlink-Bypass: path zeigt auf Symlink ausserhalb Repo

- **Pattern:** Path-Traversal (zweite Form, jenseits `..`)
- **Phase:** C3 (Validator)
- **Level:** L5
- **v1-Gap:** TC-053 testet `path: "../../etc/passwd"` (literal `..`).
  Engine `PROJECT_ROOT = Path.cwd().resolve()` (Z.89), aber `abs_path =
  PROJECT_ROOT / target_path` (Z.380) — folgt Symlinks ohne Boundary-Check.
  `path: "evil-link"` wo `evil-link` Symlink auf `/etc/passwd` ist:
  `(PROJECT_ROOT / "evil-link").resolve()` zeigt nach `/etc/passwd`.
- **Eingabe:**
  1. `ln -s /etc/passwd tests/fixtures/299/evil-link`
  2. Pointer mit `path: tests/fixtures/299/evil-link`, `kind: file_exists`
  3. Validator-Aufruf
- **Erwartung:** exit 1 mit Reason `"path resolves outside repo"`. Mechanik:
  `(PROJECT_ROOT / target_path).resolve().is_relative_to(PROJECT_ROOT)`
  muss `True` returnen.
- **Mechanik:** Resolved-Path-Boundary-Check zusaetzlich zum String-Level-
  Check. v1 TC-053 prueft nur String-Level (`"../../"`).
- **Adversary-Begruendung:** Spec §1.3 sagt "repo-relativ" als Format-Constraint
  (String). Resolution-Time-Check (gegen real-resolved-Path) ist eine zweite
  Schicht die der Implementer aus reinem String-Lesen der Spec NICHT ableitet.
- **evidence:**
  ```yaml
  - kind: file_range
    path: scripts/workflow_engine.py
    lines: 89-91
    quote: "PROJECT_ROOT = Path(os.environ.get(\"BUDDY_PROJECT_ROOT\""
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 75-76
    quote: "Path-Format:** repo-relativ, ohne `./`-Prefix"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 1358-1377
    quote: "TC-053: Path-Traversal-Adversary path:"
  ```

### ADV-TC-006 — Hook-Race: zwei parallele Tier-1-Sub-Agent-Tasks, gleiche Output-Pfad-Inferenz

- **Pattern:** NEW-V-001 (Hook-Mechanik in Spec §4.1 angedeutet, nicht spezifiziert)
- **Phase:** E
- **Level:** L4
- **v1-Gap:** TC-044 testet Hook-Filter auf Tier-1 vs Non-Tier-1. Spec §4.1
  Schritt 2 sagt "Liest Output-File (per Pattern-Inferenz aus Sub-Agent-Prompt,
  wie board-output-check.sh)". Wenn Buddy 2 Tier-1-Skills parallel spawnt
  (z.B. spec_board + adversary_test_plan via 2 Task-Calls in 1 Turn), Hook
  bekommt 2 PostToolUse-Events. Beide inferieren ggf. denselben Output-File-
  Pfad (Pattern-Hash-Kollision ueber Skill-Pfad)? ODER File von Run-1 wird
  validiert wenn PostToolUse Run-2 feuert (File-noch-nicht-da)?
- **Eingabe:** 2 parallele Tier-1-Tasks in 1 CC-Turn:
  - Task A: spec_board-Persona, Output `docs/reviews/board/X-pass1.md`
  - Task B: adversary_test_plan, Output `docs/tasks/Y-test-plan-adversary.md`
  Beide Files schreiben ueberlappend.
- **Erwartung:** Hook validiert Task-A-Output gegen Task-A-Pfad und
  Task-B-Output gegen Task-B-Pfad — KEINE Cross-Validation. Concurrency-
  safe (entweder Lock, Queue, oder pro-Task-isoliertes Pattern).
- **Mechanik:** Hook-Implementer (Phase E) muss Pattern-Inferenz pro
  Task-ID isolieren, nicht global Pfad-cachen.
- **Adversary-Begruendung:** v1 TC-042/043/044/045 testen sequentiell ein
  Hook-Trigger. Parallele Spawn-Mechanik (real Buddy-Pattern) bricht
  Isolation. Spec §4.1 ueberlaesst das "Phase-E-Decision" (F-I-016) — also
  Race-Pfad nicht modelliert.
- **evidence:**
  ```yaml
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 290-294
    quote: "PostToolUse-Trigger auf Tool=Task"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 1150-1169
    quote: "TC-044: Hook filtert auf Tier-1-Skill-Sub-Agent-Outputs"
  ```

### ADV-TC-007 — Compound-Order-Reverse: workflow.yaml mit manual VOR pointer_check, yaml_loader laesst durch

- **Pattern:** Compensation-Bug (Welle-N Fix in Spec, Welle-N+1 Fix waere
  in yaml_loader, nicht gemacht)
- **Phase:** C1
- **Level:** L2
- **v1-Gap:** TC-038 prueft dass Tier-1-Steps `completion.checks[0].type ==
  "pointer_check"` haben (Konvention). TC-024 prueft Engine-Verhalten bei
  korrekt-konfigurierter Reihenfolge. Aber: Spec §2.2 "Reihenfolge-Pflicht:
  pointer_check VOR manual" ist DISZIPLIN. yaml_loader.py:100-107
  `_validate_completion(compound)` iteriert ueber Sub-Checks, validiert
  jeden, aber prueft KEINE Reihenfolge-Constraint zwischen Sub-Check-Types.
  Implementer kann `[manual, pointer_check]` schreiben, Schema akzeptiert.
- **Eingabe:**
  ```yaml
  completion:
    type: compound
    checks:
      - type: manual
      - type: pointer_check
        source_file: "docs/foo.md"
  ```
- **Erwartung:** `_validate_completion` returnt Error
  `"compound: pointer_check must precede manual when both present"`.
- **Mechanik:** yaml_loader Schema-Layer muss Order-Constraint enforcen,
  nicht nur Workflow-Author-Disziplin.
- **Adversary-Begruendung:** Spec §2.2 sagt Reihenfolge ist Pflicht (Race-
  Mitigation). Aber Pflicht ist DISZIPLINARISCH (workflow.yaml-Author muss
  korrekt schreiben). v1 TC-024 testet "wenn korrekt geschrieben, dann
  funktioniert"; testet NICHT "wenn falsch geschrieben, blockt der Loader".
  Ohne Loader-Block: jeder neue Tier-1-Workflow-Step ist single-point-of-
  failure. Compensation-Bug-Klasse: Welle-N (Spec) sagt Reihenfolge-Pflicht,
  Welle-N+1 (yaml_loader) hat dieselbe Bug-Klasse "implizite Spec, kein
  Code-Enforcement".
- **evidence:**
  ```yaml
  - kind: file_range
    path: scripts/lib/yaml_loader.py
    lines: 100-107
    quote: "elif ctype == \"compound\":"
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 194-196
    quote: "Reihenfolge-Pflicht:** `pointer_check` VOR `manual`"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 1008-1031
    quote: "TC-038: 6 Tier-1-Workflow-Steps haben completion.compound"
  ```

### ADV-TC-008 — Quote-Cap: Codepoint-vs-Byte-vs-Grapheme-Cluster-Drift

- **Pattern:** Smart-but-Wrong (Cap-Check pass, Quote semantisch zu lang)
- **Phase:** C3 (Validator §6.4)
- **Level:** L2
- **v1-Gap:** TC-016 testet `>3 Zeilen`, TC-017 testet `>200 Zeichen`,
  TC-054 testet Boundary `3 Zeilen + 200 Zeichen → pass; +1 → block`. Alle
  drei messen mit `len(quote)`. Wenn `len()` Codepoints zaehlt (Python-Default)
  und Implementer-Tests nur ASCII verwenden, decken sie nicht ab: (a) Combining-
  Marks (1 Grapheme = N Codepoints), (b) UTF-8-Bytes (1 Codepoint = 1-4 Bytes),
  (c) Zero-Width-Joiner-Sequenzen (1 visible glyph = mehrere Codepoints).
- **Eingabe:** drei Quote-Variants:
  - Quote A: 200 Codepoints reine Combining-Marks (`"a" + "́" * 199`) —
    Codepoint-Count 200, Byte-Count ~400, visible-Length ~1 Grapheme
  - Quote B: 100 Emoji-Codepoints (`"\U0001F600" * 100`) — Codepoint-Count
    100, Byte-Count 400
  - Quote C: 200 Codepoints mit Zero-Width-Joiner zwischen jedem Char
- **Erwartung:** Spec entscheidet *eine* Metrik UND `quote_length_cap_ok()`
  enforced sie konsistent. Test asserts: gewaehlte-Metrik dokumentiert
  (Spec-Amendment ODER Validator-Docstring), und Test deckt alle drei
  Variants gegen *gewaehlte* Metrik ab.
- **Mechanik:** Wahl `len(quote)` vs `len(quote.encode("utf-8"))` vs
  `grapheme.length(quote)`. Default-Implementer waehlt `len()` ohne Spec-
  Lesen.
- **Adversary-Begruendung:** v1 implizit ASCII-only. Spec §1.3 "200 Zeichen"
  ist Sprache-Drift (Deutsch "Zeichen" = Codepoint? Grapheme? Byte?). Bypass-
  Vector: 200-Codepoint Combining-Mark-Quote = visuell ueber-eine-Buchstaben-
  Glyphe — Cap formal-pass, semantisch absurd.
- **evidence:**
  ```yaml
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 71-73
    quote: "<= 3 Zeilen UND <= 200 Zeichen"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 514-530
    quote: "TC-017: pointer_check Quote-Cap-Verletzung (>200 Zeichen)"
  ```

### ADV-TC-009 — Cycle-Entry-Point: source_file referenziert sich selbst via Variable-Substitution

- **Pattern:** Cycle-Entry-Point
- **Phase:** C2
- **Level:** L2
- **v1-Gap:** TC-022 erwaehnt "selbst-referent → graceful degradation, keine
  InfiniteLoop" als 1-zeilige Adversary-Note. Aber: konkrete Cycle-Konstruktion
  ist `source_file: "{source_file_var}"` mit `state["variables"]["source_file_var"]
  = "{source_file_var}"` — `_resolve_vars` (Z.255-261) macht *single-pass*
  Substitution, returnt `"{source_file_var}"` literal. v1 testet das nicht
  als echten Cycle.
- **Eingabe:**
  ```python
  comp = {"type": "pointer_check", "source_file": "{a}"}
  state = {"variables": {"a": "{b}", "b": "{a}"}}
  ok, msg = check_completion(comp, state, step_state)
  ```
- **Erwartung:** Single-Pass-Resolution (Z.261) returnt `"{b}"` ODER `"{a}"`
  je nach Resolution-Order. `_has_unresolved_vars` faengt das (returnt
  `["b"]` oder `["a"]`). graceful → manual.
- **Mechanik:** Engine macht KEINE multi-pass-Resolution (gut — kein Infinite-
  Loop). Aber: Test asserts dass `_resolve_vars` *nicht* rekursiv expandiert
  und `_has_unresolved_vars` das Resultat catched.
- **Adversary-Begruendung:** v1 TC-022 hat Adversary-Note "selbst-referent",
  aber konstruiert keinen 2-Variable-Cycle. 1-Variable-Self-Ref ist trivial,
  2-Variable-Cycle ist die echte Failure-Mode.
- **evidence:**
  ```yaml
  - kind: file_range
    path: scripts/workflow_engine.py
    lines: 255-261
    quote: "def _resolve_vars(text: str, variables: dict[str, Any])"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 643-645
    quote: "Cycle-Adversary:** `source_file: \"{source_file}\"`"
  ```

### ADV-TC-010 — Cleanup-Tx-Silent-Ack: Force-Bypass-Counter-Reset durch archive_state+Restart

- **Pattern:** Cleanup-Tx-Silent-Ack
- **Phase:** C2 / E2E
- **Level:** L4
- **v1-Gap:** TC-023 testet MAX_FORCE_PER_WORKFLOW=2 in *einem* Workflow-Run.
  Engine `archive_state(workflow_id)` (Z.242-248) `os.replace` State-File.
  Wenn User Workflow nach 2 Forces archiviert + neu startet (gleiche
  Task-ID) → frischer State-File → force_count=0. v1 testet das NICHT.
- **Eingabe:**
  1. `--start build --task 299` → workflow_id W1
  2. `--complete step --force` x2 (counter=2, MAX erreicht)
  3. `--archive` (oder Workflow-finish)
  4. `--start build --task 299` → workflow_id W2 (neu)
  5. `--complete step --force` (counter=1, accepted)
- **Erwartung:** EITHER force-counter persistent per-task (nicht per-workflow-
  instance), OR Spec dokumentiert "per-workflow-instance, restart erlaubt
  reset" als Feature mit explizitem Test. Aktuell: silent-ack of reset.
- **Mechanik:** Spec §2.3 "MAX_FORCE_PER_WORKFLOW" — semantisch unklar:
  per-workflow-Definition (build) oder per-workflow-Instance (build-Run-N)?
- **Adversary-Begruendung:** v1 nimmt "pro workflow" als per-Run an. Cleanup-
  Tx-Pattern: archive ist die Cleanup-Tx, frischer Start ack't fabrication-
  bypass-history nicht. Reviewer kann unbegrenzt forcen indem er nach 2x
  re-startet.
- **evidence:**
  ```yaml
  - kind: file_range
    path: scripts/workflow_engine.py
    lines: 121-121
    quote: "MAX_FORCE_PER_WORKFLOW = 2"
  - kind: file_range
    path: scripts/workflow_engine.py
    lines: 242-248
    quote: "def archive_state(workflow_id: str)"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 659-686
    quote: "TC-023: --force-Bypass umgeht pointer_check"
  ```

### ADV-TC-011 — Smart-but-Wrong: Reviewer mit nur 1 Pointer pro Finding, kind=file_exists, mechanisch valid

- **Pattern:** Smart-but-Wrong (Schema-erfuellt, Disziplin-verletzt)
- **Phase:** B (Schema-Doku) + Engine
- **Level:** L1
- **v1-Gap:** TC-052 testet "synth_legacy_only_file_exists" Adversary-Pattern,
  aber Setup ist `schema_version: 1 + nur file_exists` — global. v1-Test
  asserts "mechanisch alle drei pass". Aber: pro-Finding-Min-Constraint
  (F-I-015 Discipline-Note: "min. einen non-trivial Pointer pro Finding")
  ist NICHT mechanisch enforced. Engine prueft `file_exists` als gueltigen
  Pointer-Type, durchschluepft. v1 hat keinen Test der `kind: file_exists`-
  only PRO FINDING als Discipline-Verletzung dokumentiert (testet nur
  "Mechanik passt").
- **Eingabe:** Reviewer-Output mit 5 Findings, jedes mit `evidence: [{kind:
  file_exists, path: <real-existing-path>}]` — 1 Pointer/Finding, alle
  trivial.
- **Erwartung:** EITHER Engine-Layer warnt (`WARN: finding without non-
  trivial pointer (file_exists is trivial per F-I-015)`), OR Discipline-Layer
  (consistency_check Tier-1-Drift) enforced. NICHT: silent-pass.
- **Mechanik:** F-I-015 sagt "Discipline-Note in Schema-Doku" — keine
  Enforcement-Mechanik. Test asserts dass Doku diese Disziplin enthaelt UND
  dass mindestens ein Validator-Layer sie als WARN-Pfad implementiert (sonst
  toter Buchstabe).
- **Adversary-Begruendung:** v1 TC-052 + F-I-015-Spec-Block sagen "Disziplin",
  testen aber nicht ob Disziplin in Mechanik abgebildet ist (mindestens als
  WARN). Smart-but-Wrong-Pattern: alle Tests gruen weil mechanisch korrekt;
  aber Anti-Fabrication-Mechanik ist trivial-bypass-bar.
- **evidence:**
  ```yaml
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 644-647
    quote: "F-I-015 `kind: file_exists` Defeating-Pattern"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 1336-1356
    quote: "TC-052: Synthetic-Legacy-Output durchlaeuft ohne BLOCK"
  ```

### ADV-TC-012 — Force-Bypass-Drift: Reviewer-Pass + Fix-Pass + Verify-Pass alle nutzen --force, kumuliert

- **Pattern:** Force-Bypass-Drift (Cumulative ueber Workflow-Phasen)
- **Phase:** C2 / D
- **Level:** L4
- **v1-Gap:** TC-023 + TC-058 testen MAX=2 in einer Phase. Workflow build
  hat aber MEHRERE pointer_check-Steps (board, code-review-board, adversary-
  test-plan, spec-amendment-verify in build/workflow.yaml + arch-coherence-
  review, sectional-deep in review/workflow.yaml — 6 Tier-1-Steps in
  Decomposition-Tabelle Spec §3.3). MAX_FORCE=2 gilt fuer den GESAMTEN
  Workflow-Run. Wenn 6 Steps pointer_check haben, koennten 2/6 force-bypassed
  werden — das sind 33% der Tier-1-Defense bypass-bar.
- **Eingabe:** Vollstaendiger build-Workflow-Run mit allen 4 build-Tier-1-
  Steps. User force-bypassed 2 davon (z.B. board + adversary-test-plan).
- **Erwartung:** Spec/Test entscheidet explizit: (a) MAX=2 ist absolut
  pro-Workflow (akzeptiertes 33%-Bypass-Risiko, Trade-off dokumentiert), OR
  (b) MAX wird per-pointer_check-Step gezaehlt (strenger), OR (c) MAX
  unterscheidet pointer_check-Force vs other-completion-Force. v1 testet
  keine dieser Alternativen.
- **Mechanik:** Engine MAX_FORCE_PER_WORKFLOW Z.121 = 2 Konstante. Spec §2.3
  "Force-Counter ist genug Protection". Adversary-Frage: ist es?
- **Adversary-Begruendung:** TC-058 simuliert "User uses --force 2x bis
  MAX=2" aber als single-step. Cumulative-Multi-Step-Adversary-Pfad ist
  separates Bedrohungsmodell. Force-Bypass-Drift heisst: legitime Recovery
  in 2 Steps + bewusste Fabrication in 2 Steps = 4 Force-Aktionen, davon
  2 Fabrication. MAX=2 erlaubt das nicht — aber 2 Fabrication-Force in
  Workflow mit 0 Recovery-Force ist erlaubt. Test asserts dass Spec das
  bewusst akzeptiert (nicht silent).
- **evidence:**
  ```yaml
  - kind: file_range
    path: scripts/workflow_engine.py
    lines: 121-121
    quote: "MAX_FORCE_PER_WORKFLOW = 2"
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 256-263
    quote: "spec_board"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 1478-1497
    quote: "TC-058: Force-Bypass + Pre-commit umgeht beide Layers"
  ```

### ADV-TC-013 — Compensation-Bug: Phase C2 Engine-Edit + Phase D workflow.yaml-Edit beide haben "ich nehme an die andere Welle erkennt das"

- **Pattern:** Compensation-Bug
- **Phase:** C2 + D (cross-Phase)
- **Level:** L3
- **v1-Gap:** Spec §9 Decomposition: Phase C2 implementiert `pointer_check`-
  Type, Phase D editiert workflow.yaml-Steps mit `completion.compound`.
  Wenn Phase D einen Step mit `pointer_check` aber OHNE compound-Wrapper
  (also `completion: {type: pointer_check, source_file: ...}` ohne manual-
  Sub-Check), greift v1 TC-038-Assertion `completion.checks[0].type ==
  "pointer_check"` NICHT (kein checks-Liste). Schema-Validation laesst es
  durch (yaml_loader nach C1-Edit akzeptiert pointer_check als top-level-
  type). Engine pruft pointer_check, wenn fail → block (gut). Aber: kein
  manual-Sub-Check = Step ist auto-complete-bei-pass. User sieht keinen
  Manual-Confirm-Schritt. Stille Funktional-Aenderung.
- **Eingabe:** workflow.yaml-Step mit:
  ```yaml
  completion:
    type: pointer_check
    source_file: "docs/foo.md"
  ```
  (KEIN compound, KEIN manual)
- **Erwartung:** EITHER Schema-Validation rejected `pointer_check` als
  top-level-type (nur compound-Sub-Check erlaubt — Spec-Pattern §2.2),
  OR Engine-Behavior dokumentiert dass auto-complete-on-pass kein manual-
  step braucht (Spec-Decision). v1 nimmt implizit compound-only an.
- **Mechanik:** yaml_loader.py:80 `if ctype not in VALID_COMPLETION_TYPES`
  laesst pointer_check als top-level zu, nachdem es addiert wurde (per
  Spec AC-3). Aber Spec §2.2 zeigt nur Beispiele MIT compound. Disziplin
  vs Mechanik-Drift.
- **Adversary-Begruendung:** Phase C2 (Engine) + Phase D (workflow.yaml-
  Edit) haben beide die Annahme "die andere Welle catched falsche Konfig".
  Engine catched "ungueltige Konfig" auf Engine-Type-Level, nicht auf
  Workflow-Pattern-Level. Compensation-Bug: beide Wellen lassen Fehlerklasse
  durch.
- **evidence:**
  ```yaml
  - kind: file_range
    path: scripts/lib/yaml_loader.py
    lines: 80-82
    quote: "if ctype not in VALID_COMPLETION_TYPES:"
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 181-196
    quote: "completion.compound`-Integration mit Race-Mitigation"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 1008-1031
    quote: "TC-038: 6 Tier-1-Workflow-Steps haben completion.compound"
  ```

### ADV-TC-014 — Pre-commit Mixed-Batch: 50 staged Files, 5 mit schema_version: 1 fabricated, 45 legacy

- **Pattern:** Cleanup-Tx-Silent-Ack (Validator-Loop frueher Exit)
- **Phase:** F
- **Level:** L4
- **v1-Gap:** TC-051 (Performance) + TC-047/048/049 testen pre-commit Filter
  + Single-File-Validation. Spec §5 Filter-Mechanik:
  ```bash
  ... | while read f; do
    grep -lE '...' "$f" >/dev/null && validate ... || true
  done
  ```
  `|| true` = silent-ack of validate-failure. Wenn Validator exit 1
  (fabrication detected), `|| true` schluckt das. Pre-commit produziert KEIN
  WARN-Output ohne explizites stderr-printing im Validator.
- **Eingabe:** 50 staged Files: 5 mit `schema_version: 1` + fabricated
  evidence (Quote-Mismatch), 45 legacy.
- **Erwartung:** Pre-commit produziert mindestens 5 WARN-Lines (eine pro
  fabrication-detected-File), Commit geht durch (WARN-only initial).
  Aktuell-Risk: `|| true` schluckt validator-stderr falls validator nichts
  zu stderr schreibt (nur Exit-Code).
- **Mechanik:** Validator MUSS auf stderr WARN schreiben + exit 1; Pre-commit
  MUSS WARN-Lines aggregieren statt `|| true` silent.
- **Adversary-Begruendung:** Spec §5 Filter-Code zeigt `|| true` literal.
  v1 TC-047 testet "validator wird aufgerufen" — testet NICHT dass
  WARN-Aggregation real outputtet. Cleanup-Tx-Silent-Ack-Klasse: jede
  einzelne validation acked silent als "irgendwas ist schief gegangen,
  egal", User sieht nichts.
- **evidence:**
  ```yaml
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 348-353
    quote: "validate_evidence_pointers.py \"$f\" || true"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 1218-1241
    quote: "TC-047: Pre-commit Check 13 ruft validate_evidence_pointers.py"
  ```

### ADV-TC-015 — Stale-State: schema_version Mid-Run von 0 zu 1 (Migration mid-flight)

- **Pattern:** Stale-State (Migration-Window)
- **Phase:** C2 + G
- **Level:** L3
- **v1-Gap:** TC-019 / TC-029 testen `schema_version: 0` → silent skip.
  TC-055 testet 5 Legacy-Cases statisch. Aber: was passiert in der
  Migration-Welle, wenn ein Reviewer-Output zwischen `--start` und
  `--complete` von schema_version 0 (legacy, draft) auf 1 (final) flippt?
  Engine liest zur Check-Zeit. Was wenn Engine state-snapshot zur Start-
  Zeit cached? Welcher Wert gewinnt?
- **Eingabe:**
  1. Reviewer-Draft mit `schema_version: 0` + fabricated evidence
  2. `--start step` (Engine snapshots state)
  3. Reviewer flippt File auf `schema_version: 1` (versehentlich oder
     boeswillig — fabricated evidence bleibt drin)
  4. `--complete step`
- **Erwartung:** Engine liest zur Check-Zeit aktuell-File (schema_version: 1)
  + faengt fabrication. NICHT: cached snapshot 'legacy' → silent-skip.
- **Mechanik:** Spec §1.4 "schema_version: 1 = aktuelle Pointer-Pflicht.
  Engine-Check enforced". Implizit: Engine liest fresh, nicht cached.
  Test asserts das.
- **Adversary-Begruendung:** v1 testet statische schema_version-Werte.
  Migration-Phase ist genau die Zeit wo Files flippen. Stale-State-Pattern:
  Engine "weiss" Werte aus Start-Zeit, faengt nicht mit Aktuell-Zeit-Werten
  ab.
- **evidence:**
  ```yaml
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 86-90
    quote: "schema_version: 0` ODER fehlend = **legacy**"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 552-572
    quote: "TC-019: pointer_check schema_version: 0 → skip"
  ```

### ADV-TC-016 — Smart-but-Wrong v1-Stichprobe: TC-038 prueft Reihenfolge nicht semantisch (referenziert nur Spec-Section, nicht Engine-Verhalten)

- **Pattern:** Smart-but-Wrong (Test prueft falschen Aspekt)
- **Phase:** D
- **Level:** L1 (Test-Quality)
- **v1-Gap:** TC-038 (`docs/tasks/299-test-plan.md` Z.1008-1031) Assertions:
  - `completion.checks[0].type == "pointer_check"` (FIRST per Race-Mitigation §2.2)
  - `completion.checks[0].source_file` referenziert Variable mit `{spec_name}` ODER `{state_file}`

  Beide sind STRUKTURELLE YAML-Assertions. Test prueft NICHT dass Engine
  bei dieser Reihenfolge tatsaechlich pointer_check VOR manual ausfuehrt
  (das macht TC-024 — aber nur fuer EINEN Step, nicht fuer alle 6 Tier-1
  Steps). Smart-but-Wrong: TC-038 sieht aus wie Mass-Coverage (alle 6
  Steps), aber prueft nur YAML-Structure. Engine-Behavior-Coverage = TC-024
  (1 Step). Wenn 1/6 Steps abweichendes Engine-Verhalten hat, faengt v1 das
  nicht.
- **Eingabe:** Synthetic-Modifikation: Step `code-review-board` in build-
  workflow.yaml hat compound mit `[pointer_check, manual]` (TC-038 pass)
  ABER Engine-Implementierung hat einen Bug der speziell fuer diesen
  Step-Typ den Order-Check skipped (e.g. catches `code-review-board`-step-id
  via Hardcoded-Path). Komplettes E2E-Run.
- **Erwartung:** ADV-TC-016 = TC-038-Erweiterung um Engine-Behavior-Assertion
  PRO Step (nicht nur YAML-Structure). Implementer muss demonstrieren dass
  alle 6 Tier-1-Steps das compound-Verhalten in *real-Engine-Run* haben.
- **Mechanik:** parametrisierter Test ueber alle 6 Tier-1-Step-IDs, jeder
  als E2E-Run mit pointer_check-Fail-Setup → Assertion: manual-Sub-Step nie
  erreicht.
- **Adversary-Begruendung:** TC-038 ist NEW-V-001-Pattern in Test-Plan-
  Erstellung selbst — Test bestaetigt SPEC-Aussage ("Reihenfolge per Spec
  §2.2") via YAML-Read, statt Engine-Verhalten unabhaengig zu pruefen.
  v1-Author: "Spec sagt es, YAML enthaelt es, also ist es so". Adversary:
  "Spec sagt es, YAML enthaelt es, aber Engine-Implementation kann
  davon abweichen — Test muss Engine-Verhalten pruefen."
- **evidence:**
  ```yaml
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 1017-1023
    quote: "completion.checks[0].type == \"pointer_check\""
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 705-723
    quote: "Reverse-Order-Negativ-Check"
  ```

### ADV-TC-017 — Smart-but-Wrong v1-Stichprobe: TC-031 (Eval 6 Misinterpretation) testet WAS-die-Spec-akzeptiert, nicht WAS-mechanik-leistet

- **Pattern:** Smart-but-Wrong (Test ist Spec-Affirmation, nicht Mechanik-Check)
- **Phase:** C3
- **Level:** L2 (Test-Quality)
- **v1-Gap:** TC-031 (`docs/tasks/299-test-plan.md` Z.843-863) Assertions:
  - `exit_code == 0` (Pointer mechanisch valid)
  - "Test-Doc explicit dokumentiert dass das KEIN Bug-Test sondern ein Verifikations-Test fuer das Trade-off ist"

  Test ist tautologisch: "Validator akzeptiert valid pointer + ignoriert
  semantischen Kontext, weil Spec das so sagt". Was *tatsaechlich* getestet
  werden muesste: Validator gibt KEIN false-positive-pass (anders gesagt:
  bei valid-quote-match, REPORT pass — egal ob Reviewer-Schluss korrekt
  ist). Aktuelle Assertion `exit_code == 0` testet nur exit-code, nicht
  was-der-Validator-im-Output-sagt. Wenn Validator silent-pass'ed waere
  bei *jedem* Pointer (Bug), wuerde Test trotzdem grun.
- **Eingabe:** Originale Test-Setup TC-031 PLUS: zweiter Pointer im selben
  File mit invalidem quote-match. Erwartung: validate-Output zeigt 1
  pass + 1 fail Detail-Line, exit 1 (mindestens 1 fail). Aktuelles TC-031
  exit 0-Assertion wuerde diesen Mix nicht catchen.
- **Erwartung:** Validator-Output (stdout/stderr) enthaelt Pro-Pointer-
  Detail (z.B. `pointer 1: ok`, `pointer 2: ok`) + Aggregat-Exit-Code.
  Bei nur 1 valid pointer: stdout `pointer 1: ok`, exit 0. Test asserts
  *Detail-Output*, nicht nur Exit-Code.
- **Mechanik:** §6.2 `validate_file()` returnt `tuple[int, list[str]]` —
  zweite Komponente ist "error_messages". Test asserts dass auch *success-
  messages* (oder leere errors-Liste) per CLI sichtbar ist.
- **Adversary-Begruendung:** TC-031 ist Trade-off-Affirmation-Test, nicht
  Mechanik-Test. Smart-but-Wrong-Klasse: Test sieht aus wie Coverage,
  prueft aber Spec-Selbstaussage. Echter Validator-Bug der allen Pointern
  pass gibt waere durch v1 TC-026/027/028 gecatched (die sind echte
  Mechanik-Tests). TC-031 leistet Coverage-Theatre.
- **evidence:**
  ```yaml
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 843-863
    quote: "TC-031: validate_evidence_pointers.py Exit 0 fuer valid pointer"
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 591-598
    quote: "Eval 6 — Misinterpretation"
  ```

### ADV-TC-018 — consistency_check Tier-1-Drift prueft "mindestens ein workflow.yaml-Step", aber nicht ob `pointer_check`-Sub-Check tatsaechlich PFLICHT-PATH-PFLICHT ist

- **Pattern:** NEW-V-001 (consistency_check-Spec-Drift)
- **Phase:** D
- **Level:** L1 + L3
- **v1-Gap:** TC-041 testet `consistency_check --check tier1-drift` mit
  Setup "Skill mit verification_tier: 1 aber ohne workflow.yaml-Step der
  mit pointer_check-Sub-Check referenziert". Spec §3.2 (Z.232-236) sagt
  "pro `verification_tier: 1`-Skill prueft ob mindestens ein workflow.yaml-
  Step Skill referenziert mit `completion.compound`-Sub-Check `pointer_check`."
  Aber: was wenn Skill in 2 Workflows referenziert ist, EINER mit
  pointer_check-Sub-Check, EINER ohne? "mindestens ein" → pass. Aber:
  ist das die Pflicht-Path-Coverage? Wenn der pointer_check-lose-Pfad
  der primaer-genutzte ist, ist Drift-WARN false-negative.
- **Eingabe:** Tier-1-Skill `code_review_board` referenziert in:
  1. `workflows/runbooks/build/workflow.yaml` Step `code-review-board` MIT compound+pointer_check
  2. `workflows/runbooks/full/workflow.yaml` Step `code-review-board-full` OHNE pointer_check (legacy)

  consistency_check `tier1-drift` aufgerufen.
- **Erwartung:** EITHER WARN fuer "Skill in workflow X referenziert ohne
  pointer_check" (strenge Coverage), OR Spec dokumentiert "min 1 reicht"
  als bewusste Locker-Coverage. v1 testet locker, ohne strenger Variante.
- **Mechanik:** consistency_check-Implementer waehlt min-1-Strategy ohne
  Spec-Klaerung — false-negative-Risk fuer Multi-Workflow-Skills.
- **Adversary-Begruendung:** Spec-Text §3.2 "mindestens ein" ist deklarativ-
  loose. Implementer kann das als "Drift-Schutz erfuellt" interpretieren,
  aber realer Drift entsteht in den Pfaden ohne pointer_check. NEW-V-001:
  Test bestaetigt Spec-Wortlaut, faengt aber semantischen Coverage-Gap nicht.
- **evidence:**
  ```yaml
  - kind: file_range
    path: docs/specs/299-fabrication-mitigation.md
    lines: 232-236
    quote: "Drift-Schutz (mechanisch)"
  - kind: file_range
    path: docs/tasks/299-test-plan.md
    lines: 1082-1105
    quote: "TC-041: consistency_check Tier-1-Drift-WARN"
  ```

---

## Adversary-TC-Total-Count

`adv_tc_count: 18`

Validierung: `grep -c '^### ADV-TC-' docs/tasks/299-test-plan-adversary.md`
muss `18` returnen.

---

## Definition-of-Done (Pflicht-Pre-Fix-Gate)

Per `skills/adversary_test_plan/SKILL.md` §5: alle ADV-TC-* sind first-class
DoD. MCA-Brief enthaelt explicit:

> **All adversary-TCs (`ADV-TC-001` bis `ADV-TC-018`) MUST pass post-
> Implementation.** Pre-commit Check 9 (RUNBOOK-DRIFT) catched wenn
> Adversary-TCs unconfigured bleiben.

Erweiterte v1 + ADV → Pflicht-Coverage = 62 + 18 = 80 TCs.

---

## Cross-Reference-Tabelle (ADV-TC ↔ v1-TC)

| ADV-TC | Pattern | v1-TC den es NICHT abdeckt | v1-Gap-Begründung |
|---|---|---|---|
| ADV-TC-001 | NEW-V-001 | TC-022 | Whitelist != Loop-Z.350 |
| ADV-TC-002 | NEW-V-001 | TC-018 | `[]` != `~` != missing |
| ADV-TC-003 | Stale-State | TC-020 | Skill-Mutation-Window unmodelliert |
| ADV-TC-004 | Race | TC-024 | Reverse-TOCTOU (post-check) |
| ADV-TC-005 | Path-Traversal | TC-053 | String-Check != Symlink-Resolve |
| ADV-TC-006 | NEW-V-001 | TC-044 | Sequential != Parallel |
| ADV-TC-007 | Compensation | TC-038 | YAML-Disziplin != Loader-Enforcement |
| ADV-TC-008 | Smart-but-Wrong | TC-016/017/054 | ASCII-only, Codepoint-Drift offen |
| ADV-TC-009 | Cycle-Entry-Point | TC-022 | Self-Ref != 2-Var-Cycle |
| ADV-TC-010 | Cleanup-Tx-Silent-Ack | TC-023 | Single-Run != Restart |
| ADV-TC-011 | Smart-but-Wrong | TC-052 | Mechanik-Pass != Disziplin-WARN |
| ADV-TC-012 | Force-Bypass-Drift | TC-058 | Single-Phase != Multi-Step-Cumulative |
| ADV-TC-013 | Compensation | TC-038 | compound-Wrap-Pflicht ungetestet |
| ADV-TC-014 | Cleanup-Tx-Silent-Ack | TC-047 | `\|\| true` schluckt WARN-Detail |
| ADV-TC-015 | Stale-State | TC-019/029 | Statisch != Migration-Mid-Flight |
| ADV-TC-016 | Smart-but-Wrong | TC-038 | YAML-Structure != Engine-Behavior |
| ADV-TC-017 | Smart-but-Wrong | TC-031 | Exit-Code != Output-Detail |
| ADV-TC-018 | NEW-V-001 | TC-041 | "min 1" != "alle Pfade" |

---

## Notes

- ADV-TCs sind extending, nicht replacing — v1 bleibt vollstaendig gueltig
- Source-Grounding-Audit: alle Engine-Lines (workflow_engine.py:89, 121,
  242-248, 255-261, 264, 324-336, 343-449, 350-352) und yaml_loader-Lines
  (yaml_loader.py:59-62, 73-109, 80-82, 100-107) via Read-Tool verifiziert
- v1-TC-Lines aus `docs/tasks/299-test-plan.md` mit echten Zeilen-Ranges
  (Z.532-723, Z.843-863, Z.1008-1031, Z.1336-1356, Z.1478-1497) referenziert
- Spec-Section-Lines aus `docs/specs/299-fabrication-mitigation.md` mit echten
  Zeilen-Ranges (Z.71-77, 86-90, 105-110, 162-171, 181-196, 232-236, 256-263,
  290-294, 348-353, 591-598, 644-647) referenziert
