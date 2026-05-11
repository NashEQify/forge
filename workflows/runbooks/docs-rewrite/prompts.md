# docs-rewrite — Agent Prompts

Prompt cores for the research agent (Phase Research) and the writer agent (Phase Write).
The Buddy-facing `WORKFLOW.md` is the checklist; this file is the reference
for the full prompt texts.

## Research-agent prompt (Phase Research)

**Agent:** CC subagent_type `Explore` (thoroughness: very thorough)
**Output:** research document ~1500-2500 words

```
You are a research agent for a documentation rewrite.

GOAL: Extract from the repo the design decisions, workflows,
architecture principles and technologies that cover {content_goal}.

NOT: list files or describe components.
INSTEAD: why was it built this way? Which alternatives were rejected?
What are the first principles?

ENTRY POINTS (read these first, then follow the references):
{entry_points}

OUTPUT FORMAT:
## Design decisions (the most important 5-8, each with "Problem -> Solution -> Why")
## Workflows (how does work flow through the system, end-to-end)
## Architecture principles (the invariants, the mindset, the pattern)
## Technology decisions (what, why, what not)
## Key tensions (where are the deliberate trade-offs)

Back every claim with a source file.
```

### Entry points (Buddy populates before dispatch)

- **Always:** `intent.md` (vision), `CLAUDE.md` (invariants), `framework/process-map.md` (workflows)
- **For framework rewrite:** `docs/tasks/273.md` (design decisions),
  `framework/agentic-design-principles.md`, workflow runbooks
- **For product rewrite:** `docs/architecture/ARCHITECTURE.md`, specs, container atlas
- Buddy derives the entry points from `scope` + `reason`. No heuristic —
  from known context.

---

## Writer-agent prompt (Phase Write)

**Agent:** CC subagent_type `general-purpose` (1 spawn per page, parallel where possible)
**NOT MCA** — doc pages are not code, MCA expects delegation artefacts
(intent_chain, spec, test plan) which do not exist here.
**Output:** finished markdown page as a file in `docs/architecture/framework/`

```
Write the page "{title}" for the BuddyAI framework documentation.
Write the finished page to: {file_path}

CORE QUESTION this page answers: {core_question}

CONTENT POINTS (from research, this is your material):
{content_points}

READER: {persona_context}

WRITING GUIDELINES:
- Explain WHY, not WHAT. "We use X" is worthless. "We use X because Y,
  and not Z because W" is page-worthy.
- Reduce to first principles. What is the pattern BEHIND the mechanism?
- Concrete examples > abstract descriptions.
- Mermaid diagrams where they make the flow clearer than text.
- Max {max_lines} lines. If you need more: the page is too broad,
  split the scope.
- SoT references at the end (which repo files are the truth for this page).
- Language: English (working language of the framework site).

DO NOT:
- list files ("there is agents/board-adversary.md, agents/board-chief.md...")
- describe components without context
- marketing speak
- redundancy with other pages (your page is ONE page in a set —
  {neighbour_pages})
```

### Parallelisation

- Pages without dependencies: spawn in parallel
- Pages with a dependency: sequential

## References

| Topic | SoT |
|---|---|
| Runbook (phases + gates) | `WORKFLOW.md` |
| CC subagents | Built-in Claude Code |
| UX review (Phase Review) | `skills/spec_board/SKILL.md` (`mode=ux`) |
