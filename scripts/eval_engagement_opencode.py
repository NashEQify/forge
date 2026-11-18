#!/usr/bin/env python3
"""Run engagement cases on OpenCode, graded by eval_engagement's own code.

The cases are the files under tests/fixtures/engagement, unchanged, in the two arms `with` and `without`,
N runs each. Per run:
- a fresh Git repository holding the case fixture (eval_engagement.materialize);
- scratch XDG_CONFIG_HOME, XDG_DATA_HOME, XDG_STATE_HOME and XDG_CACHE_HOME under the run folder (<arm>-<n>/xdg),
  OPENCODE_DISABLE_CLAUDE_CODE=1 (no CLAUDE.md, no ~/.claude skills), OPENCODE_DISABLE_EXTERNAL_SKILLS=1 and
  OPENCODE_CONFIG_CONTENT (no autoupdate, no sharing, a header timeout for the model's provider);
- the with arm then gets Forge's OpenCode setup as a user runs it: the framework copy's
  `scripts/forge_setup.py --host opencode project --project <repo>` in the run's scratch XDG directories with a
  scratch HOME (<arm>-<n>/setup-home) for that call, so it writes the project's activation line (repo/AGENTS.md,
  left uncommitted) and the boot skill under the scratch config, and nothing in the real home; the result is stored
  as setup.json. The without arm gets no setup;
- the login: <XDG_DATA_HOME>/opencode/auth.json is a symlink to ~/.local/share/opencode/auth.json, removed after
  the run; no code path opens, reads or copies that file;
- the child environment keeps only basic variables (eval_engagement_direct.child_env) plus the above; no
  CLAUDE*/CODEX_*/FORGE_*/OPENCODE_* variable of the parent reaches it. HOME stays the real one (OpenCode's own
  paths go through XDG), so ~ and $HOME count as outside in the confined check;
- the isolation check: `opencode debug config` and `opencode debug skill` in the run's environment and
  repository, stored as debug-config.json and debug-skill.json. Both arms: no instructions, no default_agent,
  agent/mode/command as empty as in an empty scratch, no mcp, no plugin. Without arm: every listed skill is a
  built-in and no AGENTS.md from the repo up to / holds the activation line. With arm: the built-ins plus exactly
  one forge:boot located under the run's scratch config, and repo/AGENTS.md holds the line. A violation leaves the
  run unscored (`isolation: ...`) and the model is not started.

Limits: OpenCode has no max-turns flag, so a case's max_turns is recorded, not enforced; timeout_seconds is
enforced by killing the process group. A case with user_scope or clean_start is refused (the project install
carries no user scope; a clean start needs the Claude-side origins). The with arm's activation line leaves the case
repository with an uncommitted AGENTS.md (no case check reads the project's Git status).

Grading, judge validation and summary reuse eval_engagement (grade_run, validate_judgement, report); the trace has
the engine's shape (normalize_opencode), tool names mapped to the engine's, so the case checks apply unchanged. The
judge is `claude -p` (eval_engagement_direct.judge) or, with --judge-host opencode, the same hosted model through
`opencode run` with every tool denied. No model runs in the test suite.

Usage:
  python3 scripts/eval_engagement_opencode.py --out <dir outside Git> --model nvidia/poolside/laguna-xs-2.1
      [--case ID ...] [--runs N] [--judge-host claude|opencode] [--judge-model M]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = "eval_engagement_opencode"
HOST = "opencode"
# The login OpenCode keeps; only ever symlinked into a run's scratch XDG_DATA_HOME, never opened.
AUTH = Path.home() / ".local/share/opencode/auth.json"
# OpenCode's lower-case tool names mapped to the engine's, so read/absent/call checks apply as on Claude.
TOOL_NAMES = {"read": "Read", "bash": "Bash", "grep": "Grep", "glob": "Glob", "list": "Glob", "edit": "Edit",
              "write": "Write", "task": "Task", "skill": "Skill", "todowrite": "TodoWrite"}
# A tool error whose output says the host withheld the call (OpenCode 1.19.5's permission messages).
PERMISSION_REJECTION = re.compile(r"The user rejected permission|The user has specified a rule which prevents you"
                                  r"|PermissionRejectedError|PermissionDeniedError|RejectedError|DeniedError")
TERMINAL_STATES = {"completed", "error"}
# `opencode debug config` in an empty scratch with this runner's environment (OpenCode 1.19.5): these keys are empty.
EMPTY_CONFIG = {"agent": {}, "mode": {}, "plugin": [], "command": {}}
BOOT_SKILL = "forge:boot"
BUILTIN = "<built-in>"  # the location `opencode debug skill` lists for OpenCode's own skills
SETUP = "scripts/forge_setup.py"
LIMITS = ["max_turns is not enforced: OpenCode has no max-turns flag (recorded per case)",
          "timeout_seconds is enforced by killing the run's process group",
          "cases with user_scope or clean_start are refused"]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


def direct():
    """eval_engagement_direct, for child_env and the Claude judge."""
    return sys.modules.get("eval_engagement_direct") or _load("eval_engagement_direct",
                                                              ROOT / "scripts/eval_engagement_direct.py")


def engagement():
    return direct().engagement()


def user_scope():
    """This checkout's user_scope (the framework copy is archived from it)."""
    return sys.modules.get("user_scope") or _load("user_scope", ROOT / "scripts/user_scope.py")


