# Codex execution boundaries

Codex host adaptation for Buddy and delegated writers. Apply this before invoking
commands, including the boot freshness helper. Consumer authorization and the
host's effective permissions remain separate requirements.

## Instruction output

Follow `framework/work-principle.md`'s instruction-loading contract before using a
read result. On Codex, `exec_command.max_output_tokens` and an enclosing
`functions.exec` response budget are separate limits: complete inner command results
can still be clipped in the outer response. Keep instruction text out of responses
that also dump task context, tool logs or search results. Size independent reads
against their combined returned output, or return them separately. Check the actual
outer result for every requested unit/range and recover omissions before dependent
work; exit code 0 and raw command telemetry are not loading receipts.

## Git reads and writes

In Codex `workspace-write`, a writable project may still have a read-only `.git`.
This includes `.git` pointer files and their resolved Git directories in linked
worktrees. Trust the effective permissions supplied by the host; filesystem mode
bits and a trusted-project setting do not override a protected mount.

- Run read-only queries (`git log`, `diff`, `show`, `rev-parse`, `ls-remote`) in the
  normal sandbox when permitted. Use `GIT_OPTIONAL_LOCKS=0 git status` to avoid an
  optional index refresh; network reads may separately need host approval.
- For an **already authorized** operation that writes protected Git metadata,
  call `exec_command` with `sandbox_permissions="require_escalated"` directly when
  that route is offered. Do not make a predictably denied sandbox attempt first.
  This includes `fetch`, `pull`, `add`, `commit`, `push`, and helpers that invoke
  them, notably `scripts/git-status-check.sh`. A push can update tracking refs.
- Keep requests scoped to the concrete command and repository. Supply the host's
  required justification. If using `prefix_rule`, choose a narrow stable prefix
  such as `["git", "pull"]`; never propose a blanket `["git"]` or shell prefix.
  Keep independent reads separate from the escalated command. Helpers cannot
  choose their own tool permissions: the caller escalates the helper invocation.

This selects the supported approval route; it grants no new substantive authority.
A fetch permission is not permission to pull, publish, reset or switch branches.
Commit and push follow the request and applicable standing user/project rules;
a commit-only or implementation-only scope must not silently become publication.
Preserve foreign staged work, inspect the whole outgoing range before a push, and
retain hooks and any explicit branch or live-operation limits.

## Denials and verification

Auto-review may approve a justified request without a human prompt. It can also
reject it; `require_escalated` does not guarantee access. If escalation is unavailable
or denied, stop that operation and report the concrete command, host boundary and
actual outcome. Do not repeatedly submit the same rejected request or re-ask an
already answered substantive permission. If automatic approval rejects the action
and no safer authorized alternative can complete it, identify that rejection and
its stated reason and request user approval for the concrete blocked operation.
A materially safer, still-authorized
alternative can proceed through the host's offered tools.

Do not weaken the sandbox, add writable-root exceptions, relocate Git metadata,
change permissions, use sudo or install broad allow rules to defeat the boundary.
A shell/Git alias cannot supply an `exec_command` permission setting.

A failed fetch means remote freshness is unknown; ahead/behind values from cached
refs remain useful only with that qualification. Empty status output alone proves
no successful online check. Verify the actual result after approved writes; after
an authorized push compare the intended local commit with the intended remote ref.

Host reference: [OpenAI agent approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security).
This is an instruction protocol, not an app configuration change or an automatic
retry hook. Activate shared source/integration changes through
[installation activation](../../framework/installation-activation.md).
