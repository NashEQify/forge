#!/usr/bin/env python3
"""generate_agent_skill_map.py — Agent ↔ Skill awareness generator.

Produces two outputs from frontmatter `relevant_for:` lists in
`skills/**/SKILL.md`:

1. AUTO-block in each `agents/<name>.md` — gives spawned sub-agents a
   curated, minimal skill-pointer-list. Markers:
       <!-- AGENT-SKILLS-AUTO-START -->
       ...
       <!-- AGENT-SKILLS-AUTO-END -->

2. Aggregate `framework/agent-skill-map.md` — canonical reverse-map for
   humans + maintenance.

Schema (skill frontmatter, optional):

    relevant_for: ["main-code-agent", "tester"]   # explicit list
    relevant_for: ["*"]                            # wildcard — all agents
    relevant_for: []                               # not auto-injected
    # field absent                                 # not auto-injected

Wildcard `*` injects the skill into ALL agent .md files that have the
AUTO-block markers (opt-in per agent — agent file must contain the markers
to participate).

Usage:
    python3 generate_agent_skill_map.py            # write
    python3 generate_agent_skill_map.py --check    # exit 1 on drift
    python3 generate_agent_skill_map.py --agent main-code-agent  # subset

Drift-detection (pre-commit Check 10): runs --check, WARNs on diff.

Pattern follows generate_skill_map.py + generate_navigation.py
(Generator+Validator, drift-anfaellige Indizes mechanisch generiert).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required", file=sys.stderr)
    sys.exit(2)

AUTO_START = "<!-- AGENT-SKILLS-AUTO-START -->"
AUTO_END = "<!-- AGENT-SKILLS-AUTO-END -->"
AGGREGATE_START = "<!-- AGENT-SKILL-MAP-AUTO-START -->"
AGGREGATE_END = "<!-- AGENT-SKILL-MAP-AUTO-END -->"


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / "framework").is_dir() and (parent / "agents").is_dir():
            return parent
    return start.resolve()


def parse_frontmatter(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


def collect_skills(root: Path) -> list[tuple[str, str, list[str]]]:
    """Returns list of (dir_name, description, relevant_for_list).

    Path-component is dirname (underscored, matches actual disk-layout).
    Excludes _archived, _protocols, _references — those are categorical
    not standalone skills.
    """
    out: list[tuple[str, str, list[str]]] = []
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return out
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        rel = skill_md.relative_to(root).as_posix()
        if any(seg in rel for seg in ("/_archived/", "/_protocols/", "/_references/")):
            continue
        data = parse_frontmatter(skill_md)
        if not data:
            continue
        # Use directory name for path-stability — name field can be
        # hyphenated while dir is underscored (validator normalizes both).
        dir_name = skill_md.parent.name
        desc = (data.get("description") or "").strip()
        # Compact description to one line, max 140 chars
        desc = re.sub(r"\s+", " ", desc)
        if len(desc) > 140:
            desc = desc[:137] + "..."
        rel_for = data.get("relevant_for")
        if not isinstance(rel_for, list):
            continue
        rel_for = [str(x).strip() for x in rel_for if str(x).strip()]
        if not rel_for:
            continue
        out.append((dir_name, desc, rel_for))
    return out


def known_agents(root: Path) -> set[str]:
    """Set of agent names by .md filename in agents/ (excluding README, navigation)."""
    agents_dir = root / "agents"
    out: set[str] = set()
    if not agents_dir.is_dir():
        return out
    for md in agents_dir.glob("*.md"):
        stem = md.stem
        if stem in ("README", "navigation"):
            continue
        out.add(stem)
    return out


def agents_for_skill(rel_for: list[str], all_agents: set[str]) -> set[str]:
    """Resolve relevant_for list to concrete agent names, expanding wildcard."""
    if "*" in rel_for:
        return set(all_agents)
    return {a for a in rel_for if a in all_agents}


def build_block_for_agent(
    agent: str, skills: list[tuple[str, str, list[str]]], all_agents: set[str]
) -> str:
    """Compose AUTO-block content for one agent."""
    rows: list[tuple[str, str]] = []
    for name, desc, rel_for in skills:
        if agent in agents_for_skill(rel_for, all_agents):
            rows.append((name, desc))
    rows.sort(key=lambda x: x[0])
    lines = [
        AUTO_START,
        "## Relevant Skills (auto-generated)",
        "",
        "Generated by `scripts/generate_agent_skill_map.py` from skill",
        "frontmatter `relevant_for:`. Do NOT edit between the markers — "
        "rerun the generator. Methodology SoT: `framework/skill-map.md`.",
        "",
    ]
    if not rows:
        lines.append("*(no skills tagged `relevant_for: [\"" + agent + "\"]` yet)*")
    else:
        for name, desc in rows:
            path = f"skills/{name}/SKILL.md"
            if desc:
                lines.append(f"- `{path}` — {desc}")
            else:
                lines.append(f"- `{path}`")
    lines.append("")
    lines.append(AUTO_END)
    return "\n".join(lines)


def update_agent_file(agent_path: Path, new_block: str) -> tuple[bool, bool]:
    """Returns (changed, has_markers). If markers missing → no-op (opt-in)."""
    text = agent_path.read_text(encoding="utf-8")
    if AUTO_START not in text or AUTO_END not in text:
        return (False, False)
    pattern = re.compile(
        re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END),
        re.DOTALL,
    )
    new_text = pattern.sub(new_block, text)
    if new_text == text:
        return (False, True)
    agent_path.write_text(new_text, encoding="utf-8")
    return (True, True)


def check_agent_file(agent_path: Path, expected_block: str) -> bool:
    """True if drift detected (file differs from expected)."""
    text = agent_path.read_text(encoding="utf-8")
    if AUTO_START not in text or AUTO_END not in text:
        return False  # opt-in: no markers = no participation
    pattern = re.compile(
        re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END),
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return True
    return m.group(0) != expected_block


def build_aggregate_map(
    skills: list[tuple[str, str, list[str]]], all_agents: set[str]
) -> str:
    """framework/agent-skill-map.md content (aggregate reverse-map)."""
    # Per-agent table
    by_agent: dict[str, list[tuple[str, str]]] = {a: [] for a in sorted(all_agents)}
    wildcard_skills: list[tuple[str, str]] = []
    for name, desc, rel_for in skills:
        if "*" in rel_for:
            wildcard_skills.append((name, desc))
            continue
        for ag in rel_for:
            if ag in by_agent:
                by_agent[ag].append((name, desc))

    lines = [
        AGGREGATE_START,
        "# Agent ↔ Skill Map (auto-generated)",
        "",
        "Reverse map of skill `relevant_for:` frontmatter — which skills each",
        "agent should know about when spawned. SoT: skill frontmatter.",
        "Regenerate via `scripts/generate_agent_skill_map.py`. Pre-commit",
        "Check 10 (AGENT-SKILL-DRIFT) detects out-of-date AUTO-blocks.",
        "",
        "Agent-Definitionen (`agents/<name>.md`) participate via",
        f"`{AUTO_START}` / `{AUTO_END}` markers — opt-in per agent.",
        "",
    ]

    if wildcard_skills:
        lines.append("## Wildcard (`relevant_for: [\"*\"]`)")
        lines.append("")
        lines.append("Injected into ALL participating agent definitions:")
        lines.append("")
        for name, desc in sorted(wildcard_skills):
            short = desc if len(desc) <= 80 else desc[:77] + "..."
            lines.append(f"- `{name}` — {short}" if short else f"- `{name}`")
        lines.append("")

    lines.append("## Per-Agent")
    lines.append("")
    for agent in sorted(by_agent.keys()):
        rows = sorted(by_agent[agent])
        if not rows:
            continue
        lines.append(f"### `{agent}`")
        lines.append("")
        for name, desc in rows:
            short = desc if len(desc) <= 80 else desc[:77] + "..."
            lines.append(f"- `{name}` — {short}" if short else f"- `{name}`")
        lines.append("")

    lines.append(AGGREGATE_END)
    return "\n".join(lines)


def update_aggregate_file(agg_path: Path, new_content: str) -> bool:
    """Write aggregate map. Returns True if changed."""
    if agg_path.exists():
        existing = agg_path.read_text(encoding="utf-8")
    else:
        existing = ""
    if existing == new_content:
        return False
    agg_path.parent.mkdir(parents=True, exist_ok=True)
    agg_path.write_text(new_content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 on drift instead of writing (pre-commit mode)",
    )
    parser.add_argument(
        "--agent",
        help="Only process this agent (for testing)",
    )
    parser.add_argument(
        "--root",
        help="Repo root (default: auto-detect)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else repo_root(Path.cwd())

    skills = collect_skills(root)
    all_agents = known_agents(root)
    if args.agent:
        all_agents = {args.agent} & all_agents
        if not all_agents:
            print(f"ERROR: agent '{args.agent}' not found in agents/", file=sys.stderr)
            return 2

    drift_files: list[str] = []
    written: list[str] = []
    skipped_no_markers: list[str] = []

    for agent in sorted(all_agents):
        agent_path = root / "agents" / f"{agent}.md"
        if not agent_path.exists():
            continue
        block = build_block_for_agent(agent, skills, all_agents)
        if args.check:
            if check_agent_file(agent_path, block):
                drift_files.append(str(agent_path.relative_to(root)))
        else:
            changed, has_markers = update_agent_file(agent_path, block)
            if not has_markers:
                skipped_no_markers.append(str(agent_path.relative_to(root)))
            elif changed:
                written.append(str(agent_path.relative_to(root)))

    # Aggregate map (only when not --agent-scoped)
    if not args.agent:
        agg_path = root / "framework" / "agent-skill-map.md"
        agg_content = build_aggregate_map(skills, known_agents(root))
        if args.check:
            existing = agg_path.read_text(encoding="utf-8") if agg_path.exists() else ""
            if existing != agg_content:
                drift_files.append(str(agg_path.relative_to(root)))
        else:
            if update_aggregate_file(agg_path, agg_content):
                written.append(str(agg_path.relative_to(root)))

    if args.check:
        if drift_files:
            print(f"DRIFT: {len(drift_files)} file(s) need regeneration:")
            for f in drift_files:
                print(f"  {f}")
            print("")
            print("Run: python3 scripts/generate_agent_skill_map.py")
            return 1
        print("CLEAN: agent-skill-map up to date")
        return 0

    if written:
        print(f"WROTE: {len(written)} file(s)")
        for f in written:
            print(f"  {f}")
    else:
        print("CLEAN: no changes")
    if skipped_no_markers:
        print(
            f"\nSKIPPED (no AUTO-block markers): {len(skipped_no_markers)} agent file(s)"
        )
        print("To opt in, add these markers to the agent file (anywhere in body):")
        print(f"  {AUTO_START}")
        print(f"  {AUTO_END}")
        for f in skipped_no_markers[:5]:
            print(f"  - {f}")
        if len(skipped_no_markers) > 5:
            print(f"  ... +{len(skipped_no_markers) - 5} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
