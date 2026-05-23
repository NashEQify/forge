# forge

forge is an opinionated workflow engine and discipline layer for solo
devs and vibe coders doing complex multi-session work with coding
agents. Eight workflows (`build`, `solve`, `fix`, `review`, `research`,
`docs-rewrite`, `save`, `context-housekeeping`) walk the same arc every
time — phase models with persistent state per task, gates at the
boundaries, procedures an unsteered LLM doesn't reliably apply.

The point: when the work outgrows a single session — multi-day builds,
multi-repo refactors, anything where coherence across context loss is
the bottleneck — vibe-coding alone stops scaling. forge gives you
structure for the work without ceremony for trivial fixes.

Dogfooded. Opinionated. Pre-1.0.

## What's in the workshop

**Eight opinionated workflows.** A `build` walks the same arc every
time: scoping → spec interview → spec-board (4-7 reviewer personas in
parallel + chief consolidator) → MCA implements → code-review-board →
close. State persists per task in `.workflow-state/<id>.json` — pause
after spec today, resume at code-board tomorrow on a different
machine, with full phase history. The eight workflows carry the
methodology; their 41 skills carry the moves inside each phase.

**Discipline at the boundaries.** Workflow state gates each phase
transition. Path-whitelist + frozen-zones keep writes inside the
declared scope at tool-call time. Pre-commit checks (13) catch
convention drift before it ships. The combination is the same arc
plus the same guardrails on every task — so the methodology survives a
multi-day build, a context switch, or a fresh session next week.

## How it works

```
                   ┌─────────────────────────────────────────┐
  plain-text  ───► │  BUDDY  (single orchestrator persona)   │
  intent           │  intake-gate · routing · pre-delegation │
                   └────────────────────┬────────────────────┘
                                        │
                   ┌────────────────────▼────────────────────┐
                   │  WORKFLOW   build · solve · fix ·       │
                   │             review · research ·         │
                   │             docs-rewrite · save · …     │
                   │  multi-phase, cross-session state       │
                   │  (.workflow-state/<id>.json)            │
                   └────────────────────┬────────────────────┘
                                        │  per phase
               ┌────────────────────────┼────────────────────────┐
               ▼                        ▼                        ▼
        ┌─────────────┐          ┌─────────────┐         ┌─────────────┐
        │  SKILLS     │          │  BOARDS     │         │  COUNCIL    │
        │  41 active  │          │  spec/UX/   │         │  arch deci- │
        │  single-    │          │  code, 4-14 │         │  sions, 4-5 │
        │  purpose    │          │  personas   │         │  members +  │
        │             │          │  + chief    │         │  adversary  │
        └──────┬──────┘          └──────┬──────┘         └──────┬──────┘
               │                        │                        │
               └────────────────────────┼────────────────────────┘
                                        ▼
                              ┌──────────────────┐
                              │   SUB-AGENTS     │   main-code-agent,
                              │   do the work    │   council-member,
                              │                  │   reviewers, …
                              └────────┬─────────┘
                                       │
                                       ▼
                                    RESULT

  ── HOOKS enforce at every boundary ─────────────────────────────────
     PreToolUse · PostToolUse · UserPromptSubmit · pre-commit (13 checks)
     path-whitelist BLOCK · frozen-zone BLOCK · workflow-reminder · CG-CONV · …
```

## Cross-session continuity

Multi-session work doesn't restart from scratch:

- **`save` / `quicksave`** — writes a structured session-handoff
  (meta-summary, open topics, decisions, next steps). Next session
  reads it on boot and picks up the thread.
- **Workflow engine** — non-trivial workflows (`build`, `fix`,
  `solve`, `review`, `research`, `docs-rewrite`) persist state per
  task in `.workflow-state/<id>.json`. Pause a multi-day build
  mid-step today, resume at the same step tomorrow, on a different
  machine, with full phase history.
- **Boot continuity** — on session start the orchestrator loads
  active intent, session-handoff, and in-flight workflows, then tells
  you where you left off. No manual context reconstruction.

## Get `cc` running

End state: type `cc` inside any directory and a Claude Code session
opens there with the full forge framework (agents, skills, hooks,
workflows) attached — your directory is the working scope, forge is
loaded alongside via `--add-dir` plus `~/.claude/{agents,skills}`
symlinks. `cc forge` always works from anywhere — opens a session in
the framework repo itself, no per-project setup needed.

### Setup

```bash
git clone https://github.com/NashEQify/forge ~/projects/forge
cd ~/projects/forge
python3 -m venv .venv && .venv/bin/pip install pyyaml
bash scripts/setup-cc.sh    # idempotent install + symlinks
cc forge                    # smoke-test — opens the framework
```

