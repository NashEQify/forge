# Protocol: Content Preservation

Prevents accidental deletion of valuable spec/code content during
fixes.
Referenced by: spec_board, code_review_board, sectional_deep_review.

## Rule

When a finding recommends REMOVING or REPLACING content, the fixing
agent (MCA) checks before the edit:

1. Does the old content have standalone value? (Illustrative code,
   pattern documentation, examples that aid understanding.)
2. Is the finding a violation (wrong signature, re-declaration) or
   a content problem?
3. If both: fix the violation, preserve the content. Don't delete
   everything.

## Application

**Spec content** is documentation — it exists so an implementer
understands what to build. "Remove this code block" is only correct
when the block is WRONG or copies a FOREIGN signature.

**Code content:** findings recommending REMOVAL ("dead code",
"redundant", "unused") → MCA checks whether the code has a
defensive, documentary, or fallback purpose. Defensive code
(timeout guards, fallback paths, degradation checks) is not
removed merely because the happy path doesn't exercise it.

## Proof output

MCA documents in the return summary:
`Content preservation: checked (N removals reviewed, M preserved
because {reason})`. Without this line for removals → chief flags
F-C-CONTENT-MISSING. With zero removals in the fix:
`Content preservation: n/a (no removals)`.

## Boundary

Detail + boundary table: `docs/specs/interface-contract.md` S-001.
Overall stance: mechanical removal without a content recheck is
substance loss. This protocol is the mechanical gate for that — not
a CLAUDE.md invariant, but anchored here.
