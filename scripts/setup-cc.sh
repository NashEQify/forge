#!/usr/bin/env bash
# setup-cc.sh — Setup fuer den cc-Launcher (Claude Code) und path-whitelist.
#
# Was es tut:
#   1. Erkennt FRAMEWORK_DIR aus eigenem Standort.
#   2. Kopiert orchestrators/claude-code/bin/cc nach ~/.local/bin/cc
#      (cc detektiert FRAMEWORK_DIR ohnehin selbst — Kopie ist fuer PATH).
#   3. Generiert .claude/path-whitelist.txt aus .example (substituiert
#      ${FRAMEWORK_DIR} und ${HOME}).
#   4. Pruefe Symlinks ~/.claude/agents und ~/.claude/skills (cc legt sie
#      ebenfalls idempotent an, hier nur Info-Output).
#
# Usage: bash $FRAMEWORK_DIR/scripts/setup-cc.sh
#
# Voraussetzungen:
#   - claude CLI installiert (`claude --version`)
#   - ~/.local/bin/ im PATH

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
FRAMEWORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="$HOME/.local/bin"
INSTALL_PATH="$INSTALL_DIR/cc"

# --- Checks ---
if [ ! -f "$FRAMEWORK_DIR/CLAUDE.md" ]; then
  echo "FEHLER: $FRAMEWORK_DIR sieht nicht nach forge aus (kein CLAUDE.md)." >&2
  exit 1
fi

if ! command -v claude &>/dev/null; then
  echo "WARNUNG: 'claude' nicht im PATH. Installiere Claude Code zuerst." >&2
  echo "         https://docs.anthropic.com/en/docs/claude-code" >&2
fi

# --- Install cc launcher ---
mkdir -p "$INSTALL_DIR"
SOURCE="$FRAMEWORK_DIR/orchestrators/claude-code/bin/cc"
if [ ! -f "$SOURCE" ]; then
  echo "FEHLER: $SOURCE nicht gefunden." >&2
  exit 1
fi

# cc autodetects FRAMEWORK_DIR from $0 location, but the install copy under
# ~/.local/bin/ would resolve $0/../../.. to /home (wrong). Substitute the
# install-time absolute path into FRAMEWORK_DIR_INSTALLED so the installed
# copy carries its own canonical FRAMEWORK_DIR. Always re-write — content is
# deterministic, no idempotency concern.
sed "s|^FRAMEWORK_DIR_INSTALLED=\"\"  # SUBSTITUTED-BY-SETUP-CC|FRAMEWORK_DIR_INSTALLED=\"$FRAMEWORK_DIR\"  # SUBSTITUTED-BY-SETUP-CC|" \
    "$SOURCE" > "$INSTALL_PATH"
chmod +x "$INSTALL_PATH"
echo "cc-Launcher: $INSTALL_PATH (substituted from $SOURCE, FRAMEWORK_DIR=$FRAMEWORK_DIR)"

# Sanity: verify the substitution actually fired (catches marker drift early).
if ! grep -q "^FRAMEWORK_DIR_INSTALLED=\"$FRAMEWORK_DIR\"" "$INSTALL_PATH"; then
  echo "FEHLER: Substitution in $INSTALL_PATH fehlgeschlagen — Marker im Source aendern?" >&2
  exit 1
fi

# --- Generate path-whitelist.txt ---
WHITELIST_TEMPLATE="$FRAMEWORK_DIR/.claude/path-whitelist.txt.example"
WHITELIST_TARGET="$FRAMEWORK_DIR/.claude/path-whitelist.txt"
if [ -f "$WHITELIST_TEMPLATE" ]; then
  sed -e "s|\${FRAMEWORK_DIR}|$FRAMEWORK_DIR|g" \
      -e "s|\${HOME}|$HOME|g" \
      "$WHITELIST_TEMPLATE" > "$WHITELIST_TARGET"
  echo "path-whitelist: $WHITELIST_TARGET"
else
  echo "WARNUNG: $WHITELIST_TEMPLATE fehlt — path-whitelist nicht generiert." >&2
fi

# --- Provision .claude/settings.local.json (env block for CLAUDE_PROJECT_DIR) ---
# Why: committed .claude/settings.json uses ${CLAUDE_PROJECT_DIR}/... for
# all hook paths. The cc Launcher sets CLAUDE_PROJECT_DIR automatically;
# claude-desktop and claude-web do NOT — there the variable is unset, the
# path resolves to /orchestrators/..., the hooks die silently, and the
# whole discipline layer (path-whitelist, frozen-zones, brief-claims,
# SessionStart boot-inject, workflow-reminder, …) is off.
#
# Fix: provision per-user settings.local.json with an env block that sets
# CLAUDE_PROJECT_DIR to this checkout's absolute path. settings.local.json
# is gitignored and machine-local, so committed settings.json stays
# user-neutral. CC merges settings.local.json over settings.json.
#
# Idempotent: skip if the env block already names this FRAMEWORK_DIR;
# refuse to overwrite a different file silently — bail with a hint so
# the user can merge by hand.
SETTINGS_LOCAL="$FRAMEWORK_DIR/.claude/settings.local.json"
DESIRED_ENV_LINE="\"CLAUDE_PROJECT_DIR\": \"$FRAMEWORK_DIR\""
if [ -f "$SETTINGS_LOCAL" ]; then
  if grep -qF "$DESIRED_ENV_LINE" "$SETTINGS_LOCAL"; then
    echo "settings.local.json: OK (CLAUDE_PROJECT_DIR already pinned to $FRAMEWORK_DIR)"
  else
    echo "WARNUNG: $SETTINGS_LOCAL existiert, enthaelt aber nicht den erwarteten CLAUDE_PROJECT_DIR-Eintrag." >&2
    echo "         Fuege manuell ein (oder loesche die Datei und re-run setup-cc.sh):" >&2
    echo "         { \"env\": { $DESIRED_ENV_LINE } }" >&2
  fi
