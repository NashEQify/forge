# forge

<img src="assets/vibeforge-logo.png" align="right" width="294" alt="forge mascot — a friendly furnace with headphones smithing code on a circuit-board anvil. The forged code reads: def forge(vibes): build(); ship()." />

forge is **disciplined LLM capabilities** between you and your coding
agent — an opinionated orchestration layer that gives the LLM
*more reach*, not *less rope*. Aimed at a single dev who wants
vibe-at-complexity: the velocity of vibe-coding with the coherence of
process when the work outgrows a single session.

Eight workflows (`build`, `solve`, `fix`, `review`, `research`,
`docs-rewrite`, `save`, `context-housekeeping`) walk the same arc
every time. Three review boards (Spec-Board, Code-Review-Board,
UX-Board) and an Architectural Council provide a multi-perspective
reasoning substrate when one model can't hold the whole thing
coherently. A small set of universally-portable hooks (git pre-commit
plus SessionStart for boot) catches drift where mechanical catching is
both cheap and reliable across harnesses.

The point: when the work outgrows a single session — multi-day builds,
multi-repo refactors, anything where coherence-across-context-loss is
the bottleneck — unsteered vibe-coding stops scaling. forge augments
the LLM's reasoning with skills + boards + council, so the LLM stays
in the driver's seat while drift gets caught at the boundaries.

Dogfooded. Opinionated. Pre-1.0.

> **Honest framing (2026-05-31, post-self-review).** Earlier versions
> of this README claimed "mechanical enforcement" as a primary pillar
> — *"the LLM cannot rationalize away a shell hook"*. Empirically that
> framing was overstated: most hooks were stderr-WARN (observability),
> several BLOCK hooks had bypass vectors, the PreToolUse layer was
> CC-Terminal-CLI only (claude-desktop / claude-web / Codex / Cursor
> lack it). The framework's actual operating substrate is **Buddy's
> reasoning, augmented by skills + boards + council + protocols**.
> The hook layer is a thin reinforcement at the boundaries — git
> pre-commit checks (universal) + SessionStart for boot (semi-
> universal). The CC-Terminal-only PreToolUse / PostToolUse /
> UserPromptSubmit layer is being removed (May 2026 hook-paradigm
> shift) so the framework runs identically on every supported harness.

## What's in the workshop

**Eight opinionated workflows.** A `build` walks the same arc every
time: scoping → spec interview → spec-board (4-7 reviewer personas in
parallel + chief consolidator) → MCA implements → code-review-board →
close. The 8 workflows carry the methodology; the 41 active skills
carry the moves inside each phase. Workflow state can persist per
task in `.workflow-state/<id>.json` (atomic-write + flock) for
genuinely-multi-day-multi-phase builds — currently in usage standby;
Buddy's reasoning + the `save` session-handoff cover most cross-
session needs without ceremony.

**Multi-perspective decision substrate.** Three boards (Spec-Board,
Code-Review-Board, UX-Board) and an Architectural Council are the
framework's reasoning layer for irreversible or multi-path decisions.
Anti-anchoring discipline (`_protocols/dispatch-template.md` +
`context-isolation.md`) keeps Buddy from coloring the reviewers'
findings; the orchestrator reads only the chief consolidator's signal
(Invariant 1). Council has four modes (light / standard / full /
interactive) with proportionality gates and an explicit
*council-before-user-escalation* rule when Buddy hits a multi-path
uncertainty.

**Reinforcement at the boundaries — universal-portable only.** Git
pre-commit catches convention + schema drift before it ships on any
harness. SessionStart hooks bootstrap Buddy on claude-desktop /
claude-web / Codex where the `--agent buddy` flag isn't an
entrypoint. The earlier CC-Terminal-CLI-only PreToolUse / PostToolUse
/ UserPromptSubmit layer is being dropped — discipline replicates,
and harness-portability beats CC-coupled enforcement.

## How it works

Every session enters through **Buddy** — the single orchestrator persona.
Buddy handles intake, classifies the request, and routes to one of the
eight workflows; sub-agents do the actual work.

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

  ── HOOKS (universal-portable only, post-ADR-004 2026-05-31) ──
     SessionStart (boot inject) · git pre-commit (5 checks)
     PLAN-VALIDATE BLOCK · CG-CONV BLOCK · SKILL-FM-VALIDATE BLOCK
     SECRET-SCAN WARN · SOURCE-VERIFICATION WARN
