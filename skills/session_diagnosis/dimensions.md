# Session diagnosis — reading, dimensions, report

Step-loaded unit of `skills/session_diagnosis/SKILL.md`. Read §Reading a transcript at step 2 before opening any
session file, §Dimensions at step 4 (an analyst reads it whole), and §Report and §Shared copy at step 7.

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.

## Reading a transcript

- **Where:** the host keeps the transcripts. Claude Code writes `~/.claude/projects/<working-directory slug>/
  <session-id>.jsonl` and the subagents' under `<session-id>/subagents/`; Codex writes under `~/.codex/sessions/`.
  Verify each path on disk; a host may change its layout. A resumed session can continue in a new file: take every
  file of the session. A large tool result can be stored beside the transcript (Claude Code:
  `<session-id>/tool-results/`, named in a `persisted-output` record): follow it before judging that result.
- **Measure first:** `wc -lc <file>`, and the long lines (`awk 'length($0) > 100000 {print NR, length($0)}'`).
- **Never print a record whole:** get line numbers and counts first (`grep -n … | cut -d: -f1`,
  `jq -r '.type' | sort | uniq -c`), then small fields from one line (`sed -n <N>p <file> | jq -c '{…}' | cut -c1-500`).
  Narrow any output over 500 characters per record.
- **Whose words:** the user's prompts are the records the host marks as typed by the person. A host's stored
  transcript keeps a headless prompt as such a record; a captured output stream (`--output-format stream-json`)
  does not, so take the prompt from the launch command. In a subagent transcript, "user" is the parent agent.
- **Record meanings:** establish them from the records in front of you (`jq -r '.type' | sort | uniq -c`), not
  from another host's format. A headless stream (`--output-format stream-json`) carries no timestamps: take
  durations from its result record and say so.
- **Hidden reasoning:** a host may record thinking without its text. Then the agent's reasons are readable only where
  it wrote them out; say so in coverage.
- **Read-only:** never write, move or delete a session file.

## Analyst return

```
## <Dimension> findings

- finding: <one sentence, what happened>
  evidence: <absolute path>:<line> — "<quote, at most 200 characters>"
  turns: <first>–<last>
  confidence: high | medium | low

Checked: <files, line ranges, commands>
```

Nothing found: `- none found` and the Checked line. A finding without `path:line` is dropped.

## Dimensions

Report what the records show; do not judge whether a choice was right.

1. **Process timeline.** Per user turn: skills invoked, workflows started, agents dispatched, Forge files read. A turn
   whose request matches a skill's description as the session saw it (the transcript's skill-listing records;
   without them, the framework root at the session's revision, or today's text marked as such) with no invocation in
   that turn (quote both); an invocation turns
   after its request; other plugins, skills, servers or hooks used.
2. **Plan adherence.** The agreed course: a plan the user approved in chat, a brief, the approved acceptance, a task
   list. Per step: executed, skipped, out of order, changed without saying so, or work no step covers. Drift right
   after a compaction, resume or aborted turn is its own finding.
3. **Repeated work.** The same read or search three times or more, the same edit or shell command twice (status
   checks and test runs exempt), the same dispatch twice; whether something changed in between (a write, a
   compaction, the user's correction). A decision reached again that the session had already stated.
4. **Stumbles.** Tool errors, failed commands, retries, reverted edits, backtracking in the agent's text, the user
   correcting the previous action, permission denials, hook failures, rate limits, compactions mid-task; and where
   each recovered, or that it did not.
5. **Quality evidence.** Test runs and their results; completion claims without the evidence their row requires
   (`skills/_protocols/evidence-author-claims.md` §8.5) at the claim's position, such as a run after the last edit
   to the covered paths; commit messages against the work done; review
   points acknowledged but not acted on; each acceptance line met, not met or not checked.
6. **Request conflicts.** The user's instructions against each other, against the instruction files loaded, and
   against the injected boot entry; an instruction to skip a step or rule, and what followed; a clarification that
   changed scope.
7. **Cost and time.** From usage records only, with each counter's meaning stated (per turn or cumulative): turns,
   tokens, the largest turns, gaps over ten minutes, the largest tool results, compactions, each subagent's share.
   No price from memory.

## Report

1. **Problem statement**, as agreed in step 1.
2. **Load check:** the verdict and its three evidence points.
3. **Verdict:** the layer from the load check and the dimensions (installation, instruction loading, session
   outcome, none shown, or not separated) and what the evidence shows,
   with a citation after every claim and a confidence (high, medium, low) with what would raise it.
4. **Environment:** Forge revision (the framework root's Git, or unknown), install profile and method, host and
   version, model(s), instruction files present; each marked as read from the transcript, observed now, or unknown.
5. **Sessions examined:** role, id, absolute path, lines, bytes; rejected candidates with the reason.
6. **Findings**, one subsection per dimension in the order above.
7. **Baseline question:** does the problem occur without Forge? The cited answer, or the run that would answer it.
8. **Coverage:** what was not read and why, whether the session was still running, what the user should check.

## Shared copy

A report that leaves the user's machine (a Forge report, an independent trial) is a copy prepared for it:
- the home directory becomes `~`;
- user and host names, email addresses, organization, account and session ids, tokens, keys and passwords become
  placeholders (`<user>`, `<session-A>`);
- the user's own prompts are paraphrased, unless the user approves the exact quote;
- a quote of tool output stays only where its finding needs it, after the same replacements.

The user reads the copy before it goes anywhere. The transcript itself stays on the user's machine.
