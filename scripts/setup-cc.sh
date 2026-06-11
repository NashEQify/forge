#!/usr/bin/env bash
# setup-cc.sh — Setup fuer den cc-Launcher (Claude Code).
#
# Was es tut:
#   1. Erkennt FRAMEWORK_DIR aus eigenem Standort.
#   2. Kopiert orchestrators/claude-code/bin/cc nach ~/.local/bin/cc
#      (cc detektiert FRAMEWORK_DIR ohnehin selbst — Kopie ist fuer PATH).
#   3. Merged forge's SessionStart-Hooks idempotent in ~/.claude/settings.json
#      (Template-getrieben, User-Keys bleiben erhalten).
#   4. Pruefe Symlinks ~/.claude/agents und ~/.claude/skills (cc legt sie
#      ebenfalls idempotent an, hier nur Info-Output).
#   5. Wired git pre-commit + commit-msg Hooks im Framework-Checkout.
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

# --- Provision ~/.claude/settings.json with forge hooks (idempotent merge) ---
# Forge ships SessionStart hooks that should fire in EVERY claude-code session
# regardless of CWD (boot-inject + resume-nudge). The canonical place for that
# is ~/.claude/settings.json (global user-level config). Per-project
# .claude/settings.json is no longer used by forge.
#
# Idempotent merge strategy:
#   1. Read existing ~/.claude/settings.json (or {} if absent)
#   2. Strip out the top-level "hooks" key entirely (forge owns this slot)
#   3. Substitute __FRAMEWORK_DIR__ placeholder in the template with the
#      detected absolute path (template-driven so paths are not hardcoded
#      in the script and the same template can be shipped to consumers)
#   4. Merge user's preserved (non-hooks) keys with forge's hooks block
#   5. Write atomically with a timestamped backup of the prior file
#
# User-owned keys (effortLevel, voiceEnabled, permissions, env, …) are
# preserved across re-runs. If a user wants their own hooks alongside
# forge's, they go into a per-project .claude/settings.local.json (which
# CC merges over the global) — not into the global hooks slot.
SETTINGS_TEMPLATE="$FRAMEWORK_DIR/orchestrators/claude-code/settings.json.template"
USER_SETTINGS="$HOME/.claude/settings.json"

if ! command -v jq &>/dev/null; then
  echo "FEHLER: 'jq' wird gebraucht zum idempotenten Mergen von $USER_SETTINGS." >&2
  echo "       Install: apt install jq / brew install jq / dnf install jq" >&2
  exit 1
fi

if [ ! -f "$SETTINGS_TEMPLATE" ]; then
  echo "FEHLER: $SETTINGS_TEMPLATE fehlt." >&2
  exit 1
fi

# Substitute FRAMEWORK_DIR placeholder (in memory, not written to disk).
FORGE_HOOKS_JSON="$(sed "s|__FRAMEWORK_DIR__|$FRAMEWORK_DIR|g" "$SETTINGS_TEMPLATE")"

# Validate substituted template parses as JSON (catches path with quotes).
if ! echo "$FORGE_HOOKS_JSON" | jq empty 2>/dev/null; then
  echo "FEHLER: Template ergibt nach Substitution kein gueltiges JSON. Path mit Sonderzeichen?" >&2
  exit 1
fi

mkdir -p "$HOME/.claude"
USER_PRESERVED="$(jq 'del(.hooks)' "$USER_SETTINGS" 2>/dev/null || echo '{}')"
MERGED="$(jq -n --argjson user "$USER_PRESERVED" --argjson forge "$FORGE_HOOKS_JSON" \
  '$user + $forge')"

if [ -f "$USER_SETTINGS" ] && [ "$(jq -S . "$USER_SETTINGS")" = "$(echo "$MERGED" | jq -S .)" ]; then
  echo "global settings.json: OK (forge hooks already merged into $USER_SETTINGS)"
else
  if [ -f "$USER_SETTINGS" ]; then
    cp "$USER_SETTINGS" "$USER_SETTINGS.backup-$(date +%Y%m%d-%H%M%S)"
  fi
  echo "$MERGED" | jq . > "$USER_SETTINGS"
  echo "global settings.json: $USER_SETTINGS (forge hooks merged, user keys preserved)"
  echo "  → fires in every claude-desktop / claude-web / cc session, regardless of CWD"
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
# detects mode via $0 basename). The dedicated installer handles
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
