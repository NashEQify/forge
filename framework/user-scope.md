# User scope — who the user is, on every machine

forge serves one person per machine (the plugin model's user switch, on OpenCode too). Everything that is about
that person — their soul (how Buddy works with them), their values and
profile, the facts about them — lives in **their own user repository**, not
in the framework. The framework knows only where that repository is; the
layout inside it is a fixed convention, identical for every person. This file
is the SoT for that contract. Consumers: `agents/buddy/boot.md`,
`skills/knowledge_processor/SKILL.md`, the boot injectors and
`scripts/forge_setup.py`.

## 1. Machine setting

`${XDG_CONFIG_HOME:-~/.config}/forge/user.yaml` (override: env
`FORGE_USER_CONFIG`):

```yaml
version: 1
user_repo: /absolute/path/to/the/users/repo   # required
buddy: every-session                          # optional, plugin on Claude Code: Buddy in every session
```

The plugin model's setup writes it (`forge_setup.py every-session`, `skills/setup/SKILL.md`; with
`--create-user-repo` it creates the folder with `context/user/profile.md` and `navigation.md`). `user_repo` is
the only per-person value. Settings from earlier installations may still carry `profile`, `skill_links` or
`maintenance`; the reader accepts them and the setup does not write them. Without `user.yaml` (a plugin session under a
project's activation line only), a project session has no user scope.

The plugin (§5) reads this setting at session start; whenever Buddy starts,
under the project's activation line as under the user switch, it resolves the
user scope from it when one is configured. `buddy` is the user switch on Claude
Code, read by the plugin's boot hook: the value `every-session` starts Buddy in
every session; any other value is a warning and leaves the switch off. Codex
runs no boot hook; there the user switch is the activation line in
`~/.codex/AGENTS.md`. Without the switch, Buddy starts only in a project whose
`AGENTS.md` (in the project directory or a parent up to the Git root) carries
this line on its own:

```
Forge: start Buddy. Before the first answer, run the forge:boot skill and follow the boot entry it returns.
```

Elsewhere the plugin's boot hook stays silent and its listed skills stay
usable. The rule lives in `scripts/user_scope.py` (`ACTIVATION_LINE`,
`is_active`).

## 2. Convention inside the user repo

```
<user_repo>/context/user/
  soul.md        optional — how Buddy works with this person; else forge's soul
  profile.md     boot-loaded — who the person is, including values,
                 priorities and constraint defaults (short)
  navigation.md  on demand — index to the detail files in this folder
  <topic>.md     detail files, reached through navigation.md
```

`profile.md` is read in every session in every repo, so keep it short; detail belongs in topic files reached through `navigation.md`.
The whole authorized user repo stays readable; boot does not preload it.
Profile links to user navigation; user navigation offers a route to the person's
activity/project navigation for recall from another CWD. Activities and technical
setups belong to their project owners even inside the personal repository.
Personal topic preferences remain in user scope. Placement, semantic admission,
retrieval, validity, provenance, history and restructuring have one owner:
`skills/knowledge_processor/SKILL.md` (one current statement per claim, §3–§4;
restructuring, §6). Restructuring the top-level files (`soul.md`, `profile.md`,
`navigation.md`) or changing what is boot-loaded is a proposal to the person; content
writes to them follow the knowledge processor.
`inner-life.md` is for relevant reflections, not an automatic bucket for preferences.
No unconditional companion-file loading or fixed life-domain taxonomy.

Recovery uses `framework/continuity.md`: user operations use
`<user_repo>/context/user/maintenance-pending.md`; project operations use
`<project_root>/context/maintenance-pending.md`. They stay distinct when both roots
are the same. Project-only visitors do not inspect personal recovery. Check pending
work and capture a coherent scoped snapshot before dependent reads or mutations.

## 3. Resolution

1. Read the machine setting. Missing or without `user_repo` → **no user
   scope**: forge soul, no personal files, and say once in the greeting
   "no user scope configured".
2. `<user_repo>/context/user/` missing → same as 1, naming the path.
3. Soul: `context/user/soul.md` if present, else `agents/buddy/soul.md`.
   A user soul replaces the forge soul. To extend it instead, the user soul
   says so in its first lines ("read `agents/buddy/soul.md` first, then:").
4. Profile: `profile.md` if present; a missing one is reported. How the
   person wants to be worked with belongs in `soul.md`, not in the profile.

Never substitute another person's repository or a remembered path. The
deterministic implementation is `scripts/user_scope.py` (`--json`, `--soul`,
`--boot-text`); injectors hand its result to the session. A session-start
injector also includes the resolved soul and `agents/buddy/operational.md`
as whole files where the host carrier has room
(`agents/buddy/boot.md` §User scope). An install-time block includes no
files: the person's files and framework Markdown change without a reinstall. Without an
injection, an agent resolves the same way by reading the machine setting.

The soul follows the **person**, not the repository: the resolved soul
applies in every repo the person works in. Project rules (`AGENTS.md` /
`CLAUDE.md`) still govern the project's work and win on conflict.

## 4. Writing user-scope facts

A fact about the user (preference, person, decision about their life or
career, correction of their profile) belongs to the user scope regardless of
which repo the session runs in. File it under `<user_repo>/context/user/` at
its responsible topic file, found through `navigation.md` (new topic → new
file, linked from `navigation.md`), following
`skills/knowledge_processor/SKILL.md` (mode `user-signal`; update where the subject
already stands, §5). Project facts stay in the project's `context/`.

Authority: configuring a user repo is the person's standing consent that
Buddy maintains that user scope during the work (`skills/knowledge_processor/continuous-maintenance.md`). It does not widen permissions for other
repositories, commits or pushes; commit and push of the user repo follow that
repo's own rules (`save` persists it separately when it is not the active
project).

**Never into the wrong repo.** A user-scope fact is written only inside
`<user_repo>/context/user/`. If that write is blocked (sandbox, missing
access), the fact is reported in the answer as `deferred:` — it is never
parked in the active project's handoff, buffer or context, because that
repository may be shared with other people. Person-wide rules for handling
the person's data (provenance, sensitive topics) belong in their `soul.md`,
so they apply wherever the facts are written.

Resolved paths are checked after following symlinks (`realpath`) and must
stay inside `<user_repo>`.

## 5. Placement

The active project's intent selects the workflow (`framework/workflow-selection.md`); where Forge is placed
never changes who the user is.

The plugin is how Forge is placed on Claude Code and Codex: the host's plugin
manager installs this repository's plugin (`.claude-plugin/`), and Buddy starts
under the activation line or the user switch (§1). Its entry names the profile
`plugin`, which is no `user.yaml` profile; on Claude Code the plugin's
SessionStart hook carries it, on Codex the `forge:boot` skill prints it.
