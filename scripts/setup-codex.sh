#!/usr/bin/env bash
# setup-codex.sh — Setup fuer Codex Desktop / Codex CLI as forge runtime.
#
# What it does:
#   1. Detects FRAMEWORK_DIR from this script's location.
#   2. Installs forge Codex agent wrappers into ~/.codex/agents.
#   3. Writes a Codex-specific Buddy wrapper with concrete FRAMEWORK_DIR.
#   4. Writes a small global ~/.codex/AGENTS.md fallback.
#   5. Installs forge skill wrappers into ~/.agents/skills.
#   6. Generates project-local .codex/hooks.json for each given project path.
#
# Usage:
#   bash $FRAMEWORK_DIR/scripts/setup-codex.sh [project-dir ...]
#
# If no project dir is passed, only the global Codex agent setup is performed.
#
# Secrets:
#   This script never writes passwords or secret values. Secrets stay in SOPS
#   (sysadmin: infra/secrets/*.sops.yaml) and are intentionally out of scope.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
FRAMEWORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
AGENTS_HOME="${AGENTS_HOME:-$HOME/.agents}"
AGENTS_SOURCE="$FRAMEWORK_DIR/.codex/agents"
AGENTS_TARGET="$CODEX_HOME/agents"
SKILLS_TARGET="$AGENTS_HOME/skills"

if [ ! -f "$FRAMEWORK_DIR/agents/buddy/boot.md" ] || [ ! -f "$FRAMEWORK_DIR/framework/boot-navigation.md" ]; then
  echo "FEHLER: $FRAMEWORK_DIR sieht nicht nach forge aus (Buddy boot/navigation fehlt)." >&2
  exit 1
fi

if [ ! -d "$AGENTS_SOURCE" ]; then
  echo "FEHLER: Codex agents source missing: $AGENTS_SOURCE" >&2
  exit 1
fi

mkdir -p "$AGENTS_TARGET"

# Copy all generated wrappers first; Buddy is overwritten below with a
# Codex-specific concrete-FRAMEWORK_DIR wrapper.
find "$AGENTS_SOURCE" -maxdepth 1 -type f -name '*.toml' -print0 |
  while IFS= read -r -d '' file; do
    cp "$file" "$AGENTS_TARGET/$(basename "$file")"
  done

cat > "$AGENTS_TARGET/buddy.toml" <<EOF
name = "buddy"
description = "Primary orchestrator and user-facing agent of the forge framework. Handles intake gating, spec interviews, dispatch to board/council/main-code-agent, context maintenance, and session bookkeeping."
developer_instructions = """
You are Buddy.

This file is the Codex wrapper for the tool-neutral Buddy definition that
lives in the forge framework. The source-of-truth content is there, not here.
Do not encode personality, rules, or routing logic in this wrapper beyond
Codex bootstrapping.

## Boot sequence — execute BEFORE responding to the user

Concrete framework root for this Codex setup:

$FRAMEWORK_DIR

On your first turn, read these three files by absolute path:

1. $FRAMEWORK_DIR/agents/buddy/soul.md — personality, role, principles
2. $FRAMEWORK_DIR/agents/buddy/operational.md — phases, gates, delegation
3. $FRAMEWORK_DIR/agents/buddy/boot.md — session-start routing

Then follow boot.md: ORIENT, RESOLVE, ROUTE, LOAD, STATUS-CHECK, RESUME,
GREET. Use absolute paths for framework and personal-context reads.

Mental model: Codex repository instructions come from AGENTS.md. Relative file
paths resolve against the session CWD, not against the framework root. Consumer
repos such as BuddyAI do not have a local agents/buddy/ framework tree.

## Project rules

Codex loads the active repository's AGENTS.md. Treat that file as the project
Tier-0 instruction surface for Codex. If it conflicts with this wrapper, the
project AGENTS.md wins.
"""
EOF

cat > "$CODEX_HOME/AGENTS.md" <<EOF
# Global Codex Fallback

Use the active repository's AGENTS.md as the project instruction source.

For forge/Buddy projects, the installed Buddy agent wrapper points at:
$FRAMEWORK_DIR

Do not put secrets here. Passwords and deploy secrets stay in SOPS-managed
sysadmin files.
EOF

echo "codex agents: $AGENTS_TARGET (from $AGENTS_SOURCE)"
echo "buddy wrapper: $AGENTS_TARGET/buddy.toml (FRAMEWORK_DIR=$FRAMEWORK_DIR)"
echo "global AGENTS: $CODEX_HOME/AGENTS.md"

python3 "$FRAMEWORK_DIR/scripts/generate_skill_wrappers.py" \
  --repo "$FRAMEWORK_DIR" \
  --output-root "$SKILLS_TARGET" \
  --tool-label Codex
echo "codex skills: $SKILLS_TARGET (generated from $FRAMEWORK_DIR/skills)"

write_project_hooks() {
  local project_dir="$1"
  local target_dir="$project_dir/.codex"
  local target="$target_dir/hooks.json"

  if [ ! -d "$project_dir" ]; then
    echo "WARNUNG: project dir not found, skipping hooks: $project_dir" >&2
    return 0
  fi

  mkdir -p "$target_dir"
  cat > "$target" <<EOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|NotebookEdit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/path-whitelist-guard.sh",
            "timeout": 3
          }
        ]
      },
      {
        "matcher": "Edit|Write|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/frozen-zone-guard.sh",
            "timeout": 3
          },
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/state-write-block.sh",
            "timeout": 3
          },
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/engine-bypass-block.sh",
            "timeout": 3
          },
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/plan-adversary-reminder.sh",
            "timeout": 3
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/workflow-commit-gate.sh",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/delegation-prompt-quality.sh",
            "timeout": 3
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/mca-return-stop-condition.sh",
            "timeout": 3
          },
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/board-output-check.sh",
            "timeout": 3
          },
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/evidence-pointer-check.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash $FRAMEWORK_DIR/orchestrators/claude-code/hooks/workflow-reminder.sh",
            "timeout": 3
          }
        ]
      }
    ]
  }
}
EOF
  echo "project hooks: $target"
}

for project_dir in "$@"; do
  write_project_hooks "$(cd "$project_dir" && pwd)"
done

if command -v codex >/dev/null 2>&1; then
  echo "codex: $(command -v codex) ($(codex --version 2>/dev/null || true))"
else
  echo "WARNUNG: codex CLI nicht im PATH." >&2
fi

echo ""
echo "Usage:"
echo "  codex   # from a repo with AGENTS.md"
echo "  Codex Desktop reads ~/.codex/agents, ~/.agents/skills, and project .codex/hooks.json"
