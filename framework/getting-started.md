# Getting started with Forge

Forge is a discipline for software development with AI coding agents. Its continuity
and reasoning methods also work without selecting a software workflow. Keep working in your own project or knowledge folder.

1. Read the [overview](../architecture-documentation/01-overview.md) to choose the
   capability you need.
2. Follow [installation](../architecture-documentation/05-installation.md): the
   plugin (Claude Code, Codex) starts Buddy in a project whose `AGENTS.md` carries
   the activation line, or in every session with the user switch; the OpenCode
   `full-ai-integration` installation puts Buddy into every session of the
   machine, with a personal context folder.
3. Open a fresh agent session in your workspace and verify that its project rules,
   configured user scope and relevant context are actually loaded.
4. Describe the work. For ordinary use start with the
   [daily handbook](../architecture-documentation/13-operational-handbook.md);
   for a structured method or selected software workflow use the
   [usage guide](../architecture-documentation/06-usage-workflows.md).

Useful knowledge is maintained during work. `save` reconciles knowledge and the
handoff and follows the project's commit/push rules. It does not require a software
plan. Optional personal context stays in its configured owner; project knowledge
can be used independently.

To update, run `git pull` in the Forge checkout; the next session start brings
the installed entries up to it. A machine on the coordinated maintenance path
(for changing Forge itself) follows [installation activation](installation-activation.md).

This page is a reader entry. Canonical selection rules are in
[process-map.md](process-map.md); capability ownership is in
[capabilities.md](capabilities.md). Do not duplicate those algorithms in a consumer.
