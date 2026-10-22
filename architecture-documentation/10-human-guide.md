# 10 — Human guide

Forge helps an agent carry context and apply useful methods while you retain the
goal, values and consequential choices. You should be able to ask for a result
without coordinating every internal step.

The most useful input is a clear desired outcome with its constraints. You do not
need to name a workflow or prescribe how many agents should work on it.

## Start with the result you need

Compare “help with my application” with:

> Continue the application using the current draft and the criteria we recorded.
> Produce a draft I can review. Leave unknown facts visible, and do not submit it.

This supplies a result, relevant context and an action boundary. The same pattern
works for a decision or software change: say what success looks like, which evidence
matters and which actions are authorized.

| Your situation | Useful input |
|---|---|
| Everyday work | Topic, current material, desired result and practical constraints |
| A difficult choice | Goal, viable options, hard limits, preferences and uncertainty |
| A software change | Intended behavior, affected users and acceptance evidence |
| An investigation | Observed symptom, impact, reproduction evidence and scope of action |

A clear instruction authorizes work within its scope. Existing authorization should
survive routine phase changes. Clarification is useful when the outcome, risk or a
consequential choice is unresolved; it should not be a ritual between every step.

## What to expect from memory

Forge's continuity is stored in files in your authorized workspaces. It can preserve
useful knowledge, decisions, corrections and the next step for open work. It cannot
assume access to an earlier conversation that was never captured.

You can ask, “What do we already know about this?” The agent should find the relevant
owner, read current material and check qualifications. A missing index entry is not
proof that a topic never occurred; exhausted or inaccessible sources should be
reported as limits.

Correct stale facts explicitly. A changed plan and a correction of an earlier error
have different meanings. The useful current view should preserve that distinction
and retain enough source context to interpret it.

Personal facts belong in your configured user scope. Activity and technical facts
belong with their project/topic owner. If a personal write is blocked, the agent
should report it as deferred, not copy private details into a shared project.

## Choose depth deliberately

A direct answer may be enough for a small, reversible question. Use **Frame** when
the problem needs clarification, **Bedrock** when its assumptions need examination,
and **Council** when alternatives need distinct perspectives.

For example, a Council comparing two approaches should explain what each makes
easier, what each sacrifices, and which missing evidence could change the choice.
Agreement among reviewers is useful evidence to examine, not proof of correctness.

A standalone method can return its result in the conversation. Saving the result
is a separate action under your existing permissions. A recommendation should stay
a proposal until the relevant decision has been made. Your values are inputs to
reasoning, not facts for an agent to infer from one passing request.

See [method selection](06-usage-workflows.md#general-reasoning) for the practical options.

## Review the outcome

A good result makes it possible to answer:

- Does this serve the goal and respect the constraints?
- Which statements come from evidence, and which are proposals or inferences?
- What was actually changed, checked or saved?
- Which limitations or unresolved decisions still matter?

For software, look for behavior verified by appropriate checks. A passing command
proves only what that command checks. For a service change, process liveness or an
HTTP response alone may not prove the user-visible outcome works.

For knowledge work, check the leading material and whether you can find it again.
A polished handoff cannot compensate for a missing draft or an unrecorded correction.

## Save with the right expectation

Useful knowledge is maintained during work within its authorized scope. `save`
reconciles it with the session handoff so a later session can continue open topics.
It also requests commit and push to the active project's tracked upstream unless
that project's rules restrict them. If you want local persistence only, say so.

Separate user-repository changes follow that repository's own rules. A local save,
a successful push and a fully reconciled save are distinct outcomes; the agent
should report which happened. Ordinary maintenance alone does not authorize a push.

## When the framework gets in your way

State the intended mode and boundary: “Use the project's normal working rules” or
“Use Council for this decision only.” On-demand work does not automatically require
software tasks, specification cycles, boards or workflow-engine records. Installing
`full` does not change that rule.

For software work, lighter paths remain conditional on the actual risks. Changing
a security boundary, data schema or live system can justify safeguards even when
the edit is small. The question is what failure the safeguard prevents for the
consumer, not how many files were touched.

If the agent claims a capability the host cannot supply, ask for the concrete
limit. Instructions, tooling and actual host enforcement are different kinds of
evidence. [Troubleshooting](12-troubleshooting.md) covers setup and continuity gaps.

## Next steps

[Daily handbook](13-operational-handbook.md) · [Usage and workflows](06-usage-workflows.md) ·
[Overview](01-overview.md) · [Documentation hub](README.md)