def activation_line() -> str:
    return user_scope().ACTIVATION_LINE


def line_files(repo: Path, up_to_root: bool) -> list[Path]:
    """The AGENTS.md files holding the activation line: the repo's alone, or, up_to_root, every one from the repo up
    to / (OpenCode walks up from the cwd; user_scope's activation_found stops at the Git root, so it does not fit)."""
    has_line = user_scope().has_activation_line
    folder = Path(os.path.abspath(repo))
    folders = [folder, *folder.parents] if up_to_root else [folder]
    return [d / "AGENTS.md" for d in folders if has_line(d / "AGENTS.md")]


# --- Trace ---------------------------------------------------------------------------------------------------------


def normalize_opencode(lines: list[str], execution: dict) -> dict:
    """OpenCode's `run --format json` events in the engine's trace shape. execution: returncode, timed_out, model.

    Complete when the process exited 0 within its timeout, the last step_finish has reason `stop`, no error event
    occurred, every tool call reached a terminal state, no line is malformed and no tool call was withheld by a
    permission rule. Unknown event types are recorded (trace["unknown_events"]), not fatal."""
    calls: dict[str, dict] = {}
    texts: dict[str, str] = {}
    malformed, errors, unknown, steps, last_reason = 0, [], {}, 0, None
    usage = {"steps": 0, "input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0}
    for number, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if not isinstance(event, dict):
            malformed += 1
            continue
        kind = event.get("type")
        part = event.get("part") if isinstance(event.get("part"), dict) else {}
        if kind == "tool_use":
            key = part.get("callID") or part.get("id") or f"line-{number}"
            state = part.get("state") if isinstance(part.get("state"), dict) else {}
            raw = str(part.get("tool", ""))
            calls[key] = {"raw": raw, "state": state}
        elif kind == "text":
            key = part.get("id") or f"line-{number}"
            texts[key] = str(part.get("text", ""))
        elif kind == "step_finish":
            steps += 1
            last_reason = part.get("reason")
            tokens = part.get("tokens") if isinstance(part.get("tokens"), dict) else {}
            cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}
            for name, value in (("input", tokens.get("input")), ("output", tokens.get("output")),
                                ("reasoning", tokens.get("reasoning")), ("cache_read", cache.get("read")),
                                ("cache_write", cache.get("write"))):
                usage[name] += int(value or 0)
        elif kind == "error":
            errors.append(json.dumps(event.get("error", event), sort_keys=True)[:400])
        elif kind != "step_start":
            unknown[str(kind)] = unknown.get(str(kind), 0) + 1
    usage["steps"] = steps
    tools, pending, denials = [], 0, 0
    for call in calls.values():
        state = call["state"]
        status = state.get("status")
        error = status == "error"
        if status not in TERMINAL_STATES:
            pending += 1
        if error and PERMISSION_REJECTION.search(str(state.get("error", "")) + str(state.get("output", ""))):
            denials += 1
        tools.append({"name": TOOL_NAMES.get(call["raw"], call["raw"]),
                      "input": json.dumps(state.get("input", {})), "error": error})
    shown = [text for text in texts.values() if text.strip()]
    incomplete = None
    if execution.get("timed_out"):
        incomplete = "timeout"
    elif malformed:
        incomplete = f"{malformed} malformed trace lines"
    elif errors:
        incomplete = f"error event: {errors[0]}"
    elif execution.get("returncode") != 0:
        incomplete = f"returncode {execution.get('returncode')}"
    elif last_reason != "stop":
        incomplete = f"no terminal step (last step_finish reason {last_reason})"
    elif pending:
        incomplete = f"{pending} tool calls without a terminal state"
    elif denials:
        # A denial is the harness withholding a tool the case needs, not behaviour to score.
        incomplete = f"{denials} permission denials"
    return {
        "completed": incomplete is None,
        "incomplete": incomplete,
        "tools": tools,
        "texts": shown,
        "final": shown[-1] if shown else "",
        "model": execution.get("model"),
        "permission_denials": denials,
        "usage": usage,
        "unknown_events": unknown,
    }


