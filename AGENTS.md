# Buddy — Codex / OpenCode Adapter

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
Format and types are enforced by the `pre-commit` hook (CG-CONV).

## Active Hooks

Forge's shared git hooks run when installed in the active repository:
`pre-commit.sh` (pre-commit, pre-merge-commit and commit-msg; PLAN-VALIDATE / CG-CONV /
SKILL-FM-VALIDATE BLOCK; SECRET-SCAN / SOURCE-VERIFICATION WARN). The two
SessionStart scripts are Claude-specific and conditional, not universal Codex
boot hooks. Codex uses the managed AGENTS entry installed by
`scripts/setup-codex.sh`; its loading must be checked in a fresh session. The framework runs no tool-event hooks
(PreToolUse / PostToolUse / UserPromptSubmit); write-time discipline is
protocol-anchored via protocols + operational.md.

## OC Constraints
The consumer repo is the CWD; the framework is mounted via the OpenCode
launcher (`$FRAMEWORK_DIR/orchestrators/opencode/bin/oc`, with
`OPENCODE_CONFIG_DIR=$FRAMEWORK_DIR/orchestrators/opencode/.opencode`).
A consumer's project-level AGENTS.md (in the consumer repo root) adds
to this framework AGENTS.md, it doesn't replace it. Commands are
trigger words without a prefix (wakeup, save, checkpoint, think!).
OpenCode follows the same protocol-based method. Its launcher, instruction
loading, permissions and actually installed Git checks must be verified for
that host. Shared methodology does not establish identical execution or
enforcement. There is no tool-event (PreToolUse/PostToolUse) hook layer on
either harness.