```

## Cross-session continuity

Multi-session work doesn't restart from scratch — but only if you end
sessions with `save`.

- **`save` / `quicksave`** — the explicit session-end / mid-session
  ritual. Type `save` before closing the terminal; Buddy writes a
  structured session-handoff (meta-summary, open topics, decisions,
  next steps). The next session reads it on boot and picks up the
  thread. `quicksave` is the lighter mid-day variant for context
  switches.
- **Workflow engine** — non-trivial workflows (`build`, `fix`,
  `solve`, `review`, `research`, `docs-rewrite`) persist state per
  task in `.workflow-state/<id>.json`. Pause a multi-day build
  mid-step today, resume at the same step tomorrow, on a different
  machine, with full phase history.
- **Boot continuity** — on session start the orchestrator loads
  active intent, session-handoff, and in-flight workflows, then tells
  you where you left off. No manual context reconstruction.

## Setup

forge runs on top of an existing coding-agent harness. Three are
supported out of the box: **Claude Code**, **OpenCode**, and **Codex**
(Desktop / CLI). Buddy is the orchestrator persona in all three — same
methodology, same workflows, same boards.

**One command provisions the whole Claude Code adapter:**

```bash
bash ~/forge/scripts/setup-cc.sh
```

After that, opening **any** folder in **any** Claude Code entrypoint
(`cc` terminal launcher, `claude` CLI, claude-desktop, claude-web)
triggers Buddy boot. The discipline-layer hooks (path-whitelist,
frozen-zones, brief-claims, workflow-reminder, SessionStart boot-inject,
…) fire globally — they live in `~/.claude/settings.json`, not in
per-project files, and resolve to absolute forge paths so the folder
you opened is irrelevant.

How the boot signal actually reaches Buddy still differs per
entrypoint, but every path lands on the same boot:

| Entrypoint | Boot trigger |
|---|---|
| `cc` (terminal launcher) | launcher passes `--agent buddy` + framework inject |
| `claude --agent buddy --add-dir` (CLI direct) | user's explicit `--agent buddy` flag |
| claude-desktop / claude-web | SessionStart hook `buddy-boot-inject.sh` (gated on `CLAUDE_CODE_ENTRYPOINT in {claude-desktop, claude-web}`) |

What `setup-cc.sh` does (idempotent — re-run any time to repair or
re-apply):

- installs the `cc` launcher at `~/.local/bin/cc` (absolute forge path
  substituted in)
- generates `<forge>/.claude/path-whitelist.txt` from the template
- **merges forge hooks into `~/.claude/settings.json`** using `jq`;
  preserves your other keys (`effortLevel`, `voiceEnabled`, custom
  `permissions`, …); backs the prior file up with a timestamp before
  rewriting
- links `~/.claude/agents` and `~/.claude/skills` to forge's persona
  and skill SoTs (so the `Task` and `Skill` tools discover them)
- wires forge's git pre-commit and commit-msg hooks in the forge
  checkout itself

The reason setup-cc.sh writes hooks **globally** rather than into a
per-project file: forge hooks should fire in every claude-code session
regardless of which folder you opened, and the absolute paths must be
substituted at setup time (the same value the agent stores in
`FRAMEWORK_DIR`). Per-project `.claude/settings.json` files are not
required by forge — if you want project-specific overrides, drop them
into `.claude/settings.local.json` (which CC merges over the global)
and they'll layer on top.

Two setup paths:

- **Full** — one setup script per harness. Installs a launcher
  (`cc` / `oc`), wires persona + skill discovery, and registers
  forge's PreToolUse hooks where the harness exposes a tool-event
  API. This is the canonical install and gets you the full discipline
  layer with write-time enforcement.
- **Quick (Claude Code only)** — two symlinks, no scripts, no
  install-time magic. Personas and skills discoverable, but write-time
  hooks off. Fastest way to try forge in a one-off project.

### Full setup

```bash
git clone https://github.com/NashEQify/forge ~/forge

# Claude Code — installs cc launcher + symlinks + path-whitelist,
#               merges forge hooks into ~/.claude/settings.json,
#               wires forge's git pre-commit hooks
bash ~/forge/scripts/setup-cc.sh

# OpenCode — installs `oc` launcher, opencode.jsonc, forge-hooks plugin
bash ~/forge/scripts/setup-oc.sh

# Codex Desktop / CLI — agent + skill wrappers under ~/.codex, ~/.agents
bash ~/forge/scripts/setup-codex.sh
# optional: also wire PreToolUse hooks into a specific project
bash ~/forge/scripts/setup-codex.sh ~/your-project
```

Each script is idempotent and self-contained: it detects
`FRAMEWORK_DIR` from its own location, installs the launcher and
adapter pieces, and verifies prerequisites. Re-run any time to repair
the install. (Codex has no `--add-dir` equivalent, so `FRAMEWORK_DIR`
is baked in at install time — the reason a script is mandatory there.)

Then start a session in any repo:

```bash
cc <project>        # Claude Code via launcher (or bare `cc` for cwd)
oc                  # OpenCode via launcher (forge config auto-loaded)
codex               # Codex Desktop / CLI — Buddy discovered globally
```

The `cc` / `oc` launchers default to `~/projects/<project>` for the
project root. If yours live elsewhere, override `$PROJECTS_DIR` or
edit the launcher — both are short shell scripts. Per-repo git
pre-commit hooks for a consumer project (any harness):
`bash ~/forge/scripts/install-git-hooks.sh`. Launcher details:
[`docs/cc-launcher.md`](docs/cc-launcher.md).

### Quick (Claude Code CLI only)

This path is for the terminal CLI (`claude` binary) — **not** for
claude-desktop / claude-web, which need `bash setup-cc.sh` (see the
boot-mechanics table above). The trade-off below also applies: no
PreToolUse hooks.

```bash
git clone https://github.com/NashEQify/forge ~/forge

