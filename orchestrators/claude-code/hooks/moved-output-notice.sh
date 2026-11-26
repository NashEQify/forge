#!/usr/bin/env bash
# moved-output-notice.sh — PostToolUse hook (matcher Bash) of the Forge plugin on Claude Code (plugin-hooks.json).
# When the host saved a shell command's output to a file and shows only its first part, the hook's input carries
# tool_response.persistedOutputPath (observed on Claude Code 2.1.282, not documented; a recorded input is
# tests/fixtures/hooks/post-tool-use-bash-moved.json in the development repository, which the public mirror does
# not ship). The hook then puts one notice naming that file into the session's context
# (hookSpecificOutput.additionalContext). Any other input, and a path value that is empty or holds a control
# character, gives no output. It never blocks, refuses or rewrites a command, and it always exits 0.
# Not covered: Codex and OpenCode (no such hook), and a failed command, whose output the host cuts and saves to no
# file (PostToolUseFailure, observed on 2.1.282).
# Cost: it starts after every Bash call. The common path is bash builtins only (read, one pattern match); python3
# starts only when the key is in the input and runs isolated (-I), so a module in the working directory is never
# imported.

IFS= read -r -d '' input || true
[[ $input == *'"persistedOutputPath"'* ]] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
IFS= read -r -d '' program <<'PY' || true
import json, sys
NOTICE = ("This command's output was saved to {path}; only its first part is shown, and the rest is not loaded "
          "until that file is read.")
try:
    path = json.loads(sys.stdin.read())["tool_response"]["persistedOutputPath"]
except (ValueError, KeyError, TypeError, IndexError):
    sys.exit(0)
if isinstance(path, str) and path and not any(ord(c) < 32 or ord(c) in (127, 0x2028, 0x2029) for c in path):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                             "additionalContext": NOTICE.replace("{path}", path)}}))
PY
python3 -I -c "$program" <<<"$input" 2>/dev/null || true
exit 0