# --- Isolation -----------------------------------------------------------------------------------------------------


def config_content(model: str, judge: bool = False) -> str:
    provider = model.split("/", 1)[0]
    config: dict = {"provider": {provider: {"options": {"headerTimeout": 120000}}}, "autoupdate": False,
                    "share": "disabled"}
    if judge:  # the judge answers from the prompt alone: every tool off and every permission denied
        config.update(tools={"*": False}, permission={"*": "deny"})
    return json.dumps(config, sort_keys=True)


def scratch_xdg(base: Path, auth: Path | None = None) -> dict:
    """Create the scratch XDG directories under base; auth: link <data>/opencode/auth.json to it (never read)."""
    dirs = {"XDG_CONFIG_HOME": base / "config", "XDG_DATA_HOME": base / "data", "XDG_STATE_HOME": base / "state",
            "XDG_CACHE_HOME": base / "cache"}
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    if auth is not None:
        link = dirs["XDG_DATA_HOME"] / "opencode/auth.json"
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(auth, link)
    return {key: str(path) for key, path in dirs.items()}


def unlink_auth(env: dict) -> None:
    link = Path(env["XDG_DATA_HOME"]) / "opencode/auth.json"
    if link.is_symlink():
        link.unlink()


def opencode_env(xdg: dict, model: str, judge: bool = False) -> dict:
    """The child's environment: basic variables only (no CLAUDE*/CODEX_*/FORGE_*/OPENCODE_* of the parent), the
    scratch XDG directories and the OpenCode isolation switches."""
    env = direct().child_env()
    env.update(xdg)
    env.update({"OPENCODE_DISABLE_CLAUDE_CODE": "1", "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
                "OPENCODE_CONFIG_CONTENT": config_content(model, judge)})
    return env


def isolation_problem(config: object, arm: str) -> str | None:
    """Check a run's `opencode debug config` JSON; None when the arm is isolated as designed. Forge's OpenCode setup
    edits no OpenCode config, so both arms must show the empty scratch config."""
    if not isinstance(config, dict):
        return "isolation: debug config is not a JSON object"
    if config.get("mcp"):
        return f"isolation: mcp servers {sorted(config['mcp'])[:5]}"
    if config.get("plugin"):
        return f"isolation: plugins {list(config['plugin'])[:5]}"
    if config.get("instructions"):
        return f"isolation: instructions {list(config['instructions'])[:5]} in the {arm} arm"
    if "default_agent" in config:
        return f"isolation: default_agent {config['default_agent']!r} in the {arm} arm"
    for key, empty in EMPTY_CONFIG.items():
        if config.get(key, empty) != empty:
            value = config[key]
            names = sorted(value)[:5] if isinstance(value, dict) else value
            return f"isolation: {key} {names} beyond an empty config in the {arm} arm"
    return None


