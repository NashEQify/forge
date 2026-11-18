# Evidence pointer schema — integrations

Step-loaded unit of `skills/_protocols/evidence-pointer-schema.md`. Read it when changing the pointer format or one
of its consumers (reviewer protocols, engine check, validator, pre-commit check). Section numbers are protocol-wide: §1–§5 in `evidence-pointer-schema.md`, §6–§7 in
`evidence-pointer-integrations.md`, §8 in `evidence-author-claims.md`, §9–§9.3 in `evidence-review-capture.md`, §9.4–§9.6
in `evidence-review-adoption.md`.

## 6. Reviewer-output-protocol migration

Three live files (edit locations documented in
`docs/specs/299-fabrication-mitigation.md` §1.6):

- `agents/_protocols/spec-reviewer-protocol.md` — output-format
  block.
- `agents/_protocols/code-reviewer-protocol.md` — output-format
  block.
- `agents/_protocols/ux-reviewer-protocol.md` — output-format
  block.

In all three: the `evidence:` prose field is replaced by the
pointer list (per-finding layout).

`agents/_protocols/reviewer-base.md` is extended with the
output-frontmatter requirement: `schema_version: 1` MUST appear in
the output frontmatter.

---

## 7. Cross-references

- Spec: `docs/specs/299-fabrication-mitigation.md`
- Engine check: `scripts/workflow_engine.py` `check_completion`
  `pointer_check`
- yaml_loader: `scripts/lib/yaml_loader.py`
  `VALID_COMPLETION_TYPES` + `_validate_completion`
- Validator: `scripts/validate_evidence_pointers.py`
- Pre-commit Check 5 SOURCE-VERIFICATION:
  `orchestrators/claude-code/hooks/pre-commit.sh`

---
