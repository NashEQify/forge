# UX authoring — the contracts

Step-loaded unit of `skills/ux_authoring/SKILL.md`. Read it when opening the two contracts, filling a slot or writing
the closure table.

## The files

Two peer files per product, in the project's spec directory: `docs/specs/ux/<product>/look.md` and
`docs/specs/ux/<product>/experience.md`. Neither restates the other: the experience contract names look tokens and
components by the names `look.md` gives them. Both open with:

```
sources: <the specs, task, design system, code and sketches the slots cite>
peer: <the other file>
```

## Slots and source tags

Each slot below is required. A slot holds one of:
- a decision followed by its source tag: `(user)`, `(delegated: <the person's words>)`, `(acceptance: <task>/AC-n)`,
  `(spec: <path> §<section>)`, `(code: <path>)`, `(design system: <name>)`, `(sketch: <path>)`;
- `n/a: <reason>`, when the surface has no use for it (a CLI has no elevation);
- `open: <question>`, until the person answers.

A slot filled from options the person asked for carries `(user)`. When two sources disagree (a label spelled two
ways, a state handled differently in spec and code), the slot is `open`, citing both.

## Look contract (`look.md`)

```
## Base
design system: <name and path> | none
## Tokens
| Kind | Token | Value | Use | Source |
## Components
| Component | Visual rule | Tokens | Source |
## Do and don't
| Do | Don't | Source |
```

- **Base.** With a design system named, Tokens and Components record only what departs from it or adds to it.
- **Tokens.** Kinds: colour, typography, spacing, shape, elevation. A colour gives both values where the product has
  a light and a dark theme, and each text colour its contrast ratio against its background.
- **Components.** Every component the experience contract names has a row here. With a design system named, a
  component taken unchanged has the row `<name> | Base | — | (design system: <name>)`.

## Experience contract (`experience.md`)

```
## Foundation
form factor: <mobile | web | desktop | terminal | several: which> | platform or UI system: <name> | none
## Surfaces
| Surface | Reached from | Need it delivers | Source |
## Journeys
### J<n> <protagonist>, <situation>
1. … numbered steps
climax: <step n: the need it meets>
failure: <what goes wrong and what the protagonist sees>
## States
| Surface | State | What the person sees and can do | Source |
## Component behaviour
| Component | Behaviour rule | Source |
## Interaction
<gestures, keys, confirmations, patterns ruled out>
## Voice
language: <…> | terms the protagonist uses: <…>
| Do | Don't | Source |
## Accessibility floor
<keyboard, screen reader, motion, target size, focus order>
## Closure
<the closure table>
## Open
<each open slot: question, who answers, by when>
```

- **Foundation.** The form factor is settled before Surfaces closes; a journey often settles it (a protagonist on a
  phone means a phone surface).
- **States.** Per surface, each state that applies: empty, loading, error, offline, permission denied, partial,
  stale. A state that does not apply is left out.
- **Journeys.** A protagonist is a named person in a situation ("Mira, late evening after work"). Steps use the
  surface and component names of this file.
- **Component behaviour.** With a UI system named in Foundation, only behaviour that departs from it.
- **Voice.** The wording the protagonist reads: labels, confirmations, errors, empty states. Internal names (IDs,
  codes, data-model terms) appear only where the protagonist uses them.
- **Open.** Each open slot with its question, who answers it, and by when: before the dispatch of a brief that needs
  it, or a named owner or task.

## Closure

```
| Need (verbatim) | Source | Surface | Journey step | Gap |
| Surface | Journey steps that land there | Gap |
```

- **Needs** are the needs for a person that the acceptance, the request and the source spec state, copied verbatim.
- **Gap** is empty, or one of `no surface`, `no journey`, `deferred: <reason or owner>` with the source tag of the
  ruling (the person's answer, or a spec or task that recorded the deferral before this run). A `no surface` or
  `no journey` row is asked about and stays until the person answers.
- Rows cover the change's scope (`SKILL.md` Process step 1). A surface outside it appears only when a journey of the
  change passes through it. Rows of earlier changes stay; a change adds and updates the rows of its scope.

## Source

BMAD-METHOD (MIT License, © 2025 BMad Code, LLC); Forge's register of adopted methods.