Once installed, `cc` works in any directory on your machine — it
doesn't matter where your project repos live. If the directory has no
`intent.md`, Buddy offers a 5-10 min interview to create one;
afterwards `cc` there boots straight into Buddy with active workflows
and session-handoff loaded.

Details — prerequisites, what `setup-cc.sh` does, scope resolution,
gotchas: [`docs/cc-launcher.md`](docs/cc-launcher.md).

## Quick Start

You don't call commands. You tell Buddy what you want; Buddy classifies
the input (discuss / incident / substantial) and routes to a workflow:

| You say | Workflow |
|---|---|
| `solve <problem>` | open-ended: frame → refine → artifact → execute |
| `build task X` | spec → spec-board → code → code-review-board → close |
| `fix bug X` | root-cause first, no symptom-patching |
| `review spec X` | multi-perspective spec-board (4-7 personas + chief) |
| `research X` | knowledge artifact, not code |

For standalone frame / drill / council use, just ask in plain language;
Buddy picks the entry point.

## Honest cost & scope

The discipline layer isn't free. A `build` for a substantial task
spawns a 4-7 persona spec-board (5-15k tokens each), a code-review-
board on the diff, and persists workflow state across phases.
**50-200k tokens go to the discipline layer per substantial build, on
top of the actual implementation.** That earns its keep when a board
catches a spec-violation worth a day of re-work; it's wasteful on a
typo-fix.

For a 30-minute script, a slash-command catalog is faster. forge is
for the work where coherence across sessions is the bottleneck — long
multi-day builds, multi-repo work, anything where context loss costs
more than the discipline overhead.

**Adapters.** Skills are markdown + YAML, workflows are runbooks —
portable to any harness that loads MD files with frontmatter. forge
ships adapters for Claude Code, OpenCode, and Cursor. On Claude Code
and OpenCode the mechanical discipline (path-whitelist, frozen-zones,
state-write-block, engine-bypass, plan-adversary-reminder,
delegation-prompt-quality, workflow-commit-gate, mca-return-stop-
condition, board-output-check, evidence-pointer-check) wires into the
harness's tool-event API and blocks drift at write-time. Under Cursor
(and any harness without a tool-event API) the same workflows run, the
git pre-commit checks fire, and discipline is workflow-driven — drift
gets caught at commit instead of at write.

**What this isn't.** Not a generic agent framework, not a marketplace,
not a LangChain-style abstraction, not an onboarding product.
Adapter-based on top of an existing harness, not a re-implementation.

## Inventory (live)

- **Skills:** [`framework/skill-map.md`](framework/skill-map.md) (41 active)
- **Personas:** [`agents/navigation.md`](agents/navigation.md) (35, incl. boards)
- **Workflows + Routing:** [`framework/process-map.md`](framework/process-map.md)
- **Protocols / References / Hooks:** [`architecture-documentation/02-architecture.md`](architecture-documentation/02-architecture.md)

## Where to go next

| If you are... | Start with |
|---|---|
| **Just trying it out** | [Quick Start](#quick-start) above |
| **Daily user / practitioner** | [`13-operational-handbook.md`](architecture-documentation/13-operational-handbook.md) |
| **Want to understand the model** | [`01-overview.md`](architecture-documentation/01-overview.md) → [`02-architecture.md`](architecture-documentation/02-architecture.md) |
| **Building a skill** | [`04-core-concepts.md`](architecture-documentation/04-core-concepts.md) + [`08-development-and-maintenance.md`](architecture-documentation/08-development-and-maintenance.md) |
| **Adding an adapter** | [`07-tool-integrations.md`](architecture-documentation/07-tool-integrations.md) |
| **Patterns from real drift cases** | [`framework/agent-patterns.md`](framework/agent-patterns.md) |

## Read more

1. [`13-operational-handbook.md`](architecture-documentation/13-operational-handbook.md) —
   methodology-in-practice, daily patterns. If you read one file, read this.
2. [`architecture-documentation/`](architecture-documentation/README.md) —
   13-file reader-journey hub.
3. [`framework/skill-anatomy.md`](framework/skill-anatomy.md) —
   strict shape every skill follows (mechanically validated).
4. [`framework/agent-patterns.md`](framework/agent-patterns.md) —
   14 patterns from real drift cases.
5. [`framework/agentic-design-principles.md`](framework/agentic-design-principles.md) —
   13 design rules (DR-1 to DR-13).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for conventions, PR process, and
hook setup. Security policy: [`SECURITY.md`](SECURITY.md). Code of conduct:
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE).
