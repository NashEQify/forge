# Convergence loop — at the cap

Step-loaded unit of `skills/convergence_loop/SKILL.md`. Read it when a re-review leaves verified findings open and the
code board's re-review limit (`skills/code_review_board/verdict.md` §5, counted per mechanism, the foundation override
of `skills/code_review_board/REFERENCE.md` §Re-review limit included) allows no further one. On the code board that
limit decides when the loop ends; the pass-4 extension of `SKILL.md` §Pass-3 termination adds no round there. The
checks and answers it reuses are in `skills/convergence_loop/cause-before-answer.md`.

### At the cap

Buddy gives each open finding a class and a ruling instead of a further round; before the limit, each finding takes
its cause's answer (`cause-before-answer.md` §Cause before answer). A finding with a ruling recorded on the same
location and claim keeps that ruling. `false` rows and routed `maybe-false` rows
(`skills/_protocols/finding-verification.md` §What follows) are not open.

Take the checks in this order; the first that holds gives the class and the ruling:

| Class | Check | Ruling and where it goes |
|---|---|---|
| real and load-bearing, in this task | §5 keeps the finding from `accept` (a `critical`, a safety floor, a blocking finding on a `now` mechanism cell), or `agents/buddy/delegation.md` §Cumulative effort never closes it as a limit (a change-introduced regression, a blocking defect in retained required behaviour or in behaviour the change adds for an acceptance criterion). | The smallest change that removes the outcome, to the caller as the recommendation (for a `now` cell, the Simplify-before-patch gate's proposal). It is never parked or carried to other work. |
| reviewer wrong | The wrong-finding check of `cause-before-answer.md` holds. | Park: `accept`, with the quoted text. |
| real and load-bearing, for later work | A later task or stage names the unit the finding sits on in its `blocked_by` edge, acceptance or spec. | The smallest change that unblocks that work, carried there: a pointer to the entry in that task's file (and a `blocked_by` edge when the change must land first), cited in part 3 of its dispatch; `absorb_next`, or `new_task` when no task holds the work. When no such change can be named, or it would change the approved acceptance or an exclusion: to the caller, as above. |
| real, not load-bearing | None of the above. | Accept with a recorded limit (`cause-before-answer.md`): why nothing builds on it, and its §5 target. |

Each open finding gets one `remaining_findings` entry in the verdict (§5 Risk carry-forward), its rationale starting
with the class; one that goes to the caller is carried as the verdict's ESCALATE with the entry open. A finding on a
mechanism cell placed in another task leaves as that cell's `blocked_by` edge instead (§5 Mechanism-cell floor). None
leaves without one of the two. A ruling Buddy took here or on a push-back goes on the list of decisions taken for the
user when that list's two tests hold (`skills/return_summary/SKILL.md` §Decisions I took for you); the verdict holds
the rest. A workflow-engine retry of the code board step past the engine's iteration cap names this verdict
(`at-the-cap: <verdict path>`; `framework/workflow-engine-cookbook.md` §Iteration cap and review rounds).

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
