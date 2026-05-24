# Intent — forge (PUBLIC MIRROR STUB)

> **You are reading the OSS mirror.** Active development happens in
> the private `forge_dev` SoT. This repository is produced solely by
> `forge_dev/scripts/release-sync.sh` (one-way rsync, exclude-list-
> driven, `--delete`) and is **never hand-edited** except for one-
> time release hygiene. If you arrived here intending to write a
> task, file, spec, or dogfood-feed entry: stop. Switch to
> `forge_dev`. The misroute case the per-repo split was created to
> prevent (2026-05-25): a parallel session interpreted *"forge feed
> this"* as *"land in the public forge repo"* instead of the
> private `forge_dev/docs/dogfood-learnings/forge-feed.md` log.
>
> The full framework — Vision, Positioning, Pillars, Consumer model,
> Adapter layers, Non-Goals — is documented for OSS consumers in
> [README.md](README.md) and [architecture-documentation/](architecture-documentation/),
> which describe the framework from the consumer's single-repo
> perspective. The active development intent (this file's counterpart
> in `forge_dev`) is not part of the public surface; the project
> intent doesn't change what the framework is, only how its
> maintainer reasons about it.
>
> Canonical topology statement (mirrored from `forge_dev`):
> `CLAUDE.md` Invariant 8 + [docs/STRUCTURE.md](docs/STRUCTURE.md)
> §Repo topology. Symmetric stubs (excluded from sync, hand-
> maintained on this side): `docs/plan.yaml` (north_star only),
> `docs/tasks/.gitkeep` (convention marker), `intent.md` (this
> file).

## For OSS consumers

You probably want one of these instead:

- **[README.md](README.md)** — what forge is, what's in the
  workshop, how it works, honest scope.
- **[architecture-documentation/](architecture-documentation/)** —
  deeper framing per area: workflows, skills, discipline layer,
  adapter mechanics.
- **[orchestrators/](orchestrators/)** — per-harness setup
  (`claude-code/`, `opencode/`, `cursor/`).
- **GitHub repo description + issues** — current state, known
  caveats, where to file feedback.

## For developers who arrived in the wrong CWD

You want `forge_dev`. The public mirror has no live tasks
(`docs/tasks/` carries only `.gitkeep`), no live plan
(`docs/plan.yaml` is a north_star stub), no operational context
(`context/` is excluded by sync), and no dogfood feed
(`docs/dogfood-learnings/` is excluded by sync). Writes here would
either be lost on the next sync (`rsync --delete` enforces it) or,
worse, propagate confusion if force-pushed.
