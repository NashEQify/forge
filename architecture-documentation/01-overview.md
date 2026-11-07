# 01 — Overview

Forge is a discipline for software development with AI coding agents. It is a
collection of skills, roles and workflows for the craft (specs, test design, briefs,
verified review, root-cause fixing, architecture, security, UX, documentation) and for
the workflow control around it (sizing, scoping, delegation to a coding agent and
separate reviewers, evidence before "done", continuation across sessions). Forge is
agent instruction text plus supporting tools, and runs in the agent application you
already use.

You work through **Buddy**, the conversational entry. Describe the goal in ordinary
language. Your workspace's intent and rules determine the relevant context, working
style and limits on action.

## What Forge covers

| Area | Result | Typical request |
|---|---|---|
| Software development | A connected path from intent to a verified result: spec, plan, implementation, review, fixes and an evidenced close | “Build this feature and verify the behavior.” |
| Continuity | The project's intent, context and session handoff, so a change that spans sessions resumes where it stopped | “Continue the open task from where we stopped.” |
| Reasoning methods | A clearer problem, examined assumptions or a comparison of viable choices, for decisions inside development | “Use a Council to compare these approaches.” |

Continuity serves the development work; the reasoning methods serve its decisions.
Each can also be used at its own scope: supplied context is sufficient for a
standalone method, and project context needs no software task system. A personal
extension (a user repository with your profile, Buddy in every session of the
machine) builds on this and is optional.

The [capability contract](../framework/capabilities.md) defines their ownership.

## Knowledge and continuity

Useful facts and corrections are reconciled during work under the applicable
maintenance authority. The agent reads relevant context before dependent answers,
keeps claims at a responsible owner and updates routes when leading material changes.

Personal preferences belong in the configured user scope. An activity, application
or technical setup belongs with its project or topic owner. A short profile provides
boot context; topic navigation leads to details when needed. There is no required
life-domain taxonomy or automatic transcript archive.

`save` reconciles knowledge and the session handoff. It preserves open topics,
next steps, blockers and necessary approvals. An explicit `save` also requests
commit and push to the active project's tracked upstream unless its rules restrict
that action. Ordinary continuous maintenance alone does not authorize publication.
See the [daily handbook](13-operational-handbook.md) for the practical sequence.

Continuity is file-based. The agent needs access and must read the right files;
Forge does not provide automatic access to previous chats or a hosted memory service.
Protected publication checks the baseline before replacing files and retains
recovery information for interrupted changes across multiple files. Its locks
coordinate cooperating writers, not every external editor.

## General reasoning

Three methods address different needs:

- **Frame** clarifies the problem and opens a meaningful solution space before
  recommending an approach.
- **Bedrock** examines assumptions down to logic, physical constraints and chosen
  values, then traces their implications.
- **Council** compares a choice from distinct perspectives, preserving disagreement
  and uncertainty for a better-informed decision.

A method can return a useful report directly in the conversation. It does not need
Git, a user repository, a software workflow or an automatically created task.
Persistence is separate and follows the caller's authorization. A recommendation
is still a proposal until the relevant decision is made.

