# Installation activation

How a change to Forge's own sources reaches the hosts that read them, and how it is checked. Read it before changing
Forge's sources on a machine whose sessions use them, and when a change must be shown active.

**Where hosts read Forge.** Claude Code and Codex take Forge as a plugin, and neither reads the plugin's source in
place: Claude Code copies it into a versioned plugin folder, also when the marketplace is a local directory, and Codex
keeps a marketplace copy. A change reaches them only through the host's own update (`claude plugin marketplace update
forge` then `claude plugin update forge@forge`; `codex plugin marketplace upgrade forge`), and a running session keeps
the copy it started with until it is restarted. OpenCode set up through `scripts/forge_setup.py` gets a
`forge:boot` skill that names a Forge folder and reads it in place (the folder the setup ran from, or Codex's stable
plugin folder in place of Claude Code's versioned plugin folder). For a clone and for Codex's stable folder a change
there reaches the next session without a further step; a skill that names a versioned Claude Code plugin folder needs
the setup run again after a plugin update. Cursor reads its project rules.

## Choosing the path

Classify each change before editing and state the classification in its brief, decision or return record. Unclear
whether a path is read directly or as data by an engine or generator → resolve the fact (`readlink`, the generator,
the reader); still unclear → full path.

**Light path — instruction-only.** Every changed path is Markdown at an existing owner that hosts read directly from
the framework root: `framework/`, `skills/`, `workflows/` runbook text, `agents/`, the root adapters `CLAUDE.md` and
`AGENTS.md`, `orchestrators/` rule text, and project docs. Steps: edit in the framework root; when skill frontmatter or
the skill inventory changes, regenerate the derived wrappers (`scripts/generate_skill_wrappers.py`, then `--check`)
and the generated navigation; run the router check (`scripts/generate_workflow_router.py --check`) and the
consistency check; commit under the repository's commit rules. Sessions read the change on their next read; a session
that already loaded a changed boot or always-loaded file keeps the old text, so start a fresh session before relying
on such a change. Markdown that an engine or generator reads as data is not plain instruction text: skill frontmatter
fields such as `status`, `invocation` and `evidence_layout`, and workflow definitions. Such a change, and a new or
changed non-Markdown source next to the edit, takes the full path.
Text an outside agent runs on a user's machine (install, setup, removal) is shown working only by the live run in
`skills/_protocols/evidence-author-claims.md` §8.5.

**Full path — everything else.** Scripts, hooks, plugin manifests, host settings and integrations, workflow
definitions and compatibility mappings, engine-read YAML/JSON, state formats, and every mixed change:
1. **Before changing a source that running sessions read in place,** establish that the affected sessions will not
   read or write the changing set while it changes: work on a branch in a worktree outside the framework tree and
   change the read-in-place checkout only by the merge. A running agent may load another skill or call a script later
   even if its earlier instructions are cached.
2. **Check:** the change-scoped tests during the work, and the project's full gate before the merge
   (`skills/testing/lean-suite.md` §Change-scoped runs and the full gate); `scripts/plugin_release_check.py` when the
   plugin's manifests, hooks or shipped files change; the light-path checks for the Markdown in it.
3. **Activate:** merge when no session is in the middle of an operation the change alters (a workflow-engine run, a
   continuity publication, a script call). For a folder hosts read in place (a clone named by OpenCode's `forge:boot`
   skill) the merge is the activation; for a plugin it is the release where the marketplace is the public one, then
   each host's plugin update, run right after the merge or release. Until then, name the hosts and running sessions
   that do not have it yet.
4. **Verify** in a fresh session on each host that reads the change: normal entry and instruction loading, and the
   changed behaviour. Record host, commit, observations and limits. A check that did not run stays unverified.
5. **Recovery** is a new commit through the repository's commit rules (a revert or a fix); never reset history or
   hand-edit installed copies to make a host appear current.

Boot hooks never pull or set up the framework on their own; they report what they find, and the update follows this
procedure. Consumer-only Git updates follow their own authorization and preservation rules.

## Consumer integration

Only authorized small reviewed changes remove duplicated general algorithms from
consumer rules. Keep concrete topic owners, storage, language, safety and approvals.
No automatic content reorganization or re-import belongs to the upgrade. Separately
authorized migrations preserve working-tree baselines, claim maps and usable routes.
A withheld/coordinate-before-access consumer must not be inspected until that boundary
is met; a synthetic fixture is not live acceptance. Keep each target's outcome distinct.
