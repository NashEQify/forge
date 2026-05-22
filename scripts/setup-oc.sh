#!/usr/bin/env bash
# setup-oc.sh — Setup fuer den oc-Launcher (OpenCode), opencode.jsonc und
# die forge-hooks Plugin-Voraussetzungen.
#
# Was es tut:
#   1. Erkennt FRAMEWORK_DIR aus eigenem Standort.
#   2. Generiert orchestrators/opencode/opencode.jsonc aus .example
#      (substituiert ${FRAMEWORK_DIR} und ${HOME}).
#   3. Kopiert orchestrators/opencode/bin/oc nach ~/.local/bin/oc mit
#      install-time FRAMEWORK_DIR-Substitution (analog zu setup-cc.sh).
#   4. Verifiziert das forge-hooks Plugin
#      (.opencode/plugins/forge-hooks.ts).
#   5. Pruefe Bun (OpenCode-Runtime) und opencode CLI Verfuegbarkeit.
#
# Idempotent. Safe to re-run.
#
# Usage: bash $FRAMEWORK_DIR/scripts/setup-oc.sh
#
# Voraussetzungen:
#   - opencode CLI installiert (`opencode --version`)
#   - Bun runtime (kommt mit OpenCode)
#   - ~/.local/bin/ im PATH (sonst Warnung)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
FRAMEWORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="$HOME/.local/bin"
INSTALL_PATH="$INSTALL_DIR/oc"

TEMPLATE="$FRAMEWORK_DIR/orchestrators/opencode/opencode.jsonc.example"
TARGET="$FRAMEWORK_DIR/orchestrators/opencode/opencode.jsonc"
LAUNCHER_SOURCE="$FRAMEWORK_DIR/orchestrators/opencode/bin/oc"
PLUGIN_FILE="$FRAMEWORK_DIR/orchestrators/opencode/.opencode/plugins/forge-hooks.ts"

# --- Checks ---
if [ ! -f "$FRAMEWORK_DIR/CLAUDE.md" ]; then
  echo "FEHLER: $FRAMEWORK_DIR sieht nicht nach forge aus (kein CLAUDE.md)." >&2
  exit 1
fi

if [ ! -f "$TEMPLATE" ]; then
  echo "FEHLER: template not found at $TEMPLATE" >&2
  exit 1
fi

if [ ! -f "$LAUNCHER_SOURCE" ]; then
  echo "FEHLER: launcher source not found at $LAUNCHER_SOURCE" >&2
  exit 1
fi

# --- Generate opencode.jsonc ---
# Substitute ${FRAMEWORK_DIR} and ${HOME} via simple sed (paths shouldn't
# contain | so it's safe as the sed delimiter).
sed -e "s|\${FRAMEWORK_DIR}|$FRAMEWORK_DIR|g" \
    -e "s|\${HOME}|$HOME|g" \
    "$TEMPLATE" > "$TARGET"
echo "opencode.jsonc: $TARGET"
echo "  FRAMEWORK_DIR = $FRAMEWORK_DIR"
echo "  HOME          = $HOME"

# --- Install oc launcher to ~/.local/bin/oc ---
# oc autodetects FRAMEWORK_DIR from $0 location, but the install copy under
# ~/.local/bin/ would resolve $0/../../.. to /home (wrong). Substitute the
# install-time absolute path into FRAMEWORK_DIR_INSTALLED so the installed
# copy carries its own canonical FRAMEWORK_DIR. Always re-write — content is
# deterministic, no idempotency concern.
mkdir -p "$INSTALL_DIR"
sed "s|^FRAMEWORK_DIR_INSTALLED=\"\"  # SUBSTITUTED-BY-SETUP-OC|FRAMEWORK_DIR_INSTALLED=\"$FRAMEWORK_DIR\"  # SUBSTITUTED-BY-SETUP-OC|" \
    "$LAUNCHER_SOURCE" > "$INSTALL_PATH"
chmod +x "$INSTALL_PATH"
echo "oc-Launcher: $INSTALL_PATH (substituted from $LAUNCHER_SOURCE, FRAMEWORK_DIR=$FRAMEWORK_DIR)"

# Sanity: verify the substitution actually fired (catches marker drift early).
if ! grep -q "^FRAMEWORK_DIR_INSTALLED=\"$FRAMEWORK_DIR\"" "$INSTALL_PATH"; then
  echo "FEHLER: Substitution in $INSTALL_PATH fehlgeschlagen — Marker im Source aendern?" >&2
  exit 1
fi

# --- Plugin presence check ---
if [ -f "$PLUGIN_FILE" ]; then
  echo "forge-hooks plugin: $PLUGIN_FILE (auto-loaded by OpenCode)"
else
  echo "WARNUNG: forge-hooks plugin fehlt at $PLUGIN_FILE — Hook-Discipline-Layer NICHT aktiv." >&2
  echo "         Das Methodology-Layer (agents/skills/workflows) laeuft trotzdem." >&2
fi

# --- PATH check ---
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
  echo ""
  echo "WARNUNG: $INSTALL_DIR ist nicht im PATH."
  echo "Fuege zu ~/.bashrc oder ~/.zshrc hinzu:"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# --- Runtime checks ---
if ! command -v opencode &>/dev/null; then
  echo ""
  echo "WARNUNG: 'opencode' nicht im PATH. Install: https://opencode.ai" >&2
else
  echo "opencode: $(command -v opencode)"
fi

# Bun runtime: OpenCode bundles its own Bun, but a system Bun is also fine.
# The plugin uses Bun.spawn which is OpenCode-runtime-provided either way.
# This check is informational only.
if command -v bun &>/dev/null; then
  echo "bun (system): $(command -v bun) — OK fuer Plugin-Entwicklung"
else
  echo "Info: 'bun' nicht im PATH. OpenCode bringt eigenen Bun — Plugin laeuft trotzdem."
fi

echo ""
echo "Verwendung:"
echo "  oc                 → OpenCode mit forge-Config (alias: ~/.local/bin/oc)"
echo "  oc <opencode-args> → durchgereicht an opencode"
echo ""
echo "Smoke-Test (Hook-Discipline-Layer auf CC-JSON-Kontrakt):"
echo "  bash $FRAMEWORK_DIR/orchestrators/opencode/tests/smoke-shim.sh"
echo ""
echo "Plugin-Doku: $FRAMEWORK_DIR/orchestrators/opencode/PLUGIN.md"