mkdir -p ~/.claude \
  && ln -sn ~/forge/.claude/agents ~/.claude/agents \
  && ln -sn ~/forge/.claude/skills ~/.claude/skills
```

Then in any project:

```bash
cd ~/your-project
claude --agent buddy --add-dir ~/forge
```

Buddy boots, reads `agents/buddy/{soul,operational,boot}.md`, loads
the workflows + skills, and starts orchestrating. If the project has
no `intent.md` yet, Buddy offers a short interview to create one.

Trade-off vs. full setup: PreToolUse hooks (path-whitelist,
frozen-zones, state-write-block, …) are **not** active. Methodology
and the workflow engine carry the same discipline — you just lose
mechanical write-time enforcement. To add the git pre-commit layer
per repo: `bash ~/forge/scripts/install-git-hooks.sh`.

Why the symlinks are needed: `--add-dir ~/forge` grants read access
to the framework tree, but Claude Code discovers personas via
`~/.claude/agents/` — not via `--add-dir`. Without the symlinks the
`Task` tool can't dispatch `board-chief` / `main-code-agent` / any
forge persona, and the `Skill` tool sees zero forge skills. (The
agent can still read `skills/<name>/SKILL.md` via the Read tool and
follow the methodology manually — the SoT-read fallback documented in
[`agents/buddy/operational.md`](agents/buddy/operational.md) — but
proactive skill discovery is off.)

### Prerequisites

- the harness itself:
  [Claude Code](https://docs.anthropic.com/en/docs/claude-code),
  [OpenCode](https://opencode.ai), or Codex (Desktop / CLI)
- **git**, **bash**, **jq**
- **Python 3.10+ + `pyyaml`** — for the workflow / plan engines
- Optional: **`chub` CLI** for `get_api_docs`,
  **`gitleaks`** for the SECRET-SCAN pre-commit check

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
| `save` | end-of-session: writes the session-handoff so the next session picks up the thread |
| `quicksave` | mid-session checkpoint: same handoff format, lighter footprint |

For standalone frame / drill / council use, just ask in plain language;
Buddy picks the entry point.

**`save` is the session-end ritual.** Without it, the next session
starts cold — workflow state in `.workflow-state/<id>.json` still
resumes, but the discussion thread, open decisions, and "where I was
heading" don't. Type `save` before you close the terminal; type
`quicksave` when you're switching context mid-day and want to leave a
breadcrumb without the full wrap-up. See
[Cross-session continuity](#cross-session-continuity) above.

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

**Adapters.** forge's discipline is layered — skills (markdown + YAML),
workflow runbooks, the workflow engine (Python + YAML state), persona
definitions, task / plan YAMLs, and a hook layer (PreToolUse +
pre-commit). Most of it is harness-neutral: any harness that loads MD
+ YAML and can spawn sub-agents can run forge. An adapter buys
mechanical persona / skill discovery, tier-0 anchor loading, and —
where the harness exposes a tool-event API — write-time enforcement
of forge's PreToolUse hooks (path-whitelist, frozen-zones,
state-write-block, engine-bypass, plan-adversary-reminder,
delegation-prompt-quality, workflow-commit-gate,
mca-return-stop-condition, board-output-check, evidence-pointer-check).

Cursor is the fourth shipped adapter; it has no tool-event API, so
those hooks fire only at git pre-commit — drift catches at commit
instead of at write, everything else runs identically. Any harness
without a dedicated adapter can still load the skills and run the
workflows; discovery is just less mechanical and write-time hook
enforcement is off.

**What this isn't.** Not a generic agent framework, not a marketplace,
not a LangChain-style abstraction, not an onboarding product.
Adapter-based on top of an existing harness, not a re-implementation.

## Inventory (live)

- **Skills:** [`framework/skill-map.md`](framework/skill-map.md) (41 active + 1 draft + 1 deprecated)
- **Personas:** [`agents/navigation.md`](agents/navigation.md) (40, incl. boards + council)
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
5. [`references/agentic-design-principles.md`](references/agentic-design-principles.md) —
   research-derived design principles backing the framework's skill /
   persona / runbook design. Historical reference, not consulted in
   the runtime loop.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for conventions, PR process, and
hook setup. Security policy: [`SECURITY.md`](SECURITY.md). Code of conduct:
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE).
