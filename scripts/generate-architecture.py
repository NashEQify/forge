#!/usr/bin/env python3
"""
Architecture Documentation Generator for BuddyAI.

Parses SoT (Source of Truth) files and generates mkdocs-compatible
Markdown pages for the architecture documentation.

Sources:
    - agents/*.md (Agent Pool)
    - skills/*/SKILL.md (Skill Registry)
    - skills/{spec_board,code_review_board,ux_review}/SKILL.md (Board Overview)
    - CLAUDE.md (Invariants)

Output:
    - docs/architecture/generated/agent-pool.md
    - docs/architecture/generated/skill-registry.md
    - docs/architecture/generated/board-overview.md
    - docs/architecture/generated/invariants.md

Does NOT regenerate component-status.md (handled by generate-status.py).
"""

from __future__ import annotations

import re
import sys
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"
SKILLS_DIR = ROOT / "skills"
CLAUDE_MD = ROOT / "CLAUDE.md"
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "architecture" / "generated"

# Subdirectories to exclude from agent scanning
AGENT_EXCLUDE_DIRS = {"buddy", "templates"}

# Board SKILL paths for board-overview
BOARD_SKILLS: dict[str, Path] = {
    "Spec Board": SKILLS_DIR / "spec_board" / "SKILL.md",
    "Code Board": SKILLS_DIR / "code_review_board" / "SKILL.md",
    "UX Board": SKILLS_DIR / "ux_review" / "SKILL.md",
}

