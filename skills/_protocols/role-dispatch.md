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
4. **Model:** name it in the call per `framework/models.md`, in both cases; role files set none. A tier above the
   role's row names its reason, a tier below is not taken (owner: `framework/models.md` §Naming the model).
5. **Review execution:** when a review seat's scope includes executing tests or probes, the prompt says: "Run the
   prescribed gate once and the change's witnesses; keep your test runs within <bound>; a further run names the new
   evidence it adds. If role or host limits prevent a required run, give Buddy the exact execution request." The
   prompt grants no extra permission.

6. **Return contract:** the prompt ends with what the return must end with: the adoption lines of
   `skills/return_summary/SKILL.md` §Adoption line, quoted; for a role that starts commands or agents, "do not return
   while one of them runs"; for a review seat, its severity scale (critical, high, medium, low:
   `agents/_protocols/reviewer-base.md`) and, as the prompt's last part, the evidence layout of its reviewer
   protocol (code or spec)
   (§Mandatory envelope and clean output, §Output format: frontmatter first with the captured run, subject and slot
   verbatim, then findings with their `evidence:` pointers); the dispatcher adds no return shape of its own. A review
   seat's prompt also tells it
   to write its draft to a temporary file outside the repository, run
   `python3 <root>/scripts/validate_evidence_pointers.py --strict --repo-root <checkout> <file>` on it and correct what it prints before
   returning (the validator reads files only, not stdin). Purpose: the returner holds the contract and its check, and the adopter
   meets the check in the return.

With the plugin, Claude Code lists the roles whose file sets `disallowedTools` and Codex lists none, so every other
role takes step 3.

## A read-only role as a general agent

Read-only roles: a code review seat or chief, a board seat or chief, a council member, adversary or chief, and every
role whose file sets `disallowedTools`. They return their output inline and the caller writes it. As a general agent
such a role has every tool, and nothing on the host enforces the limit. So:

1. Follow the prompt's first line with the applicable restriction:
   - **Executing review seat:** `Read-only: preserve reviewed files and shared and remote state. Confine the
     temporary effects of assigned checks to their authorized private test runtime, within all host and role limits.
     Return your output inline.`
   - **Other read-only role:** `Read-only: do not create, edit or delete files and run no command that changes
     state; return your output inline.`
2. Record `git rev-parse HEAD` and `git status --porcelain` of the checkout the agent works in before the dispatch and
   again after its return. A difference is written beside the return as `working tree changed during a read-only
   role: <paths or HEAD>`, and the caller finds out who changed it before adopting the return; a change the role made
   is a role breach, and that return does not count as a review. The check misses a further edit to a path that was
   already changed, a write to an ignored path or outside the checkout, and it cannot tell parallel agents apart; the
   read-only line is the only guard there.
