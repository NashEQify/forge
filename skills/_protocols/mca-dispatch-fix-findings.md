# Protocol: MCA dispatch — a fix brief's findings

Step-loaded unit of `skills/_protocols/mca-dispatch.md`. Read it as the implementer before changing code for a fix
brief, and as Buddy before adopting a fix pass's report. It decides how the implementer answers each finding of a
fix brief. The consumers are the implementer and Buddy; the cost it prevents is a briefed change applied without
checking that it removes the outcome and keeps what the touched lines guarantee.

## A fix brief's findings

A fix brief carries, per finding, its verified row (`skills/_protocols/finding-verification.md`: the outcome occurs at
the reviewed bytes) and its cause entry (`skills/_protocols/fix-brief-template.md` §Section 5). The implementer does
not check the row again. It checks the change the brief asks for, since a real outcome can still be given a wrong
change. Per finding, before making its change:

1. Name the row's outcome and the one change the brief asks for. When the brief names no change for the finding, or
   two, the result is `unclear`.
2. Read what the lines that change touches guarantee: their callers, the tests that pin them, the rule or spec item
   the brief cites. Check that the change removes the outcome by the row's route and that each guarantee still holds.
3. Record one result per finding of the brief's Section 5 that this pass fixes, none merged or skipped, in the report
   file under `## Findings received`:

```markdown
| Finding | Result | Evidence | Instead / question |
|---|---|---|---|
| <id> | applied / pushed back / unclear | <applied: the test or command on the changed code that shows the outcome gone (a read only for a change to text no test runs); pushed back: path:lines or command output showing that the brief's change leaves the outcome or breaks a named guarantee> | <pushed back: `nothing`, or the change made instead, the check that shows the outcome gone and its undo; unclear: the question and what each reading would change; applied: `—`> |
```

- **applied:** the brief's change is made, and Evidence names its check. A change that differs from the brief's is
  not `applied`.
- **pushed back:** the brief's change is not made. A change is made instead only inside the brief's scope bound and
  out-of-scope list, with its check and undo; otherwise Instead reads `nothing`.
- **unclear:** no change is made for the finding.

Each finding gets its own result; a `pushed back` or `unclear` row does not stop the others. Each such row makes the
short return's Status `PARTIAL` and is one Concerns line: `<id> pushed back: <evidence>` or `<id> unclear:
<question>`.

## Source

Superpowers (MIT License, © 2025 Jesse Vincent); Forge's register of adopted methods.