def skill_problem(skills: object, arm: str, repo: Path, config_home: Path) -> str | None:
    """Check a run's `opencode debug skill` JSON and the activation line; None when the arm holds exactly its skills.
    Without arm: every listed skill is a built-in (location `<built-in>`), and no AGENTS.md from the repo up to /
    holds the line. With arm: the built-ins plus exactly one forge:boot located under the run's scratch config, and
    the line in the repo's AGENTS.md. Any other skill is a leak."""
    if not isinstance(skills, list) or not all(isinstance(s, dict) for s in skills):
        return "isolation: debug skill is not a JSON list of objects"
    boot = [s for s in skills if s.get("name") == BOOT_SKILL]
    other = [s for s in skills if s.get("name") != BOOT_SKILL and s.get("location") != BUILTIN]
    if other:
        return (f"isolation: skill {other[0].get('name')!r} at {other[0].get('location')!r} is not a built-in "
                f"in the {arm} arm")
    if arm == "without":
        if boot:
            return f"isolation: skill {BOOT_SKILL} at {boot[0].get('location')!r} in the without arm"
        if found := line_files(repo, up_to_root=True):
            return f"isolation: activation line in {found[0]} in the without arm"
        return None
    if len(boot) != 1:
        return f"isolation: {len(boot)} {BOOT_SKILL} skills in the with arm, not one"
    location = os.path.realpath(str(boot[0].get("location", "")))
    home = os.path.realpath(config_home)
    if not location.startswith(home + os.sep):
        return f"isolation: skill {BOOT_SKILL} at {location!r}, not under the run's scratch config {home}"
    if not line_files(repo, up_to_root=False):
        return f"isolation: no activation line in {Path(repo) / 'AGENTS.md'} in the with arm"
    return None


# --- Children ------------------------------------------------------------------------------------------------------


def run_process(cmd: list[str], cwd: Path, timeout: int, env: dict) -> tuple[str, str, bool, int | None]:
    """eval_engagement_direct.run_child's approach, with the return code: own process group, killed on timeout,
    partial output kept, stdin closed (opencode run reads a piped stdin into the message)."""
    process = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = process.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        try:
            out, err = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:  # a grandchild in its own session holds the pipes open
            for stream in (process.stdout, process.stderr):
                stream.close()
            out, err = b"", b""
        timed_out = True
    return (out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace"), timed_out,
            process.returncode)


def command(prompt: str, model: str, repo: Path, auto: bool = True) -> list[str]:
    return ["opencode", "run", "--format", "json", *(["--auto"] if auto else []), "-m", model, "--dir", str(repo),
            prompt]


def _debug(what: str, env: dict, repo: Path) -> tuple[object, str]:
    stdout, stderr, timed_out, code = run_process(["opencode", "debug", what], repo, 120, env)
    if timed_out or code != 0:
        return None, f"debug {what} failed (returncode {code}, timed_out={timed_out}): {stderr[-400:]}"
    try:
        return json.loads(stdout), ""
    except ValueError:
        return None, f"debug {what} is not JSON: {stdout[:200]}"


def debug_config(env: dict, repo: Path) -> tuple[object, str]:
    return _debug("config", env, repo)


def debug_skill(env: dict, repo: Path) -> tuple[object, str]:
    return _debug("skill", env, repo)


_HOSTS = "import json, sys; sys.path.insert(0, sys.argv[1]); import forge_setup; print(json.dumps(forge_setup.HOSTS))"


def setup_hosts(framework: Path) -> list[str]:
    """The hosts the framework copy's forge_setup serves."""
    result = subprocess.run([sys.executable, "-c", _HOSTS, str(framework / "scripts")], capture_output=True,
                            text=True, env=direct().child_env())
    if result.returncode != 0:
        raise RuntimeError(f"cannot read the framework copy's setup hosts: {result.stderr[-400:]}")
    return json.loads(result.stdout)


