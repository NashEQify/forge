#!/usr/bin/env python3
"""
Buddy Operations Center — Control Page Generator

Reads active Claude Code sessions from ~/.claude/sessions/*.json,
enriches with JSONL event logs, checks PID liveness, and generates
a standalone dark-themed HTML dashboard at _site/control/index.html.

Usage:
    python3 scripts/generate-control.py [--output PATH]

Default output: _site/control/index.html (relative to repo root)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_DIR = Path.home() / ".claude"
SESSIONS_DIR = CLAUDE_DIR / "sessions"
PROJECTS_DIR = CLAUDE_DIR / "projects"
CURRENT_HOOK_PATH = REPO_ROOT / "docs" / "current-hook.md"
BACKLOG_PATH = REPO_ROOT / "docs" / "backlog.md"
DEFAULT_OUTPUT = REPO_ROOT / "_site" / "control" / "index.html"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def warn(msg: str) -> None:
    print(f"  WARNING: {msg}", file=sys.stderr)


def now_ms() -> int:
    """Current time in milliseconds since epoch."""
    return int(time.time() * 1000)


def format_duration(ms: int) -> str:
    """Format milliseconds duration into human-readable string."""
    if ms < 0:
        return "0s"
    secs = ms // 1000
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m"
    hours = mins // 60
    remaining_mins = mins % 60
    if hours < 24:
        return f"{hours}h {remaining_mins}m"
    days = hours // 24
    remaining_hours = hours % 24
    return f"{days}d {remaining_hours}h"


def format_ago(ms: int) -> str:
    """Format milliseconds ago into human-readable string."""
    if ms < 0:
        return "just now"
    secs = ms // 1000
    if secs < 5:
        return "just now"
    if secs < 60:
        return f"{secs}s ago"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def format_tokens(n: int) -> str:
    """Format token count into human-readable string (e.g. 1.2M, 89K)."""
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}K"
    return f"{n / 1_000_000:.1f}M"


def html_escape(s: str) -> str:
    """Minimal HTML escaping."""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# PID Liveness
# ---------------------------------------------------------------------------

def is_pid_alive(pid: int) -> bool:
    """Check if a process is alive via os.kill(pid, 0)."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it — still alive
        return True
    except (OSError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Session parsing
# ---------------------------------------------------------------------------

def cwd_to_project_key(cwd: str) -> str:
    """Convert CWD path to Claude project directory name.

    e.g. /home/xxx/BuddyAI -> -home-xxx-BuddyAI
    """
    return cwd.replace("/", "-")


def load_sessions() -> list[dict]:
    """Load all session JSON files from ~/.claude/sessions/."""
    sessions = []
    if not SESSIONS_DIR.exists():
        warn(f"Sessions directory not found: {SESSIONS_DIR}")
        return sessions

    for fpath in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            # Minimal validation — pid and sessionId should exist
            if "pid" not in data or "sessionId" not in data:
                warn(f"Skipping {fpath.name}: missing pid or sessionId")
                continue
            sessions.append(data)
        except (json.JSONDecodeError, OSError) as e:
            warn(f"Skipping {fpath.name}: {e}")
    return sessions


def parse_jsonl_for_session(session_id: str, cwd: str) -> dict:
    """Parse JSONL event log for a session. Returns enrichment data.

    Returns dict with keys:
        model, input_tokens, output_tokens, last_timestamp,
        last_tool_name, last_tool_file, tool_count, recent_actions,
        custom_title
    """
    result = {
        "model": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "last_timestamp": 0,
        "last_tool_name": None,
        "last_tool_file": None,
        "tool_count": 0,
        "recent_actions": [],
        "custom_title": None,
    }

    project_key = cwd_to_project_key(cwd)
    jsonl_path = PROJECTS_DIR / project_key / f"{session_id}.jsonl"

    if not jsonl_path.exists():
        # Try parent directories — session might be in a parent project
        # e.g. cwd is /home/xxx/BuddyAI/workspaces/infra but project is -home-xxx-BuddyAI
        # Check all project dirs to find matching sessionId
        found = False
        if PROJECTS_DIR.exists():
            for proj_dir in PROJECTS_DIR.iterdir():
                if proj_dir.is_dir():
                    candidate = proj_dir / f"{session_id}.jsonl"
                    if candidate.exists():
                        jsonl_path = candidate
                        found = True
                        break
        if not found:
            return result

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type", "")

                # Custom title
                if event_type == "custom-title":
                    title = event.get("customTitle")
                    if title:
                        result["custom_title"] = title

                # Timestamp tracking
                ts = event.get("timestamp")
                if ts and isinstance(ts, (int, float)):
                    if ts > result["last_timestamp"]:
                        result["last_timestamp"] = int(ts)

                # Assistant events — model, tokens, tool calls
                if event_type == "assistant":
                    msg = event.get("message", {})
                    if not isinstance(msg, dict):
                        continue

                    # Model (keep latest)
                    model = msg.get("model")
                    if model:
                        result["model"] = model

                    # Token usage
                    usage = msg.get("usage", {})
                    if isinstance(usage, dict):
                        result["input_tokens"] += (
                            usage.get("input_tokens", 0)
                            + usage.get("cache_creation_input_tokens", 0)
                            + usage.get("cache_read_input_tokens", 0)
                        )
                        result["output_tokens"] += usage.get("output_tokens", 0)

                    # Tool calls
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "tool_use":
                                tool_name = item.get("name", "unknown")
                                tool_input = item.get("input", {})
                                file_hint = ""
                                if isinstance(tool_input, dict):
                                    for key in ("file_path", "path", "pattern", "command"):
                                        if key in tool_input:
                                            val = str(tool_input[key])
                                            # Shorten file paths
                                            if "/" in val:
                                                file_hint = val.split("/")[-1]
                                            else:
                                                file_hint = val
                                            # Truncate long hints (especially Bash commands)
                                            if len(file_hint) > 50:
                                                file_hint = file_hint[:47] + "..."
                                            break

                                result["tool_count"] += 1
                                result["last_tool_name"] = tool_name
                                result["last_tool_file"] = file_hint

                                # Keep recent 3 actions
                                action_str = tool_name
                                if file_hint:
                                    action_str += f" {file_hint}"
                                result["recent_actions"].append(action_str)
                                if len(result["recent_actions"]) > 3:
                                    result["recent_actions"] = result["recent_actions"][-3:]

    except OSError as e:
        warn(f"Error reading JSONL for {session_id}: {e}")

    return result


# ---------------------------------------------------------------------------
# Session enrichment & classification
# ---------------------------------------------------------------------------

def classify_session(session: dict, enrichment: dict, current_ms: int) -> dict:
    """Classify and enrich a session with all display data."""
    pid = session.get("pid", 0)
    started_at = session.get("startedAt", 0)
    cwd = session.get("cwd", "")
    session_id = session.get("sessionId", "")

    # PID liveness
    alive = is_pid_alive(pid)

    # Last activity — from JSONL or startedAt
    last_activity = enrichment.get("last_timestamp", 0)
    if last_activity == 0:
        last_activity = started_at

    # Time since last activity
    idle_ms = current_ms - last_activity if last_activity > 0 else 0

    # Status classification
    if not alive:
        status = "DEAD"
    elif idle_ms > 60 * 60 * 1000:  # >60 min
        status = "DEAD"
    elif idle_ms > 15 * 60 * 1000:  # >15 min
        status = "STALE"
    else:
        status = "ACTIVE"

    # Session name resolution
    name = session.get("name")
    if not name:
        name = enrichment.get("custom_title")
    if not name:
        # Fallback: last CWD segment
        name = cwd.rstrip("/").split("/")[-1] if cwd else "unknown"

    # Model — clean up for display
    model = enrichment.get("model", "unknown")
    if model:
        # Simplify model names
        if "opus" in model.lower():
            model_display = "opus"
        elif "sonnet" in model.lower():
            model_display = "sonnet"
        elif "haiku" in model.lower():
            model_display = "haiku"
        else:
            model_display = model
    else:
        model_display = "unknown"

    # Runtime
    runtime_ms = current_ms - started_at if started_at > 0 else 0

    # Last tool info
    last_tool = ""
    if enrichment.get("last_tool_name"):
        last_tool = enrichment["last_tool_name"]
        if enrichment.get("last_tool_file"):
            last_tool += f" {enrichment['last_tool_file']}"

    # Project name from CWD
    project = cwd.rstrip("/").split("/")[-1] if cwd else "unknown"

    return {
        "name": name,
        "status": status,
        "pid": pid,
        "session_id": session_id,
        "cwd": cwd,
        "project": project,
        "model": model_display,
        "runtime": format_duration(runtime_ms),
        "idle_ms": idle_ms,
        "last_ago": format_ago(idle_ms),
        "last_tool": last_tool,
        "alive": alive,
        "input_tokens": enrichment.get("input_tokens", 0),
        "output_tokens": enrichment.get("output_tokens", 0),
        "tool_count": enrichment.get("tool_count", 0),
        "recent_actions": enrichment.get("recent_actions", []),
    }


# ---------------------------------------------------------------------------
# Project snapshot
# ---------------------------------------------------------------------------

def parse_current_hook() -> dict:
    """Parse current-hook.md for task and step."""
    result = {"task": "-", "step": "-", "status": "unknown"}
    if not CURRENT_HOOK_PATH.exists():
        return result
    try:
        text = CURRENT_HOOK_PATH.read_text(encoding="utf-8")
        m = re.search(r"^task:\s*(.+)$", text, re.MULTILINE)
        if m:
            result["task"] = m.group(1).strip()
        m = re.search(r"^step:\s*(.+)$", text, re.MULTILINE)
        if m:
            result["step"] = m.group(1).strip()
        m = re.search(r"^status:\s*(.+)$", text, re.MULTILINE)
        if m:
            result["status"] = m.group(1).strip()
    except OSError:
        pass
    return result


def parse_backlog_counts() -> dict:
    """Parse backlog.md for task status counts.

    Backlog format uses lines like:
        Prio: high | Area: ... | Status: done | ...
    or section headers like:
        ### [NNN] Task Name -- DONE
    """
    counts = {"pending": 0, "in_progress": 0, "done": 0, "total": 0}
    if not BACKLOG_PATH.exists():
        return counts
    try:
        text = BACKLOG_PATH.read_text(encoding="utf-8")
        for line in text.split("\n"):
            # Match "Status: <value>" in task description lines
            m = re.search(r"Status:\s*(\w+)", line)
            if m:
                status = m.group(1).lower()
                if status == "done":
                    counts["done"] += 1
                elif status == "in_progress":
                    counts["in_progress"] += 1
                elif status in ("pending", "todo"):
                    counts["pending"] += 1
                elif status == "superseded":
                    pass  # Don't count superseded
                else:
                    counts["pending"] += 1  # Unknown status → pending
                counts["total"] += 1
    except OSError:
        pass
    return counts


def get_recent_commits(n: int = 10) -> list[str]:
    """Get last N commits via git log."""
    try:
        result = subprocess.run(
            ["git", "log", f"--oneline", f"-{n}"],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    except (subprocess.SubprocessError, OSError):
        pass
    return []


# ---------------------------------------------------------------------------
# Ampel (traffic light) logic
# ---------------------------------------------------------------------------

def compute_ampel(sessions: list[dict], hook: dict) -> tuple[str, str, str]:
    """Compute traffic light status. Returns (label, color_name, css_color)."""
    if not sessions:
        if hook.get("status") == "active":
            return ("ACT", "red", "#f44336")
        return ("IDLE", "gray", "#757575")

    has_dead = any(s["status"] == "DEAD" for s in sessions)
    has_stale = any(s["status"] == "STALE" for s in sessions)

    if has_dead:
        return ("ACT", "red", "#f44336")
    if has_stale:
        return ("WATCH", "yellow", "#ffb300")
    return ("CLEAR", "green", "#4caf50")


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
  background: #1e1e2e; color: #cdd6f4; line-height: 1.6;
  min-height: 100vh;
}
.container { max-width: 900px; margin: 0 auto; padding: 1.5rem; }

/* Status Bar */
.status-bar {
  display: flex; align-items: center; gap: 1rem;
  background: #2d2d3d; padding: 0.8rem 1.5rem;
  border-bottom: 2px solid #7c4dff; flex-wrap: wrap;
}
.status-bar h1 {
  font-size: 0.9rem; letter-spacing: 0.15em; color: #cba6f7;
  font-weight: 700; text-transform: uppercase;
}
.ampel {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.2rem 0.7rem; border-radius: 12px;
  font-size: 0.8rem; font-weight: 600;
  border: 1px solid #444;
}
.ampel-green { background: #1b5e2033; color: #4caf50; border-color: #4caf5044; }
.ampel-yellow { background: #ff8f0033; color: #ffb300; border-color: #ffb30044; }
.ampel-red { background: #f4433633; color: #f44336; border-color: #f4433644; }
.ampel-gray { background: #42424233; color: #757575; border-color: #75757544; }
.session-count { color: #888; font-size: 0.85rem; }
.generated { margin-left: auto; color: #666; font-size: 0.8rem; }

/* Section */
.section { margin-top: 1.5rem; }
.section-title {
  font-size: 0.75rem; color: #888; text-transform: uppercase;
  letter-spacing: 0.1em; margin-bottom: 0.8rem;
  border-bottom: 1px solid #333; padding-bottom: 0.3rem;
}

/* Session Cards */
.card {
  background: #262637; border: 1px solid #333; border-radius: 8px;
  margin-bottom: 0.8rem; overflow: hidden;
}
.card-main { padding: 0.8rem 1rem; }
.card-row1 {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 0.3rem;
}
.card-name { font-weight: 700; color: #e0e0e0; font-size: 0.95rem; }
.badge {
  font-size: 0.7rem; font-weight: 600; padding: 0.15rem 0.5rem;
  border-radius: 10px; text-transform: uppercase; letter-spacing: 0.05em;
}
.badge-active { background: #1b5e2044; color: #4caf50; }
.badge-stale { background: #ff8f0044; color: #ffb300; }
.badge-dead { background: #f4433644; color: #f44336; }
.card-row2 { color: #888; font-size: 0.82rem; }
.card-row2 .model { color: #cba6f7; }
.card-row2 .stale-hint { color: #ffb300; font-style: italic; }
.card-row2 .dead-hint { color: #f44336; font-style: italic; }

/* Details expand */
.card details { border-top: 1px solid #333; }
.card details summary {
  padding: 0.4rem 1rem; font-size: 0.75rem; color: #666;
  cursor: pointer; user-select: none;
}
.card details summary:hover { color: #999; }
.card details .detail-body {
  padding: 0.5rem 1rem 0.8rem; font-size: 0.8rem; color: #888;
}
.detail-row { margin-bottom: 0.2rem; }
.detail-label { color: #666; }
.detail-value { color: #aaa; }
.recent-list { list-style: none; padding-left: 0; }
.recent-list li { color: #888; }
.recent-list li::before { content: "\\2192 "; color: #666; }

/* Empty State */
.empty-state {
  text-align: center; padding: 3rem 1rem;
  color: #666; font-size: 0.95rem;
}
.empty-state h2 { color: #888; font-size: 1.1rem; margin-bottom: 1rem; }
.empty-links { margin-top: 1.5rem; }
.empty-links a {
  display: inline-block; margin: 0.3rem;
  padding: 0.4rem 1rem; border: 1px solid #444;
  border-radius: 6px; color: #cba6f7; text-decoration: none;
  font-size: 0.85rem;
}
.empty-links a:hover { background: #7c4dff22; border-color: #7c4dff; }

/* Project Snapshot */
.snapshot {
  background: #262637; border: 1px solid #333; border-radius: 8px;
  padding: 0.8rem 1rem; font-size: 0.85rem;
}
.snapshot-row { margin-bottom: 0.2rem; }
.snapshot-label { color: #666; }
.snapshot-value { color: #aaa; }
.snapshot-value.hook-task { color: #cba6f7; font-weight: 600; }

/* Commits */
.commit-list {
  list-style: none; padding: 0; font-size: 0.8rem;
  font-family: monospace;
}
.commit-list li { padding: 0.15rem 0; color: #777; }
.commit-hash { color: #cba6f7; }

/* Footer */
.footer {
  margin-top: 2rem; padding-top: 1rem;
  border-top: 1px solid #333; text-align: center;
}
.footer a {
  display: inline-block; margin: 0.3rem 0.5rem;
  color: #7c4dff; text-decoration: none; font-size: 0.8rem;
}
.footer a:hover { text-decoration: underline; }
.footer .note { color: #555; font-size: 0.7rem; margin-top: 0.5rem; }
"""


def render_status_bar(ampel_label: str, ampel_color: str, session_count: int,
                      generated_time: str) -> str:
    """Render the top status bar."""
    ampel_class = f"ampel-{ampel_color}"
    dot = "&#9679;"
    count_text = f"{session_count} Active" if session_count > 0 else "0 Active"
    return f"""\
<div class="status-bar">
  <h1>Buddy Ops Center</h1>
  <span class="ampel {ampel_class}">{dot} {html_escape(ampel_label)}</span>
  <span class="session-count">{count_text}</span>
  <span class="generated">Generated: {html_escape(generated_time)}</span>
</div>"""


def render_session_card(s: dict) -> str:
    """Render a single session card."""
    badge_class = f"badge-{s['status'].lower()}"
    status_label = s["status"]

    # Row 2 content
    parts = [f'<span class="model">{html_escape(s["model"])}</span>']
    parts.append(html_escape(s["runtime"]))

    if s["last_tool"]:
        parts.append(f"Last: {html_escape(s['last_tool'])} ({html_escape(s['last_ago'])})")
    else:
        parts.append(f"Last activity: {html_escape(s['last_ago'])}")

    # Stale/dead hints
    hint = ""
    if s["status"] == "STALE":
        hint = '<span class="stale-hint"> &mdash; may be waiting for input</span>'
    elif s["status"] == "DEAD":
        if s["alive"]:
            hint = '<span class="dead-hint"> &mdash; likely dead</span>'
        else:
            hint = '<span class="dead-hint"> &mdash; process not running</span>'

    row2 = " &middot; ".join(parts) + hint

    # Details section
    detail_rows = []
    detail_rows.append(
        f'<div class="detail-row"><span class="detail-label">PID:</span> '
        f'<span class="detail-value">{s["pid"]}'
        f'{" (alive)" if s["alive"] else " (dead)"}'
        f'</span></div>'
    )
    detail_rows.append(
        f'<div class="detail-row"><span class="detail-label">Project:</span> '
        f'<span class="detail-value">{html_escape(s["project"])}</span></div>'
    )
    detail_rows.append(
        f'<div class="detail-row"><span class="detail-label">Tokens:</span> '
        f'<span class="detail-value">{format_tokens(s["input_tokens"])} in / '
        f'{format_tokens(s["output_tokens"])} out</span></div>'
    )
    detail_rows.append(
        f'<div class="detail-row"><span class="detail-label">Tools:</span> '
        f'<span class="detail-value">{s["tool_count"]} calls</span></div>'
    )

    if s["recent_actions"]:
        items = "".join(f"<li>{html_escape(a)}</li>" for a in s["recent_actions"])
        detail_rows.append(
            f'<div class="detail-row"><span class="detail-label">Recent:</span>'
            f'<ul class="recent-list">{items}</ul></div>'
        )

    details_html = "\n".join(detail_rows)

    return f"""\
<div class="card">
  <div class="card-main">
    <div class="card-row1">
      <span class="card-name">{html_escape(s["name"])}</span>
      <span class="badge {badge_class}">{html_escape(status_label)}</span>
    </div>
    <div class="card-row2">{row2}</div>
  </div>
  <details>
    <summary>details</summary>
    <div class="detail-body">
      {details_html}
    </div>
  </details>
</div>"""


def render_empty_state(hook: dict) -> str:
    """Render the empty state when no sessions are running."""
    hook_line = ""
    if hook.get("task") and hook["task"] != "-":
        hook_line = f'<p>Hook: {html_escape(hook["task"])}</p>'
    step_line = ""
    if hook.get("step") and hook["step"] != "-":
        step_line = f'<p>Next: {html_escape(hook["step"])}</p>'

    return f"""\
<div class="empty-state">
  <h2>No agent sessions running.</h2>
  {hook_line}
  {step_line}
  <div class="empty-links">
    <a href="/dashboard/">Open Dashboard</a>
    <a href="/">Open Architecture Site</a>
  </div>
</div>"""


def render_snapshot(hook: dict, counts: dict) -> str:
    """Render the project snapshot section."""
    rows = []
    if hook.get("task") and hook["task"] != "-":
        rows.append(
            f'<div class="snapshot-row"><span class="snapshot-label">Hook:</span> '
            f'<span class="snapshot-value hook-task">{html_escape(hook["task"])}</span></div>'
        )
    if hook.get("step") and hook["step"] != "-":
        rows.append(
            f'<div class="snapshot-row"><span class="snapshot-label">Next:</span> '
            f'<span class="snapshot-value">{html_escape(hook["step"])}</span></div>'
        )
    if counts.get("total", 0) > 0:
        rows.append(
            f'<div class="snapshot-row"><span class="snapshot-label">Tasks:</span> '
            f'<span class="snapshot-value">'
            f'{counts["in_progress"]} in_progress &middot; '
            f'{counts["pending"]} pending &middot; '
            f'{counts["done"]} done'
            f'</span></div>'
        )
    if not rows:
        return ""
    return f"""\
<div class="snapshot">
  {"".join(rows)}
</div>"""


def render_commits(commits: list[str]) -> str:
    """Render the recent commits section."""
    if not commits:
        return ""
    items = []
    for c in commits[:10]:
        parts = c.split(" ", 1)
        hash_str = parts[0] if parts else ""
        msg = parts[1] if len(parts) > 1 else ""
        items.append(
            f'<li><span class="commit-hash">{html_escape(hash_str)}</span> '
            f'{html_escape(msg)}</li>'
        )
    return "\n".join(items)


def render_footer() -> str:
    """Render the quick links footer."""
    return """\
<div class="footer">
  <a href="/">Architecture Site</a>
  <a href="/dashboard/">Kanban Dashboard</a>
  <a href="/system-context/">C4 Model</a>
  <div class="note">Static page — regenerate with: python3 scripts/generate-control.py</div>
</div>"""


def generate_html(sessions: list[dict], hook: dict, counts: dict,
                  commits: list[str], generated_time: str) -> str:
    """Generate the complete HTML page."""
    # Compute ampel
    active_sessions = [s for s in sessions if s["status"] in ("ACTIVE", "STALE")]
    ampel_label, ampel_color, _ = compute_ampel(sessions, hook)

    # Status bar
    status_bar = render_status_bar(ampel_label, ampel_color, len(sessions), generated_time)

    # Sessions section
    if sessions:
        # Sort: ACTIVE first, then STALE, then DEAD
        order = {"ACTIVE": 0, "STALE": 1, "DEAD": 2}
        sorted_sessions = sorted(sessions, key=lambda s: order.get(s["status"], 3))
        cards = "\n".join(render_session_card(s) for s in sorted_sessions)
        sessions_html = f"""\
<div class="section">
  <div class="section-title">Active Sessions</div>
  {cards}
</div>"""
    else:
        sessions_html = render_empty_state(hook)

    # Project snapshot
    snapshot_html = render_snapshot(hook, counts)
    if snapshot_html:
        snapshot_html = f"""\
<div class="section">
  <div class="section-title">Project Snapshot</div>
  {snapshot_html}
</div>"""

    # Recent commits
    commits_html = render_commits(commits)
    if commits_html:
        commits_html = f"""\
<div class="section">
  <div class="section-title">Recent Commits</div>
  <ul class="commit-list">
    {commits_html}
  </ul>
</div>"""

    # Footer
    footer = render_footer()

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Buddy Ops Center</title>
  <style>
{CSS}
  </style>
</head>
<body>
  {status_bar}
  <div class="container">
    {sessions_html}
    {snapshot_html}
    {commits_html}
    {footer}
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Buddy Operations Center HTML")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output HTML file (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    start_time = time.monotonic()
    current_ms = now_ms()
    generated_time = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

    print("Buddy Operations Center — generating...")

    # 1. Load sessions
    raw_sessions = load_sessions()
    print(f"  Found {len(raw_sessions)} session file(s)")

    # 2. Enrich each session with JSONL data + PID check
    enriched_sessions = []
    for raw in raw_sessions:
        sid = raw.get("sessionId", "")
        cwd = raw.get("cwd", "")
        try:
            enrichment = parse_jsonl_for_session(sid, cwd)
            classified = classify_session(raw, enrichment, current_ms)
            enriched_sessions.append(classified)
        except Exception as e:
            warn(f"Error processing session {sid}: {e}")

    # Count by status
    status_counts = {}
    for s in enriched_sessions:
        status_counts[s["status"]] = status_counts.get(s["status"], 0) + 1
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    # 3. Parse project state
    hook = parse_current_hook()
    counts = parse_backlog_counts()
    commits = get_recent_commits()

    # 4. Generate HTML
    html = generate_html(enriched_sessions, hook, counts, commits, generated_time)

    # 5. Write output
    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    elapsed = time.monotonic() - start_time
    size_kb = len(html.encode("utf-8")) / 1024
    print(f"  Output: {output_path} ({size_kb:.1f} KB, {elapsed:.2f}s)")


if __name__ == "__main__":
    main()