See [method selection and examples](06-usage-workflows.md#general-reasoning).

## Software development: from intent to verified result

**Build** takes a defined change through the stages below. When the solution is
still open, the Solve workflow (tell Buddy **“Forge my idea”**) works out what would
meet the goal and how to check it, and can hand the chosen change to Build.
[Worked example](06-usage-workflows.md#start-with-an-idea).

Buddy chooses the stages the change needs. Each stage hands a defined output
to the next. [Build lifecycle](../workflows/runbooks/build/lifecycle.md).

| Stage | What Forge does | What is particular |
|---|---|---|
| Intent and sizing | Writes down the goal, the acceptance criteria and the authorization, and picks the route from three written facts: open points the user would notice, what cannot be undone, and the footprint | Safety floors are checked before any shortcut; a short path still verifies ([eligibility](../framework/direct-eligibility.md)); one goal per change, a second goal offered as its own task ([sizing facts](../workflows/runbooks/build/lifecycle.md#sizing-facts)) |
| Spec, UX, architecture | Writes the behaviour the change promises as a spec with one test-matrix row per promise; UX and architecture run on their trigger. UX writes a look and an experience contract from your answers, with journeys of a named person and a check that every need has a screen and every screen a journey ([UX authoring](../skills/ux_authoring/SKILL.md)). Architecture writes a spine: only the decisions separately built units could otherwise choose incompatibly, with the rest named as deferred ([architecture spine](../skills/_protocols/architecture-spine.md)) | The matrix is the test plan before code; the durable spec keeps what tests cannot ([spec carriers](../framework/spec-engineering-implementation-specs.md#convention-spec-carriers)) |
| Plan | Checks every pair of tasks that share a file or interface before the first dispatch | Conflicts are ruled by the approved acceptance, then the architecture spine, then the spec ([plan conflicts](../skills/_protocols/plan-conflicts.md)) |
| Dispatch | Hands each implementer a brief file with the approved acceptance verbatim and read-only, on a model named for its role | The implementer reports in a file and returns a short summary; it starts no agents of its own ([dispatch](../skills/_protocols/mca-dispatch.md), [models](../framework/models.md)) |
| Review | Reviewers read one package of exactly the change under review | Each finding is verified at its location before it is graded; its cause is classified; the implementer may push back ([review package](../skills/code_review_board/review-package.md), [verification](../skills/_protocols/finding-verification.md)) |
| Fix | Fixes the cause the classification found, in the code, the spec or the mechanism; an intent question goes back to the user | Fix rounds keep their memory and end at a cap with a ruling per open finding; debugging stops after three failed fixes ([cause before answer](../skills/convergence_loop/cause-before-answer.md), [at the cap](../skills/convergence_loop/at-the-cap.md)) |
| Close | Records the result, moves durable decisions into their owners and closes the task | Each completion claim carries its evidence ([completion claims](../skills/_protocols/evidence-author-claims.md)) |

Effort follows risk and uncertainty. A bounded reversible change can take a short
complete path; consequential contracts, security, migrations and live systems keep
their safeguards. On the short path Buddy chooses per change how much check it gets:
a change that alters no behaviour, or a trivially reversible one its existing test
shows, he makes himself (quick); a tested local change goes to the coding agent and
Buddy checks the diff and tests (checked); and a change with
remaining uncertainty or a wider effect is checked by a separate agent run (reviewed).
The final reply names the path and what did not run, and your word ("quick",
"reviewed") sets it ([who builds and who checks](04-core-concepts.md#who-builds-and-who-checks)). Decisions an agent takes for the user are listed in its final
message with their cost and undo. Explicitly selected development state can
contribute to common save and resume; loading a session checks its exact state and
does not silently advance work or unpause a workflow.

The approaches behind these stages are in [core concepts](04-core-concepts.md#how-forge-works);
the routes are in [development usage](06-usage-workflows.md#software-development).

## Forge and the frameworks it learned from

The idea, the concept and how the parts work together are Forge's own. For the
individual practices, Forge took the best of what other open agent frameworks
published and built it into that design, under their MIT licenses and with credit.
Each project is known for something of its own:

| Project | Known for | What Forge took, in its own terms |
|---|---|---|
| [Superpowers](https://github.com/obra/superpowers) | Subagent-driven development, systematic debugging, verification before completion, writing skills that agents follow | Brief and report files for each implementer, a model per role, the review package, fix rounds with memory and a cap, hypothesis-first debugging, conflict checks across a plan's tasks, the claim-to-evidence table, matching an instruction's form to the failure it prevents |
| [Addy Osmani's agent-skills](https://github.com/addyosmani/agent-skills) | A broad library of engineering skills | Skills for documentation and decision records, security, frontend, shipping, migration and API design; a triage checklist; variation lenses for framing a problem; accessibility and performance checklists |
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | Right-sized agile planning, explicit decisions, review triage | Verifying each finding before grading it, classifying its cause, approved acceptance carried verbatim, a fix that guards only demonstrated states, edge rows as the test plan, when to settle a point and report it |
| [spec-kit](https://github.com/github/spec-kit) | Spec-driven development: the specification as the source of the code | The complexity-tracking table, and the gap inventory that checks each requirement against the present code |
| [Matt Pocock's skills](https://github.com/mattpocock/skills) | Small, sharp engineering skills | Zooming out to the module map, deep-module architecture review, the feedback loop as the product of debugging, the decision-record threshold, the one-question-at-a-time design interview |

Forge's design holds them together: every adopted method answers to the same
intent, authorization rules, evidence standard and proportional effort, and hands its
result to the next step, so the methods work as one process instead of as separate
rule sets. This is a description, not
a ranking: each project above stands on its own, and someone who wants exactly one of
their approaches may be better served by it directly.

Some adoptions are ideas that Forge wrote in its own text. The others keep
substantial text or a table's structure: the agent-skills and Matt Pocock skills and
the checklists among them, and several tables and protocol structures from
Superpowers, BMAD-METHOD and spec-kit. The [register of adopted methods](../framework/adopted-methods.md)
lists each one, its source, what changed and the Forge file that holds it. The root
[NOTICE](../NOTICE) carries the projects' license notices.

## What's in the box

Forge ships as one plugin for Claude Code and Codex. One committed line in a
project's `AGENTS.md` starts Buddy in that project and changes nothing outside it;
one user setting starts Buddy in every session of the machine and adds a personal
context folder, so knowledge and open work carry across projects. Both
make the same methods available: knowledge maintenance, save, the reasoning methods
and the development tooling. Availability does not select a software workflow.

The plugin and the setup carry the supported host integrations. Actual capabilities and
instruction loading differ by host; Cursor's rules-based integration is distinct.
Use [installation](05-installation.md) and [host support](07-tool-integrations.md)
to choose and verify your setup.

## Who is it for?

Forge is written for developers who use Claude Code or Codex for agent-driven
software work, above all a single developer on changes too complex to hold in one
session. Single skills, boards and the reasoning methods are useful on their own;
the full workflow earns its weight on complex changes. Maintainers who want shared
methods across workspaces keep each workspace's own content, vocabulary and
operational approvals.

The trade-off is discipline and overhead. A small context update is inexpensive
compared with a multi-agent Council or review board. More perspectives can expose
errors, but shared assumptions can survive review. File checks and Git hooks verify
specific properties; they cannot guarantee model judgment or universal compliance.

## Next reading

[Daily handbook](13-operational-handbook.md) · [Usage and methods](06-usage-workflows.md) ·
[Installation](05-installation.md) · [Architecture](02-architecture.md) · [Documentation hub](README.md)
