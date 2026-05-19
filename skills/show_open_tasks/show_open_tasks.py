#!/usr/bin/env python3
"""show_open_tasks — generic open-task overview table.

Scans a `docs/tasks/` directory of per-task YAML files and emits a
table of the OPEN tasks (status not in a terminal set). For each task
the "last update" is reported three ways: the YAML `updated:` date, the
last git commit that touched the task files (date + subject), and a
short slice of the task's own summary/objective.

Project-neutral: pass --tasks-dir for any repo following the
`docs/tasks/NNN.yaml` convention. Field names are tolerated loosely
(summary|objective, title, status, updated|created, priority|prio).
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys

# Terminal = NOT open. Everything else (pending, in_progress, blocked,
# spec-draft-*, review-*, ...) counts as open.
TERMINAL = {"done", "wontfix", "superseded", "absorbed", "obsolete",
            "cancelled", "canceled", "closed", "moot"}

STATUS_ORDER = {"in_progress": 0, "blocked": 1, "pending": 2}
PRIO_ORDER = {"high": 0, "medium": 1, "low": 2}
PRIO_ALIAS = {"mid": "medium", "med": "medium", "normal": "medium",
              "hi": "high", "lo": "low"}


def _norm_prio(raw) -> str:
    """Tolerant priority normalisation: take the first word, lowercase,
    map aliases (mid→medium). Strips trailing notes like
    'high (2026-05-18, User)'."""
    if raw is None:
        return "—"
    tok = re.split(r"[\s(]", str(raw).strip().lower(), maxsplit=1)[0]
    tok = PRIO_ALIAS.get(tok, tok)
    return tok if tok in PRIO_ORDER else (tok or "—")


def _load_yaml(path: str) -> dict:
    """Parse a task YAML. Prefer PyYAML; fall back to a flat-key parser
    that also captures `>`/`|` folded block scalars (enough for the
    fields this tool reads)."""
    try:
        import yaml  # type: ignore
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}
    except ModuleNotFoundError:
        pass
    except Exception:
        return {}

    data: dict = {}
    key = None
    block: list[str] | None = None
    block_indent = None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if block is not None:
                if line.strip() == "" or line.startswith((" ", "\t")):
                    if block_indent is None and line.strip():
                        block_indent = len(line) - len(line.lstrip())
                    block.append(line.strip())
                    continue
                data[key] = " ".join(w for w in block if w).strip()
                block = None
            m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if val in (">", "|", ">-", "|-", ">+", "|+"):
                block, block_indent = [], None
                continue
            data[key] = val.strip().strip('"').strip("'")
    if block is not None and key is not None:
        data[key] = " ".join(w for w in block if w).strip()
    return data


def _first_sentence(text: str, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    cut = re.split(r"(?<=[.!?]) ", text)[0]
    if len(cut) > limit:
        cut = cut[: limit - 1].rstrip() + "…"
    return cut


def _git_last_change(repo: str, files: list[str]) -> str:
    existing = [f for f in files if os.path.exists(f)]
    if not existing:
        return "—"
    try:
        out = subprocess.run(
            ["git", "-C", repo, "log", "-1", "--date=short",
             "--format=%ad\x1f%s", "--", *existing],
            capture_output=True, text=True, timeout=10,
        )
        line = out.stdout.strip()
        if not line:
            return "uncommitted"
        date, _, subj = line.partition("\x1f")
        subj = subj.strip()
        if len(subj) > 70:
            subj = subj[:69].rstrip() + "…"
        return f"{date} — {subj}"
    except Exception:
        return "—"


def _md_escape(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def collect(tasks_dir: str, repo: str, include_all: bool) -> list[dict]:
    rows = []
    for ypath in sorted(glob.glob(os.path.join(tasks_dir, "*.yaml"))):
        base = os.path.splitext(os.path.basename(ypath))[0]
        if not re.fullmatch(r"\d+", base):
            continue  # skip review-artefact yamls like 020-review-*
        d = _load_yaml(ypath)
        status = str(d.get("status", "") or "").strip().lower()
        if not include_all and status in TERMINAL:
            continue
        ic = d.get("intent_chain")
        ic_action = ic.get("action") if isinstance(ic, dict) else None
        intent_src = (d.get("summary") or d.get("objective")
                      or ic_action or "")
        mdpath = os.path.join(tasks_dir, base + ".md")
        rows.append({
            "id": str(d.get("id", base)),
            "title": str(d.get("title", "") or "(no title)"),
            "status": status or "(unset)",
            "priority": _norm_prio(d.get("priority", d.get("prio"))),
            "intent": _first_sentence(str(intent_src or "")),
            "updated": str(d.get("updated") or d.get("created") or "—"),
            "git": _git_last_change(repo, [ypath, mdpath]),
        })
    rows.sort(key=lambda r: (STATUS_ORDER.get(r["status"], 9),
                             PRIO_ORDER.get(r["priority"], 8),
                             int(r["id"]) if r["id"].isdigit() else 0))
    return rows


def render_md(rows: list[dict]) -> str:
    head = ("| ID | Status | Prio | Intent | Updated | Last change (git) |\n"
            "|----|--------|------|--------|---------|-------------------|")
    body = "\n".join(
        f"| {r['id']} | {r['status']} | {r['priority']} | "
        f"**{_md_escape(r['title'])}** — {_md_escape(r['intent'])} | "
        f"{r['updated']} | {_md_escape(r['git'])} |"
        for r in rows
    )
    return f"{head}\n{body}\n\n_{len(rows)} open task(s)._"


def _clip(text: str, width: int) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if width <= 1:
        return ""
    return text if len(text) <= width else text[: width - 1] + "…"


def render_term(rows: list[dict]) -> str:
    """Box-drawing ASCII table (TTY aesthetic). One row per task,
    columns ID │ STATUS │ PRIO │ UPDATED │ TITLE, hard-truncated to the
    terminal width — never wraps. A horizontal rule separates each
    status group so the table stays scannable."""
    import shutil
    cols = shutil.get_terminal_size((100, 24)).columns
    cols = max(70, min(cols, 120))
    id_w, st_w, pr_w, dt_w = 3, 11, 6, 10
    # frame: 5 "│" separators + each cell padded " x " (2 spaces/col)
    title_w = cols - (id_w + st_w + pr_w + dt_w) - 5 - 10
    widths = [id_w, st_w, pr_w, dt_w, title_w]

    def rule(left: str, mid: str, right: str) -> str:
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def row(c1: str, c2: str, c3: str, c4: str, c5: str) -> str:
        cells = [_clip(c1, id_w).rjust(id_w),
                 _clip(c2, st_w).ljust(st_w),
                 _clip(c3, pr_w).ljust(pr_w),
                 _clip(c4, dt_w).ljust(dt_w),
                 _clip(c5, title_w).ljust(title_w)]
        return "│ " + " │ ".join(cells) + " │"

    out = [rule("┌", "┬", "┐"),
           row("ID", "STATUS", "PRIO", "UPDATED", "TITLE"),
           rule("├", "┼", "┤")]
    cur = None
    for r in rows:
        if cur is not None and r["status"] != cur:
            out.append(rule("├", "┼", "┤"))
        cur = r["status"]
        out.append(row(r["id"], r["status"], r["priority"],
                       r["updated"], r["title"]))
    out.append(rule("└", "┴", "┘"))

    n_ip = sum(1 for r in rows if r["status"] == "in_progress")
    out.append(f"{len(rows)} open  ({n_ip} in_progress, "
               f"{len(rows) - n_ip} other)  ·  detail: --format md")
    return "\n".join(out)


def render_csv(rows: list[dict]) -> str:
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "status", "priority", "title", "intent",
                "updated", "git"])
    for r in rows:
        w.writerow([r["id"], r["status"], r["priority"], r["title"],
                    r["intent"], r["updated"], r["git"]])
    return buf.getvalue().rstrip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Open-task overview table.")
    ap.add_argument("--tasks-dir", default="docs/tasks",
                    help="Directory of NNN.yaml task files.")
    ap.add_argument("--repo", default=None,
                    help="Git repo root (default: derived from tasks-dir).")
    ap.add_argument("--all", action="store_true",
                    help="Include terminal (done/wontfix/…) tasks too.")
    ap.add_argument("--format", choices=["term", "md", "csv"],
                    default="term")
    a = ap.parse_args(argv)

    tasks_dir = os.path.abspath(a.tasks_dir)
    if not os.path.isdir(tasks_dir):
        print(f"error: tasks dir not found: {tasks_dir}", file=sys.stderr)
        return 2
    repo = os.path.abspath(a.repo) if a.repo else tasks_dir
    try:
        repo = subprocess.run(
            ["git", "-C", repo, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip() or repo
    except Exception:
        pass

    rows = collect(tasks_dir, repo, a.all)
    render = {"term": render_term, "md": render_md,
              "csv": render_csv}[a.format]
    print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