else
  cat > "$SETTINGS_LOCAL" <<JSON
{
  "env": {
    "CLAUDE_PROJECT_DIR": "$FRAMEWORK_DIR"
  }
}
JSON
  echo "settings.local.json: $SETTINGS_LOCAL (CLAUDE_PROJECT_DIR=$FRAMEWORK_DIR)"
  echo "  → fixes claude-desktop / claude-web hook resolution (cc terminal sets the var itself)"
fi

# --- PATH-Check ---
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
  echo ""
  echo "WARNUNG: $INSTALL_DIR ist nicht im PATH."
  echo "Fuege zu ~/.bashrc oder ~/.zshrc hinzu:"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# --- Symlink check + auto-fix ---
# ~/.claude/agents MUSS auf .claude/agents/ zeigen (CC-Wrapper), NICHT auf
# agents/ (orchestrator-neutral SoT). Falscher Symlink fuehrt zu Drift bei
# Persona-Discovery (CC findet SoT-Files statt Wrapper-Files).
USER_AGENTS_LINK="$HOME/.claude/agents"
USER_SKILLS_LINK="$HOME/.claude/skills"
EXPECTED_AGENTS_TARGET="$FRAMEWORK_DIR/.claude/agents"
EXPECTED_SKILLS_TARGET="$FRAMEWORK_DIR/.claude/skills"

mkdir -p "$HOME/.claude"

# Agents-Symlink
# Reihenfolge wichtig: -L vor -e pruefen, sonst werden broken Symlinks
# (Symlink existiert, Target weg) faelschlicherweise als "nichts da"
# erkannt — danach failed ln -s weil der Symlink-File existiert.
if [ -L "$USER_AGENTS_LINK" ]; then
  current=$(readlink -f "$USER_AGENTS_LINK" 2>/dev/null || true)
  expected=$(readlink -f "$EXPECTED_AGENTS_TARGET" 2>/dev/null || true)
  if [ "$current" != "$expected" ]; then
    echo "agents-Symlink-Korrektur: $USER_AGENTS_LINK"
    echo "  current  → $current"
    echo "  expected → $expected"
    rm "$USER_AGENTS_LINK"
    ln -s "$EXPECTED_AGENTS_TARGET" "$USER_AGENTS_LINK"
    echo "  re-linked."
  else
    echo "agents-Symlink: OK"
  fi
elif [ -e "$USER_AGENTS_LINK" ]; then
  echo "WARNUNG: $USER_AGENTS_LINK ist kein Symlink (echtes Verzeichnis)." >&2
  echo "         Manuell pruefen — eventuell sichern und durch Symlink ersetzen." >&2
else
  ln -s "$EXPECTED_AGENTS_TARGET" "$USER_AGENTS_LINK"
  echo "agents-Symlink: $USER_AGENTS_LINK -> $EXPECTED_AGENTS_TARGET (angelegt)"
fi

# Skills-Symlink (analog — -L vor -e)
if [ -L "$USER_SKILLS_LINK" ]; then
  current=$(readlink -f "$USER_SKILLS_LINK" 2>/dev/null || true)
  expected=$(readlink -f "$EXPECTED_SKILLS_TARGET" 2>/dev/null || true)
  if [ "$current" != "$expected" ]; then
    echo "skills-Symlink-Korrektur: $USER_SKILLS_LINK"
    rm "$USER_SKILLS_LINK"
    ln -s "$EXPECTED_SKILLS_TARGET" "$USER_SKILLS_LINK"
    echo "  re-linked."
  else
    echo "skills-Symlink: OK"
  fi
elif [ -e "$USER_SKILLS_LINK" ]; then
  echo "WARNUNG: $USER_SKILLS_LINK ist kein Symlink (echtes Verzeichnis)." >&2
else
  ln -s "$EXPECTED_SKILLS_TARGET" "$USER_SKILLS_LINK"
  echo "skills-Symlink: $USER_SKILLS_LINK -> $EXPECTED_SKILLS_TARGET (angelegt)"
fi

# --- Git Hooks (pre-commit + commit-msg) ---
# Wires .git/hooks/{pre-commit,commit-msg} in this framework checkout
# to orchestrators/claude-code/hooks/pre-commit.sh (the script self-
# detects mode via $0 basename, F-102). The dedicated installer handles
# worktrees, idempotency, broken-symlink correction, and a self-probe.
# Consumer repos call the SAME script from their own checkout:
#   bash $FRAMEWORK_DIR/scripts/install-git-hooks.sh
HOOK_INSTALLER="$FRAMEWORK_DIR/scripts/install-git-hooks.sh"
if [ -x "$HOOK_INSTALLER" ]; then
  echo ""
  echo "--- Git hooks (forge_dev itself) ---"
  if ! bash "$HOOK_INSTALLER" "$FRAMEWORK_DIR"; then
    echo "WARNUNG: install-git-hooks.sh meldete FAIL. Manuell pruefen." >&2
  fi
else
  echo "WARNUNG: $HOOK_INSTALLER fehlt oder nicht ausfuehrbar — git-hooks nicht installiert." >&2
fi

echo ""
echo "Verwendung:"
echo "  cc              → CWD (intent.md erwartet)"
echo "  cc framework    → $FRAMEWORK_DIR"
echo "  cc <project>    → \$PROJECTS_DIR/<project>/ (Default: \$HOME/projects)"
echo ""
echo "OpenCode-Adapter: bash $FRAMEWORK_DIR/scripts/setup-oc.sh"
