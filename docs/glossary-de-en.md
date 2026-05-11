# Glossary DE → EN

Authoritative term mapping for the OSS translation of `forge`
(Task 300, Phase A). Use this glossary as source-of-truth whenever a German
term has more than one plausible English equivalent — pick the one listed
here, not a synonym.

This file is the working spec for translation consistency. Add new terms
during Phase B / C as they surface; do not silently translate inconsistent
variants.

---

## Translation rules (general decisions)

- **Compound nouns:** drop hyphens unless the compound is a recognized
  methodology term. `Spec-Engineering` → `Spec Engineering`,
  `Reviewer-Persona` → `reviewer persona`, but
  `Source-of-Truth` → stays as compound (etablished). `Pointer-Schema`
  → `pointer schema` (lowercase, no hyphen, methodology term).
- **Capitalization:** common nouns lowercase in English (`workflow`,
  `agent`, `spec`, `review`). Proper roles capitalized (`Buddy`,
  `Chief Reviewer`, `MCA`).
- **Acronyms:** keep as-is (`SoT`, `ADR`, `MCA`, `CC`, `OC`, `OSS`,
  `AC`, `BL`).
- **Anglicisms in DE source:** if the source already uses an English
  loanword (`Drift`, `Hook`, `Gate`, `Backlog`), keep it — do not
  re-translate.
- **Voice:** active, second-person where the source addresses Buddy or
  the reader. Imperative for rules. No bureaucratic hedging.
- **Idiomatic:** translate meaning, not words. Work content-driven, not
  mechanical. If a literal mapping reads stiff or foreign in English,
  reformulate. Preserve intent and structure; ditch the German word
  order.
- **Code identifiers:** never touch (file names, function names, config
  keys, hook names). Comments and user-facing strings only.

---

## Methodology core

| DE                              | EN                                |
|---------------------------------|-----------------------------------|
| Spec-Engineering                | Spec Engineering                  |
| Source-Grounding                | source grounding                  |
| Source-of-Truth (SoT)           | Source-of-Truth (SoT) — keep      |
| Discipline-as-Mechanism         | Discipline-as-Mechanism — keep    |
| Werkbank                        | workbench                         |
| Schicht                         | layer                             |
| Saeule / Säule                  | pillar                            |
| Tier-0 / Tier-1 / Tier-2        | Tier-0 / Tier-1 / Tier-2 — keep   |
| Methodik                        | methodology                       |
| Vorgehen                        | approach / process (context)      |
| Leitfaden                       | guideline                         |
| Probestueck / Probestück        | pilot                             |
| Konsistenz                      | consistency                       |
| Drift                           | drift — keep                      |
| Pflicht                         | required (rule) / mandatory (norm)|
| Vorbedingung                    | precondition                      |
| Folgetask                       | follow-up task                    |
| Dogfooding                      | dogfooding — keep                 |

## Roles + agents

| DE                              | EN                                |
|---------------------------------|-----------------------------------|
| Buddy                           | Buddy — keep                      |
| Sub-Agent                       | sub-agent                         |
| Reviewer-Persona                | reviewer persona                  |
| Hauptansprechpartner            | primary contact                   |
| Orchestrator                    | orchestrator                      |
| Planner / Worker                | planner / worker — keep           |
| Council-Member                  | council member                    |
| Chief Reviewer                  | Chief Reviewer — keep             |
| Adversary                       | adversary — keep                  |
| Implementer                     | implementer — keep                |
| Konsument / Consumer            | consumer                          |
| externer Beitragender           | external contributor              |

## Mechanism / infrastructure

| DE                              | EN                                |
|---------------------------------|-----------------------------------|
| Hook                            | hook — keep                       |
| Gate                            | gate — keep                       |
| Workflow-Engine                 | workflow engine                   |
| Pre-Delegation                  | pre-delegation                    |
| Pfad-Whitelist                  | path whitelist                    |
| Frozen Zone                     | frozen zone                       |
| Engine-Step                     | engine step                       |
| Boundary                        | boundary — keep                   |
| Dispatcher                      | dispatcher                        |
| Adapter                         | adapter                           |
| Trigger                         | trigger — keep                    |
| Bookkeeping                     | bookkeeping — keep                |

## Document types + lifecycle

| DE                              | EN                                |
|---------------------------------|-----------------------------------|
| Spec                            | spec — keep                       |
| Discovery / Discoveries         | discovery / discoveries — keep    |
| ADR                             | ADR — keep                        |
| Audit-Trail                     | audit trail                       |
| Backlog                         | backlog — keep                    |
| Aufgabe / Task                  | task                              |
| Meilenstein                     | milestone                         |
| Phase                           | phase                             |
| Welle                           | wave                              |
| Pass / Pass-Cycle               | pass / pass cycle — keep          |
| Save / Checkpoint               | save / checkpoint — keep          |
| Sitzung                         | session                           |
| Handoff                         | handoff — keep                    |
| Stale                           | stale — keep                      |
| Sunset                          | sunset — keep                     |

## 299-Vocabulary (source-grounding layer)

| DE                              | EN                                |
|---------------------------------|-----------------------------------|
| Pointer-Schema                  | pointer schema                    |
| Evidence-Pointer                | evidence pointer                  |
| Reviewer-Protokoll              | reviewer protocol                 |
| Reviewer-Protokoll-Migration    | reviewer protocol migration       |
| Quote-Match                     | quote match                       |
| Quote-Length-Cap                | quote length cap                  |
| Layout-Klasse                   | layout class                      |
| Completion-Type                 | completion type                   |
| Engine-Step-Gate                | engine step gate                  |
| Fabrication-Mitigation          | fabrication mitigation            |
| Source-Verifikation             | source verification               |
| Authority-Log                   | authority log                     |
| pruefbar / prüfbar              | verifiable                        |

## German function words + common phrases

Context-sensitive — apply with judgment, but be consistent within a file.

| DE                              | EN                                |
|---------------------------------|-----------------------------------|
| etablieren / etabliert          | established                       |
| eskalieren                      | escalate                          |
| zuverlaessig / zuverlässig      | reliable                          |
| kaschieren                      | hide / paper over                 |
| umbiegen                        | bend / force-fit                  |
| nachbohren                      | dig deeper / probe                |
| schärfen / nachschärfen         | sharpen / refine                  |
| entscheiden                     | decide                            |
| nachfragen                      | ask back / clarify                |
| Engpass                         | bottleneck                        |
| Mehr-Arbeit                     | extra work / rework               |
| ueberhaupt / überhaupt          | at all                            |
| kein Touch                      | no edit / hands off               |
| im Detail                       | in detail                         |
| absolut offensichtlich          | obviously / self-evidently        |
| im Zweifel                      | when in doubt                     |

---

## Maintenance

- Phase B + C add terms here when they surface — do not translate
  inconsistently and fix later.
- Decisions (compound vs hyphen, capitalization) are sticky — flip a
  decision globally with a single sweep, not per-file.
- "— keep" means: do not translate; the source already uses the
  English (or established) form.