TODAY = datetime.now(tz=UTC).date().isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_yaml_frontmatter(path: Path) -> dict[str, str]:
    """Parse YAML frontmatter from a Markdown file using regex (no PyYAML needed)."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        warnings.warn(f"File not found: {path}", stacklevel=2)
        return {}

    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    result: dict[str, str] = {}
    current_key: str | None = None
    current_value_lines: list[str] = []

    for line in match.group(1).splitlines():
        # Multi-line continuation (indented or starting with >)
        if current_key and line.startswith(("  ", "\t")):
            current_value_lines.append(line.strip())
            continue

        # Flush previous key
        if current_key:
            result[current_key] = " ".join(current_value_lines).strip()
            current_key = None
            current_value_lines = []

        kv = re.match(r"^(\w[\w-]*):\s*(>?)(.*)$", line)
        if kv:
            current_key = kv.group(1)
            # If value is on same line (not folded scalar)
            value = kv.group(3).strip()
            if value and not kv.group(2):
                result[current_key] = value
                current_key = None
            elif value:
                current_value_lines = [value] if value else []
            else:
                current_value_lines = []

    # Flush last key
    if current_key:
        result[current_key] = " ".join(current_value_lines).strip()

    return result


def first_sentence(text: str) -> str:
    """Extract the first sentence from text."""
    # Split on period followed by space or end of string
    match = re.match(r"(.+?\.)\s", text + " ")
    if match:
        return match.group(1)
    return text.strip()


# ---------------------------------------------------------------------------
# Agent Pool
# ---------------------------------------------------------------------------


@dataclass
class AgentInfo:
    name: str
    role: str
    file: str
    board: str


def classify_agent_board(filename: str) -> str:
    """Classify agent into board based on filename prefix."""
    stem = Path(filename).stem
    if stem.startswith("code-"):
        return "Code Board"
    if stem.startswith("board-ux-"):
        return "UX Board"
    if stem.startswith("board-"):
        return "Spec Board"
    return "Other"


def parse_agents() -> list[AgentInfo]:
    """Parse all agent files and return AgentInfo list."""
    agents: list[AgentInfo] = []

    if not AGENTS_DIR.exists():
        warnings.warn(f"Agents directory not found: {AGENTS_DIR}", stacklevel=2)
        return agents

    for md_file in sorted(AGENTS_DIR.glob("*.md")):
        # Skip README
        if md_file.name.lower() == "readme.md":
            continue

        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            warnings.warn(f"Cannot read: {md_file}", stacklevel=2)
            continue

        lines = text.splitlines()

        # Find first heading line starting with "# Agent"
        agent_name: str | None = None
        for line in lines:
            if line.startswith("# Agent"):
                match = re.search(r":\s*(.+)$", line)
                agent_name = match.group(1).strip() if match else md_file.stem
                break
            if line.startswith("# "):
                agent_name = md_file.stem
                break

        if agent_name is None:
            agent_name = md_file.stem

        # Find first paragraph after the heading (role description)
        role = ""
        in_paragraph = False
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                if in_paragraph:
                    break
                continue
            if stripped.startswith("#"):
                if in_paragraph:
                    break
                continue
            if stripped.startswith(">"):
                # Skip blockquotes (e.g., SUPERSEDED notices)
                continue
            in_paragraph = True
            role += " " + stripped

        role = first_sentence(role.strip()) if role.strip() else "(no description)"

        relative_path = f"agents/{md_file.name}"
        board = classify_agent_board(md_file.name)

        agents.append(
            AgentInfo(
                name=agent_name,
                role=role,
                file=relative_path,
                board=board,
            )
        )

    return agents


def generate_agent_pool(agents: list[AgentInfo]) -> str:
    """Generate agent-pool.md content."""
    board_order = ["Spec Board", "Code Board", "UX Board", "Other"]
    boards: dict[str, list[AgentInfo]] = {b: [] for b in board_order}

    for agent in agents:
        boards.setdefault(agent.board, []).append(agent)

    lines = [
        "# Agent Pool (auto-generated)",
        "",
        "> Auto-generated by `scripts/generate-architecture.py`. Do not edit manually.",
        "",
    ]

    for board_name in board_order:
        board_agents = boards[board_name]
        if not board_agents:
            continue
        n = len(board_agents)
        lines.append(f"## {board_name} ({n} Agent{'s' if n != 1 else ''})")
        lines.append("")
        lines.append("| Agent | Rolle | Datei |")
        lines.append("|-------|-------|-------|")
        for a in sorted(board_agents, key=lambda x: x.name):
            lines.append(f"| {a.name} | {a.role} | {a.file} |")
        lines.append("")

    lines.append(f"*Status: {TODAY}*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Skill Registry
# ---------------------------------------------------------------------------


@dataclass
class SkillInfo:
    name: str
    description: str
    status: str
    path: str


def parse_skills() -> list[SkillInfo]:
    """Parse all SKILL.md files and return SkillInfo list."""
    skills: list[SkillInfo] = []

    if not SKILLS_DIR.exists():
        warnings.warn(f"Skills directory not found: {SKILLS_DIR}", stacklevel=2)
        return skills

    for skill_file in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        fm = parse_yaml_frontmatter(skill_file)
        if not fm:
            warnings.warn(f"No frontmatter in: {skill_file}", stacklevel=2)
            continue

        name = fm.get("name", skill_file.parent.name)
        description = fm.get("description", "(no description)")
        status = fm.get("status", "unknown")
        relative_path = f"skills/{skill_file.parent.name}/SKILL.md"

        skills.append(
            SkillInfo(
                name=name,
                description=first_sentence(description),
                status=status,
                path=relative_path,
            )
        )

    return skills


def generate_skill_registry(skills: list[SkillInfo]) -> str:
    """Generate skill-registry.md content."""
    active = sum(1 for s in skills if s.status == "active")
    archived = sum(1 for s in skills if s.status == "archived")
    other = len(skills) - active - archived

    lines = [
        "# Skill Registry (auto-generated)",
        "",
        "> Auto-generated by `scripts/generate-architecture.py`. Do not edit manually.",
        "",
        "| Skill | Description | Status |",
        "|-------|-------------|--------|",
    ]

    for s in sorted(skills, key=lambda x: x.name):
        lines.append(f"| {s.name} | {s.description} | {s.status} |")

    lines.append("")
    summary_parts = [f"Active: {active}"]
    if archived:
        summary_parts.append(f"Archiviert: {archived}")
    if other:
        summary_parts.append(f"Other: {other}")
    lines.append(" | ".join(summary_parts))
    lines.append("")
    lines.append(f"*Status: {TODAY}*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Board Overview
# ---------------------------------------------------------------------------


def count_agents_per_board(agents: list[AgentInfo]) -> dict[str, int]:
    """Count agents per board."""
    counts: dict[str, int] = {}
    for a in agents:
        counts[a.board] = counts.get(a.board, 0) + 1
    return counts


def generate_board_overview(agents: list[AgentInfo]) -> str:
    """Generate board-overview.md content."""
    board_counts = count_agents_per_board(agents)

    lines = [
        "# Review Boards (auto-generated)",
        "",
        "> Auto-generated by `scripts/generate-architecture.py`. Do not edit manually.",
        "",
        "| Board | Agents | SKILL | Description |",
        "|-------|--------|-------|-------------|",
    ]

    for board_name, skill_path in BOARD_SKILLS.items():
        fm = parse_yaml_frontmatter(skill_path)
        description = first_sentence(fm.get("description", "(not found)"))
        agent_count = board_counts.get(board_name, 0)
        relative_skill = str(skill_path.relative_to(ROOT))

        lines.append(f"| {board_name} | {agent_count} | {relative_skill} | {description} |")

    lines.append("")
    lines.append(f"*Status: {TODAY}*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------


def generate_invariants() -> str:
    """Generate invariants.md from CLAUDE.md."""
    lines = [
        "# Invariants (auto-generated)",
        "",
        "> Extracted from CLAUDE.md. Do not edit manually.",
        "",
    ]

    try:
        text = CLAUDE_MD.read_text(encoding="utf-8")
    except FileNotFoundError:
        warnings.warn(f"CLAUDE.md not found: {CLAUDE_MD}", stacklevel=2)
        lines.append("*CLAUDE.md nicht gefunden.*")
        lines.append("")
        lines.append(f"*Status: {TODAY}. Source: CLAUDE.md*")
        lines.append("")
        return "\n".join(lines)

    # Try to extract the Invarianten section
    md_lines = text.splitlines()
    in_section = False
    invariants: list[str] = []

    for line in md_lines:
        if re.match(r"^## Invarianten", line):
            in_section = True
            continue
        if in_section and re.match(r"^## ", line):
            # Hit next section — stop
            break
        if in_section:
            invariants.append(line)

    # Remove leading/trailing blank lines
    while invariants and not invariants[0].strip():
        invariants.pop(0)
    while invariants and not invariants[-1].strip():
        invariants.pop()

    if invariants:
        lines.extend(invariants)
    else:
        # Fallback: embed entire CLAUDE.md as code block
        warnings.warn("No Invarianten section found in CLAUDE.md, using fallback", stacklevel=2)
        lines.append("```markdown")
        lines.append(text)
        lines.append("```")

    lines.append("")
    lines.append(f"*Status: {TODAY}. Source: CLAUDE.md*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Generate all architecture documentation files."""
    # Support --output-dir for two-site-split (framework site has separate docs_dir)
    output_dir = DEFAULT_OUTPUT_DIR
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--output-dir" and i < len(sys.argv) - 1:
            output_dir = Path(sys.argv[i + 1]).resolve()
        elif arg.startswith("--output-dir="):
            output_dir = Path(arg.split("=", 1)[1]).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    generated_count = 0

    # 1. Agent Pool
    agents = parse_agents()
    agent_pool_content = generate_agent_pool(agents)
    output_path = output_dir / "agent-pool.md"
    output_path.write_text(agent_pool_content, encoding="utf-8")
    print(f"  -> {output_path.relative_to(ROOT)}")
    generated_count += 1

    # 2. Skill Registry
    skills = parse_skills()
    skill_registry_content = generate_skill_registry(skills)
    output_path = output_dir / "skill-registry.md"
    output_path.write_text(skill_registry_content, encoding="utf-8")
    print(f"  -> {output_path.relative_to(ROOT)}")
    generated_count += 1

    # 3. Board Overview (uses agent counts from step 1)
    board_overview_content = generate_board_overview(agents)
    output_path = output_dir / "board-overview.md"
    output_path.write_text(board_overview_content, encoding="utf-8")
    print(f"  -> {output_path.relative_to(ROOT)}")
    generated_count += 1

    # 4. Invariants
    invariants_content = generate_invariants()
    output_path = output_dir / "invariants.md"
    output_path.write_text(invariants_content, encoding="utf-8")
    print(f"  -> {output_path.relative_to(ROOT)}")
    generated_count += 1

    print(f"Generated {generated_count} files in {output_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
