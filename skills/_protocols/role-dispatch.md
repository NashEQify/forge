# Protocol: Role dispatch

Read it before dispatching a Forge role (a file under `agents/` of the framework root) to an agent: an implementer, a
tester, a code review seat or chief, a board seat or chief, a council member, adversary or chief. It says how the call
is written when the host lists the role as an agent type and when it does not (`framework/invariants.md` Invariant 4).
The consumer is the dispatching agent. The cost it prevents: a call to an agent type the host does not have, a role
file path that resolves against the project instead of the framework, and a read-only role that edits.

## The call

1. Look the role up in the host's agent listing at the moment of dispatch (Claude Code: the agent types the Agent tool
   offers, a plugin role as `forge:<role>`; Codex: the roles `spawn_agent` offers).
2. **Listed:** call that agent type. The host loads the role file and applies its tool limits.
3. **Not listed:** call a general agent (Claude Code: `general-purpose`; Codex: `spawn_agent` without a role). Its
   prompt starts with this line, followed by the dispatch text the calling skill prescribes:

   `You are the Forge role <role>. Read <root>/agents/<role>.md first and follow it as your role definition; paths it names resolve against <root>, a bare `_protocols/` path against <root>/agents; your working directory stays <project>.`

   `<root>` is the framework root as an absolute path: the `FRAMEWORK_DIR` the boot entry names, which in a plugin
   install is the plugin's installed copy, not a checkout. Without a boot entry (a plugin skill used on its own),
   `<root>` is the directory that holds `.claude-plugin/` above the skill's folder. A relative `agents/<role>.md`
   resolves against the project and misses.
4. **Model:** name it in the call per `framework/models.md`, in both cases; role files set none.

With the plugin, Claude Code lists the roles whose file sets `disallowedTools` and Codex lists none, so every other
role takes step 3.

## A read-only role as a general agent

Read-only roles: a code review seat or chief, a board seat or chief, a council member, adversary or chief, and every
role whose file sets `disallowedTools`. They return their output inline and the caller writes it. As a general agent
such a role has every tool, and nothing on the host enforces the limit. So:

1. The prompt's first line is followed by: `Read-only: do not create, edit or delete files and run no command that
   changes state; return your output inline.`
2. Record `git rev-parse HEAD` and `git status --porcelain` of the checkout the agent works in before the dispatch and
   again after its return. A difference is written beside the return as `working tree changed during a read-only
   role: <paths or HEAD>`, and the caller finds out who changed it before adopting the return; a change the role made
   is a role breach, and that return does not count as a review. The check misses a further edit to a path that was
   already changed, a write to an ignored path or outside the checkout, and it cannot tell parallel agents apart; the
   read-only line is the only guard there.
