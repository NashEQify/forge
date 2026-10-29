# Buddy — Claude Code Adapter (Framework SoT)

Read and follow `framework/work-principle.md` before taking up work.
Resolve this reference against the framework root; retain the consumer CWD.
Reread it after compaction.

## Boot
Load and follow: the resolved soul (`framework/user-scope.md`; default
`agents/buddy/soul.md`), `framework/invariants.md`, `agents/buddy/operational.md`,
`agents/buddy/boot.md`.
After compaction, reread before continuing every file in the boot entry's
post-compaction reread list.

## Framework-wide rules
Workflow selection, intent-driven work, the invariants (numbered as cited
elsewhere: "Inv 4" and so on) and observability hold in every project and live
in `framework/invariants.md`; read and follow it before taking up work (the boot
entry names it). This file adds the host's load list and the rules that apply
only when the active project is the forge repository itself.

## Language Policy
- Default language for all new work is English.
- Write code comments, specs, ADRs, task content, and review artifacts in English.
- Use German only when quoting existing German source text verbatim or when the user explicitly requests German output.

## Frozen Zones + Consistency
SoT: `docs/STRUCTURE.md`. Consistency cascade: `context-rules.md`.

## Commit
Format and types are enforced by the `pre-commit` hook (CG-CONV). On
`save`: ALWAYS go through `workflows/runbooks/save/WORKFLOW.md`, no
shortcuts.

Before any commit, Buddy must **PERSIST** → operational.md §Post-Action
Obligations (Context · History · Backlog).

**No branching ceremony** (applies when the active project is the forge
repository itself; consumer repos follow their own commit rules).
Single-dev workflow — Buddy commits directly
to `main` autonomously at workflow phase boundaries (the runbooks
prescribe per-phase commits) and at logical work boundaries; no
per-commit authorisation is needed — this overrides the harness "ask
before committing" default. The Claude-Code session-guidance rule "If on
the default branch, branch first" does NOT apply here. Bounds:
Conventional-Commit format (CG-CONV), the pre-commit hook must pass,
never bypass hooks. An explicit task boundary such as "no commit" overrides
this standing local-commit permission. With several Buddy sessions on one
repository, the commissioning Buddy commits and integrates unless a brief
names another committer; parallel writers use their own worktree and branch
(`agents/buddy/coordinating-sessions.md`). `git push` requires authorization for
publication to the intended remote; destructive operations (force-push,
`reset --hard`, history rewrite) require explicit authorization for that action.
A heads-up alone is not permission. See process-map.md, Authorization.

## Active Hooks

Shared git hooks and host-specific boot integration. Presence of a script
does not prove that a host invokes it.

SessionStart on configured Claude entrypoints (not Codex):
- `buddy-boot-inject` — triggers the Buddy boot sequence where `--agent
  buddy` isn't an explicit flag (claude-desktop / claude-web). Load-bearing
  for boot.
- `session-start-remote` — remote Claude entry only: observes coordinated
  maintenance readiness with `--maintenance status --require-ready`. It does
  not update sources, install, or resume workflows; resume follows boot discipline.

Codex boots through the explicit managed AGENTS entry from
`scripts/setup-codex.sh`. Additional-directory access or a Buddy role file
alone does not establish that framework instructions were loaded.

git pre-commit (5 checks, 3 BLOCK + 2 WARN; CG-CONV runs in commit-msg, the
others once per commit in pre-commit or, for a merge commit that `git merge`
creates, pre-merge-commit):
- BLOCK: PLAN-VALIDATE (plan_engine schema integrity), CG-CONV
  (Conventional-Commits format), SKILL-FM-VALIDATE (Skill frontmatter
  validation; also C3 description trigger-marker WARN — active skills
  must carry `Use when`/`Triggers when`/`Trigger:`).
- WARN: SECRET-SCAN (gitleaks), SOURCE-VERIFICATION (board/council
  review evidence-pointer schema; section cross-references that the
  commit touches).

Everything else is carried by discipline, not hooks:
- Path: Buddy writes within intent-scope; deliberate-action for anything else.
- History / WORM zones (`context/history/**`): convention — corrections via
  `.correction.md` sidecars (rare).
- Delegation prompt quality: `_protocols/dispatch-template.md` +
  `mca-brief-template.md` carry the brief shape; Buddy authors with the
  protocol open.
- Plan-adversary: Buddy invokes `plan-adversary` explicitly on non-trivial
  Tier-1 edits per `_protocols/plan-review.md`.
- MCA return: Buddy reads the return summary himself per `operational.md`
  §Sub-Agent Return.
- Board / council output: read-only reviewers and Chiefs return artifacts;
  Buddy persists verbatim with provenance, then adopts the decision based on
  evidence. See `agents/buddy/multi-perspective.md`.
- Workflow continuity: handoff + boot-resume carry it across turns;
  `workflow_engine.py --boot-context` on demand.

<!-- Source of truth for what's wired:
orchestrators/claude-code/settings.json.template. -->
