# Eval patterns

Domain-specific quality criteria for L2 / L3 tests.
Complement the coverage matrix: not just "tests green?" but
"is the result good enough for this domain?"

## Usage

In execution mode, the tester reads the relevant domain
file and checks that the implemented tests cover the eval
criteria. Missing criteria → coverage matrix gap → back to
main-code-agent.

## Available patterns

| Domain | File | Status |
|--------|------|--------|
| FastAPI endpoints | `fastapi.md` | active |
| Postgres / brain queries | `postgres.md` | active |

New domains: create on the first task that needs them.
No upfront design — patterns emerge from real tasks.

## Scope boundary

L4 / L5 testing stays manual until the harness is in
place. No attempt to automate L4 / L5 without tracing
infrastructure — evaluation without observability is
blind. Pre-harness, behavioural observations of agents
and workflows are captured in the rolling dogfood feed
(`docs/dogfood-learnings/forge-feed.md`) rather than as
discrete golden test cases.

Pre-harness manual traces: incident block + transparency
header are the current tracing proxy. Sufficient as long
as every agent run is one CC session and Buddy reads the
return synchronously. At harness build that is replaced
by Langfuse / Phoenix (ADR OBS-001).