def install_entry(framework: Path, repo: Path, env: dict, home: Path) -> dict:
    """The with arm's OpenCode setup: the framework copy's forge_setup.py --host opencode project, in the run's
    environment (its scratch XDG directories) with a scratch HOME for this call. A failed setup, or one that did not
    place the boot skill, stops the runner: every with-arm run would measure the setup, not the session."""
    home.mkdir(parents=True, exist_ok=True)
    setup_env = {**env, "HOME": str(home)}
    cmd = [sys.executable, str(framework / SETUP), "--host", HOST, "project", "--project", str(repo)]
    result = subprocess.run(cmd, capture_output=True, text=True, env=setup_env, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        raise RuntimeError(f"forge_setup failed in {repo}: {result.stderr[-800:]}")
    done = json.loads(result.stdout)
    if not [e for e in done["written"] + done["unchanged"] if e["path"].endswith("/forge-boot/SKILL.md")]:
        raise RuntimeError(f"forge_setup placed no OpenCode boot skill for {repo}: {done['skipped']}")
    return done


def host_version(base: Path, model: str) -> str:
    env = opencode_env(scratch_xdg(base), model)
    stdout, stderr, _, _ = run_process(["opencode", "--version"], base, 60, env)
    return stdout.strip() or stderr.strip()


# --- Judge ---------------------------------------------------------------------------------------------------------


def judge_opencode(ee, case: dict, trace: dict, folder: Path, model: str, auth: Path = AUTH) -> dict | None:
    """The same hosted model, no tools, in an empty scratch folder; its last text is bound by validate_judgement."""
    exps = [e for e in case["expectations"] if e["check"]["type"] == "judge"]
    if not exps or not trace["completed"]:
        return {}
    work = folder / "judge"
    (work / "cwd").mkdir(parents=True)
    prompt = ee.JUDGE_PROMPT.format(expectations="\n".join(f"{e['id']}: {e['text']}" for e in exps),
                                    reply=trace["final"])
    env = opencode_env(scratch_xdg(work / "xdg", auth), model, judge=True)
    try:
        stdout, stderr, timed_out, code = run_process(command(prompt, model, work / "cwd", auto=False), work / "cwd",
                                                      300, env)
    finally:
        unlink_auth(env)
    (work / "raw.jsonl").write_text(stdout, encoding="utf-8")
    try:
        judged = normalize_opencode(stdout.splitlines(), {"returncode": code, "timed_out": timed_out, "model": model})
        if not judged["completed"]:
            raise ValueError(f"judge run incomplete: {judged['incomplete']}")
        return ee.validate_judgement(judged["final"], [e["id"] for e in exps])
    except ValueError as error:
        ee.write_json(work / "invalid.json", {"error": str(error), "stderr": stderr[-2000:]})
        return None


def judge(ee, case: dict, trace: dict, folder: Path, judge_host: str, judge_model: str, auth: Path = AUTH):
    if judge_host == "opencode":
        return judge_opencode(ee, case, trace, folder, judge_model, auth)
    return direct().judge(ee, case, trace, folder, judge_model)


# --- Runs ----------------------------------------------------------------------------------------------------------


def case_refusal(cases: list[dict]) -> str | None:
    refused = [c["id"] for c in cases if c.get("user_scope") or c.get("clean_start")]
    if not refused:
        return None
    return (f"the OpenCode runner cannot run {', '.join(refused)} (user_scope or clean_start: the project install "
            "carries no user scope, a clean start needs the Claude-side origins); list the cases to run with --case")


def out_problem(out: Path) -> str | None:
    """--out must not exist and must lie outside every Git work tree (and outside this checkout)."""
    out = out.resolve()
    if out.exists():
        return f"--out exists: {out}"
    if out == ROOT or ROOT in out.parents:
        return f"--out lies inside the repository: {out}"
    probe = out.parent
    while not probe.exists():
        probe = probe.parent
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    result = subprocess.run(["git", "-C", str(probe), "rev-parse", "--is-inside-work-tree"], capture_output=True,
                            text=True, env=env)
    if result.returncode == 0 and result.stdout.strip() == "true":
        return f"--out lies inside a Git work tree: {out}"
    return None


def run_case(ee, case: dict, out: Path, framework: Path, model: str, judge_host: str, judge_model: str,
             runs: int, auth: Path = AUTH) -> list[dict]:
    records = []
    for arm in ee.ARMS:
        for index in range(1, runs + 1):
            folder = out / HOST / "runs" / case["id"] / f"{arm}-{index}"
            folder.mkdir(parents=True)
            repo = Path(tempfile.mkdtemp(prefix=f"forge-engagement-{case['id']}-{arm}-"))
            ee.materialize(case, repo)
            xdg_base = folder / "xdg"
            env = opencode_env(scratch_xdg(xdg_base, auth), model)
            cmd = command(case["prompt"], model, repo)
            ee.write_json(folder / "launch.json", {
                "command": cmd, "repo": str(repo), "env_keys": sorted(env),
                "opencode_config_content": env["OPENCODE_CONFIG_CONTENT"], "xdg": str(xdg_base),
                "auth": f"symlink to {auth} (never read; removed after the run)",
                "max_turns": {"case": case["max_turns"], "enforced": False},
                "timeout_seconds": case["timeout_seconds"],
                "install": f"framework copy {SETUP} --host {HOST} project" if arm == "with" else None})
            started = time.time()
            try:
                if arm == "with":
                    ee.write_json(folder / "setup.json", install_entry(framework, repo, env, folder / "setup-home"))
                config, failure = debug_config(env, repo)
                ee.write_json(folder / "debug-config.json", config if config is not None else {"error": failure})
                problem = f"isolation: {failure}" if failure else isolation_problem(config, arm)
                if not problem:
                    skills, failure = debug_skill(env, repo)
                    ee.write_json(folder / "debug-skill.json", skills if skills is not None else {"error": failure})
                    problem = (f"isolation: {failure}" if failure
                               else skill_problem(skills, arm, repo, Path(env["XDG_CONFIG_HOME"])))
                stdout = stderr = ""
                if problem:
                    execution = {"returncode": None, "timed_out": False, "model": model}
                else:
                    stdout, stderr, timed_out, code = run_process(cmd, repo, case["timeout_seconds"], env)
                    execution = {"returncode": code, "timed_out": timed_out, "model": model}
            finally:
                unlink_auth(env)
            (folder / "trace.jsonl").write_text(stdout, encoding="utf-8")
            (folder / "stderr.txt").write_text(stderr, encoding="utf-8")
            trace = normalize_opencode(stdout.splitlines(), execution)
            trace["wall_seconds"] = round(time.time() - started, 1)
            trace["roots"] = ee.run_roots(repo, framework, None, host_home=xdg_base)
            trace["files"] = ee.record_files(case, repo)
            if problem:
                trace.update(completed=False, incomplete=problem)
            judged = judge(ee, case, trace, folder, judge_host, judge_model, auth)
            record = {"host": HOST, "runner": RUNNER, "case": case["id"], "arm": arm, "run": index,
                      "repo": str(repo), "trace": trace}
            record["grade"] = ee.grade_run(case, arm, trace, judged)
            ee.write_json(folder / "record.json", record)
            records.append(record)
            print(f"{case['id']} {arm}-{index}: scored={record['grade']['scored']} "
                  f"reason={record['grade']['reason']} wall={trace['wall_seconds']}s", flush=True)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="results directory outside Git (must not exist)")
    parser.add_argument("--model", required=True, help="pinned provider/model id, e.g. nvidia/poolside/laguna-xs-2.1")
    parser.add_argument("--judge-host", choices=("claude", "opencode"), default="claude")
    parser.add_argument("--judge-model", help="default: claude-haiku-5-5 for claude, --model for opencode")
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--framework-source", type=Path, default=ROOT,
                        help="Git checkout whose committed HEAD the framework copy is archived from")
    args = parser.parse_args(argv)
    args.out = args.out.resolve()
    judge_model = args.judge_model or ("claude-haiku-5-5" if args.judge_host == "claude" else args.model)
    if problem := out_problem(args.out):
        parser.error(problem)
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    if not os.path.lexists(AUTH):
        parser.error(f"no OpenCode login at {AUTH} (run `opencode auth login` first)")
    ee = engagement()
    cases = ee.load_cases(only=args.cases)
    if refusal := case_refusal(cases):
        parser.error(refusal)
    framework = args.out / "forge"
    commit = ee.export_framework(framework, args.framework_source)
    if HOST not in (hosts := setup_hosts(framework)):
        parser.error(f"the framework copy's forge_setup serves {hosts}, not {HOST}; commit the OpenCode setup "
                     "in --framework-source first")
    ee.write_json(args.out / "framework.json", {"source": str(args.framework_source), "commit": commit})
    version = host_version(args.out / HOST / "version-xdg", args.model)
    ee.write_json(args.out / HOST / "launch.json", {
        "runner": RUNNER, "host_version": version, "model": args.model, "judge_host": args.judge_host,
        "judge_model": judge_model, "install_source": "framework copy scripts/forge_setup.py --host opencode project",
        "env_keys_set": ["XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME",
                         "OPENCODE_DISABLE_CLAUDE_CODE", "OPENCODE_DISABLE_EXTERNAL_SKILLS",
                         "OPENCODE_CONFIG_CONTENT", "FORGE_USER_CONFIG", "PYTHONDONTWRITEBYTECODE"],
        "limits": LIMITS, "max_turns": {c["id"]: c["max_turns"] for c in cases}})
    records = []
    for case in cases:
        records += run_case(ee, case, args.out, framework, args.model, args.judge_host, judge_model, args.runs)
    print(json.dumps(ee.report(records, cases, args.out, HOST), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
