# Spec-amendment discipline — section cross-references

Step-loaded unit of `skills/_protocols/spec-amendment-discipline.md`. Read it when an amendment renames, renumbers
or removes a section or adds a citation of another Markdown file's section, and when the pre-commit
SOURCE-VERIFICATION check warns about one.

### Section cross-references (commit-time WARN)

A citation of another Markdown file's section must resolve in the same
commit. The pre-commit hook checks this on the staged content and warns
under SOURCE-VERIFICATION; it never blocks
(`framework/enforcement-registry.md` §Indexed related-file input). When an
amendment renames, renumbers or removes a section, update the citations of
it in the same commit; when it adds a citation, stage the cited section
with it.

**Supported.** A path to a Markdown file (bare, in backticks or as a link)
followed by a section citation, or an anchor link. The path resolves against
the citing file's directory first, then the repository root, then the one
live Markdown file whose path ends with it (`operational.md` →
`agents/buddy/operational.md`).

| Citation | Resolves when the cited file in the commit has |
|---|---|
| `path.md §9`, `path.md §9.5`, `path.md §3b`, `path.md §1-8` | a heading whose leading number is the cited one (`## 9.`, `### 9.5 Title`, `## §9.5 Title`), or a numbered step or bold label starting with it (`3. **Step**`, `**§0) Label**`); a range `1-8` is read as `1` |
| `path.md §Name` | a label that agrees with Name on its first two words, ignoring case, a trailing plural `s`, a leading `§` or number and emphasis; the two words may be hyphen-joined (`§SOTA-Trigger`) |
| `[text](path.md#anchor)` | a heading whose GitHub anchor is `anchor` |

Labels are headings, bold labels at the start of a line and numbered list
items, anywhere in the cited file, including fenced output templates (those
count for numbers and names, not for anchors). A label is cut at its first
`,` `;` `:` `)` `]` `\|` `<` or backtick, ` —`, ` (`, ` +` or sentence end; a
heading also answers to the text after its first `: ` and to a word with a
digit in its parentheses (`§CHIEF-1` for "Consolidation (CHIEF-1)"). A
one-word heading matches a longer citation that starts with that word, unless
the citation's second word contains a digit (`§Invariant 7` does not resolve
to "Invariants"; cite a numbered section by its number, `framework/invariants.md §3`); a
one-word bold label or list item matches only a one-word citation. The cited
name is cut at the same characters.

**Reported.** Citations in a file the commit changes, and citations of a file
the commit changes, renames or deletes:

- no such section or anchor in the staged cited file, including a section that
  exists only in the working tree;
- `target file missing in candidate`: the commit deletes or renames the cited
  file;
- `target file not staged`: the cited file exists only in the working tree, or
  was added with `git add -N`.

A staged citation that resolves stays valid whatever the working tree holds.
At most 20 warning lines are printed, with a count of the rest; the
`INDEXED-STANDALONE` record lists up to 200.

**Not checked.**

- A path found nowhere in the commit and not covered above: a short path that
  matches several files (`SKILL.md`) or none, a mistyped path, a file in
  another repository.
- A cited path that is a link or runs through one, a path inside a submodule,
  and a path starting with `/`.
- Frozen zones, records and logs: `docs/tasks/archive/`,
  `context/history/`, `docs/decisions/`, `docs/build/`, `docs/fix/`,
  `docs/review/`, `docs/reviews/`, `docs/research/`, `docs/audit/`,
  `docs/audits/`, `docs/solve/`, `docs/handovers/`, `docs/docs-rewrite/`,
  `docs/discoveries/`, `docs/dogfood-learnings/`; test data in
  `tests/fixtures/`; derived skill copies in `.claude/skills/synced/`. A
  short path is not looked up among these files either; a full path still
  reaches them.
- Lines longer than 4,000 characters.
- Quoted examples: fenced code blocks, `>` quote lines, and citations inside
  inline code, like the examples above. HTML comments and indented code blocks
  are read like prose.
- Citations without a file path (`§9.5`, "the public §9.6").
- Citations in YAML, code or other non-Markdown files.
- Version references (`v1.3`, `spec_version`) and references to other
  repositories.
- Whether the cited section says what the citing text claims; that stays
  with `spec_amendment_verification` and review.

---
