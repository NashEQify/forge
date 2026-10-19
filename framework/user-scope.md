# User scope — who the user is, on every machine

forge serves one person per machine installation. Everything that is about
that person — their soul (how Buddy works with them), their values and
profile, the facts about them — lives in **their own user repository**, not
in the framework. The framework knows only where that repository is; the
layout inside it is a fixed convention, identical for every person. This file
is the SoT for that contract. Consumers: `agents/buddy/boot.md`,
`skills/knowledge_processor/SKILL.md`, the boot injectors and
`scripts/forge_install.py`.

## 1. Machine setting

`${XDG_CONFIG_HOME:-~/.config}/forge/user.yaml` (override: env
`FORGE_USER_CONFIG`):

```yaml
version: 1
user_repo: /absolute/path/to/the/users/repo   # required
profile: full                                 # full | daily (installer)
skill_links: []                               # optional, installer: external skill dirs
```

The installer writes it (`forge_install.py --user-repo PATH`). `user_repo` is
the only per-person value; `profile` and `skill_links` describe the machine's
installation, not the person.

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
The whole user repo stays readable; boot does not preload it.

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
`--boot-text`); injectors hand its result to the session. Without an
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
`skills/knowledge_processor/SKILL.md` (mode `user-signal`). Project facts stay
in the project's `context/`.

Authority: configuring a user repo is the person's standing consent that
Buddy maintains that user scope during the work (`knowledge_processor`
§Continuous maintenance). It does not widen permissions for other
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

## 5. Install profiles

`framework/install-profiles.yaml` — `full` (all roles, skills, hooks and
launchers) and `daily` (knowledge maintenance, save, bedrock drill and the
boot entry; always `on-demand`, no software tooling, no framework root
adapter). The profile selects what
is installed and which boot files are injected; it never changes who the user
is.
