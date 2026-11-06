#!/usr/bin/env python3
"""Forge's setup writer: every deterministic fact and write of the plugin setup (skills/setup/SKILL.md).

The agent decides in conversation (which scope, which folder); this script gathers the facts and does the writes:
the project's activation line, the machine setting (user.yaml), Codex's AGENTS.md line, Claude Code's two Read
allow rules, OpenCode's boot skill and AGENTS.md line, and the user-scope scaffold. user_scope.py stays the reader;
this script imports its constants and readers and re-implements none of them.

CLI: forge_setup.py [--dry-run] [--host claude-code|codex|opencode]... <command> [options]
  status [--project DIR]                         facts as JSON, writes nothing
  project --project DIR [--off]                  the activation line in DIR/AGENTS.md (+ Claude's rules)
  every-session [--user-repo PATH] [--create-user-repo] | every-session --off
  remove [--project DIR]...                      everything this script wrote
  offer-check [--project DIR]                    the one-time setup offer line (plain text, never JSON)
Writing commands print one JSON object {command, dry_run, written, unchanged, skipped, notes}. Exit 0 on success
(also when nothing changed), 2 on a refusal or usage error (stderr names the file and reason; nothing written:
every target is read and checked before the first write).
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

try:
    from .user_scope import (
        _LINE_SPACE,
        ACTIVATION_FILE,
        ACTIVATION_LINE,
        BUDDY_EVERY_SESSION,
        BUDDY_KEY,
        USER_SCOPE_SCAFFOLD,
        _inside,
        activation_found,
        config_path,
        from_config,
        has_activation_line,
        load_config,
        resolve,
        switch_on,
        unusable_setting,
    )
except ImportError:
    from user_scope import (
        _LINE_SPACE,
        ACTIVATION_FILE,
        ACTIVATION_LINE,
        BUDDY_EVERY_SESSION,
        BUDDY_KEY,
        USER_SCOPE_SCAFFOLD,
        _inside,
        activation_found,
        config_path,
        from_config,
        has_activation_line,
        load_config,
        resolve,
        switch_on,
        unusable_setting,
    )

FRAMEWORK = Path(__file__).resolve().parents[1]
HOSTS = ("claude-code", "codex", "opencode")
PLUGIN_ID = "forge@forge"
PLUGIN_MANIFEST = Path(".claude-plugin") / "plugin.json"
LINE = ACTIVATION_LINE.encode("utf-8")
OFFER_LINE = (
    "Forge setup: Buddy is not switched on here. Offer the user the forge:setup skill "
    "(project only or every session) once."
)
SETTING_REMOVABLE = {"version", "user_repo"}  # remove deletes a setting that holds only these keys


class Refusal(Exception):
    """A command that will not run; the message names the file and the reason."""


# --- locations -------------------------------------------------------------------------------------------------


def _env_dir(name: str, default: str) -> Path:
    value = os.environ.get(name)
    return Path(os.path.abspath(os.path.expanduser(value or default)))


def claude_dir() -> Path:
    return _env_dir("CLAUDE_CONFIG_DIR", "~/.claude")


def codex_dir() -> Path:
    return _env_dir("CODEX_HOME", "~/.codex")


def opencode_dir() -> Path:
    """OpenCode's global config folder: $XDG_CONFIG_HOME/opencode (absolute values only), else ~/.config/opencode."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg and os.path.isabs(xdg) else Path(os.path.expanduser("~/.config"))
    return Path(os.path.abspath(base)) / "opencode"


def opencode_skill_path() -> Path:
    return opencode_dir() / "skills" / "forge-boot" / "SKILL.md"


def opencode_cli() -> str | None:
    """OpenCode has no plugin: it counts as found when its CLI is on PATH."""
    return shutil.which("opencode")


def state_dir() -> Path:
    xdg = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg) if xdg and os.path.isabs(xdg) else Path(os.path.expanduser("~/.local/state"))
    return base / "forge"


def record_path() -> Path:
    return state_dir() / "setup.json"


def marker_path() -> Path:
    return state_dir() / "setup-offered"


def norm(path: str | Path) -> Path:
    return Path(os.path.normpath(os.path.abspath(os.path.expanduser(str(path)))))


def _is_root(path: object) -> bool:
    return isinstance(path, str) and bool(path) and os.path.isfile(Path(path) / PLUGIN_MANIFEST)


@functools.lru_cache(maxsize=None)
def claude_root() -> Path | None:
    """`claude plugin list --json`, entry forge@forge (readFromFolder, else installPath); fallback when the CLI is
    missing or yields no plugin root: installed_plugins.json. A root counts only when it holds the manifest."""
    cli = shutil.which("claude")
    if cli:
        try:
            done = subprocess.run(
                [cli, "plugin", "list", "--json"], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                timeout=30,
            )
            entries = json.loads(done.stdout) if done.returncode == 0 else []
        except (OSError, subprocess.SubprocessError, ValueError):
            entries = []
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and entry.get("id") == PLUGIN_ID:
                root = entry.get("readFromFolder") or entry.get("installPath")
                if _is_root(root):
                    return norm(root)
    try:
        installed = json.loads((claude_dir() / "plugins" / "installed_plugins.json").read_text(encoding="utf-8"))
        root = installed["plugins"][PLUGIN_ID][0]["installPath"]
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return None
    return norm(root) if _is_root(root) else None


def codex_root() -> Path | None:
    root = codex_dir() / "plugins" / "cache" / "forge" / "forge" / "local"
    return root if _is_root(str(root)) else None


def in_claude_cache(root: Path) -> bool:
    """True when root lies inside Claude Code's plugin cache (a versioned folder a plugin update replaces)."""
    cache = claude_dir() / "plugins" / "cache"
    return _inside(root, cache) and os.path.realpath(root) != os.path.realpath(cache)


def opencode_root() -> tuple[Path, str | None]:
    """The framework root OpenCode's boot skill names, and a note when that root is a versioned plugin folder.
    FRAMEWORK, unless it lies in Claude's plugin cache: then Codex's stable folder when present, else FRAMEWORK."""
    if not in_claude_cache(FRAMEWORK):
        return FRAMEWORK, None
    croot = codex_root()
    if croot is not None:
        return croot, None
    return FRAMEWORK, (f"OpenCode's boot skill names {FRAMEWORK}, a versioned Claude Code plugin folder; run this "
                       "setup again after a plugin update")


def read_rule(path: Path) -> str:
    """The host's form: an absolute path /a/b gives Read(//a/b/**)."""
    return "Read(/" + str(norm(path)) + "/**)"


def root_rule(root: Path) -> str:
    """A root inside the host's plugin cache gets the rule on its version-independent parent."""
    return read_rule(root.parent if in_claude_cache(root) else root)


def usable_repo(path: Path) -> bool:
    """A usable user repo, as the reader decides it (a folder holding context/user/)."""
    return from_config(FRAMEWORK, {"version": 1, "user_repo": str(path)}).configured


def configured_repo() -> Path | None:
    scope = resolve(FRAMEWORK, env=os.environ)
    return Path(scope.user_repo) if scope.configured and scope.user_repo else None


# --- the plan: every target read and checked before the first write ----------------------------------------------


def _read(path: Path) -> bytes | None:
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise Refusal(f"{path}: cannot read ({exc.__class__.__name__})") from exc


def _read_quiet(path: Path) -> bytes | None:
    try:
        return None if os.path.islink(path) else _read(path)
    except Refusal:
        return None


def _umask() -> int:
    old = os.umask(0)
    os.umask(old)
    return old


def write_atomic(path: Path, data: bytes) -> None:
    """Write at the resolved target (a symlink stays a link), keeping the file mode; temp file + os.replace."""
    real = os.path.realpath(path)
    folder = os.path.dirname(real)
    os.makedirs(folder, exist_ok=True)
    try:
        mode = stat.S_IMODE(os.stat(real).st_mode)
    except FileNotFoundError:
        mode = 0o666 & ~_umask()
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".forge-setup-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, real)
    except BaseException:
        if os.path.lexists(tmp):
            os.unlink(tmp)
        raise


class Plan:
    def __init__(self, command: str, dry_run: bool, hosts: list[str]) -> None:
        self.command, self.dry_run, self.hosts = command, dry_run, hosts
        self.originals: dict[str, bytes | None] = {}
        self.files: dict[str, bytes | None] = {}
        self.written: list[dict] = []
        self.unchanged: list[dict] = []
        self.skipped: list[dict] = []
        self.notes: list[str] = []
        self.prune: list[str] = []  # folders removed after the writes when they are left empty

    def read(self, path: Path) -> bytes | None:
        key = str(path)
        if key in self.files:
            return self.files[key]
        if key not in self.originals:
            self.originals[key] = _read(path)
        return self.originals[key]

    def put(self, path: Path, data: bytes | None, what: str) -> None:
        self.read(path)
        self.files[str(path)] = data
        self.written.append({"path": str(path), "what": what})

    def same(self, path: Path, what: str) -> None:
        self.unchanged.append({"path": str(path), "what": what})

    def skip(self, path: Path, why: str) -> None:
        self.skipped.append({"path": str(path), "what": why})

    def host(self, name: str) -> bool:
        return name in self.hosts

    def remove(self, path: Path, reduced: bytes, what: str) -> None:
        """Delete a file; a symlink is never unlinked: its target gets the reduced content and the link stays."""
        if os.path.islink(path):
            self.put(path, reduced, what + " (a link: its target emptied of Forge's content, the link kept)")
        else:
            self.put(path, None, what)

    def apply(self, done: list[str]) -> None:
        """Write in plan order, appending each written path to `done`; the first OS error stops the run."""
        for key, data in self.files.items():
            if data == self.originals.get(key):
                continue
            if data is None:
                if os.path.lexists(key):
                    os.unlink(key)
            else:
                write_atomic(Path(key), data)
            done.append(key)
        for folder in self.prune:
            try:
                if os.path.isdir(folder) and not os.path.islink(folder) and not os.listdir(folder):
                    os.rmdir(folder)
            except OSError:
                pass

    def result(self) -> dict:
        return {
            "command": self.command, "dry_run": self.dry_run, "written": self.written,
            "unchanged": self.unchanged, "skipped": self.skipped, "notes": self.notes,
        }


# --- activation lines ------------------------------------------------------------------------------------------


def _lines(data: bytes) -> list[bytes]:
    parts = data.split(b"\n")
    return [part + b"\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _is_line(line: bytes) -> bool:
    return line.strip(_LINE_SPACE) == LINE


def add_line(plan: Plan, path: Path) -> dict | None:
    """Append the activation line unless the file holds it; the record entry of an added line, else None."""
    if has_activation_line(path):
        plan.same(path, "activation line already present")
        return None
    data = plan.read(path)
    if data is None:
        plan.put(path, LINE + b"\n", "file created with the activation line")
        return {"path": str(path), "created": not os.path.lexists(path), "separator": False}
    eol = b"\r\n" if b"\r\n" in data else b"\n"
    separator = bool(data) and not data.endswith(b"\n")
    plan.put(path, data + (eol if separator else b"") + LINE + eol, "activation line appended")
    return {"path": str(path), "created": False, "separator": separator}


def drop_line(plan: Plan, path: Path, entry: dict | None) -> None:
    """Remove every activation line, the separator this script added, and a file it created that is now empty."""
    data = plan.read(path)
    lines = _lines(data) if data is not None else []
    if not any(_is_line(line) for line in lines):
        plan.same(path, "no activation line")
        return
    out = b"".join(line for line in lines if not _is_line(line))
    if entry and entry.get("separator") and _is_line(lines[-1]):
        for eol in (b"\r\n", b"\n"):
            if out.endswith(eol):
                out = out[: -len(eol)]
                break
    if entry and entry.get("created") and not out.strip(_LINE_SPACE):
        plan.remove(path, out, "file removed (it held only the activation line)")
    else:
        plan.put(path, out, "activation line removed")


# --- Claude settings -------------------------------------------------------------------------------------------


def settings_path() -> Path:
    return claude_dir() / "settings.json"


def load_settings(plan: Plan) -> dict | None:
    """The settings object; None when the file is missing. Refuses on anything it cannot edit safely."""
    path = settings_path()
    data = plan.read(path)
    if data is None:
        return None
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise Refusal(f"{path}: not valid JSON ({exc.__class__.__name__})") from exc
    if not isinstance(obj, dict):
        raise Refusal(f"{path}: not a JSON object")
    perms = obj.get("permissions", {})
    if not isinstance(perms, dict):
        raise Refusal(f"{path}: permissions is not an object")
    if not isinstance(perms.get("allow", []), list):
        raise Refusal(f"{path}: permissions.allow is not a list")
    return obj


def _dump_settings(obj: dict) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def add_rules(plan: Plan, record: dict, rules: list[str]) -> None:
    path = settings_path()
    obj = load_settings(plan)
    created = not os.path.lexists(path)
    obj = {} if obj is None else obj
    perms_created = "permissions" not in obj
    allow_created = perms_created or "allow" not in obj["permissions"]
    allow = obj.get("permissions", {}).get("allow", [])
    missing = [rule for rule in dict.fromkeys(rules) if rule not in allow]
    for rule in rules:
        if rule in allow:
            plan.same(path, f"rule present: {rule}")
    if not missing:
        return
    obj.setdefault("permissions", {}).setdefault("allow", []).extend(missing)
    plan.put(path, _dump_settings(obj), "rules added: " + ", ".join(missing))
    record["rules"] = list(dict.fromkeys(record["rules"] + missing))
    record["settings_created"] = record["settings_created"] or created
    record["permissions_created"] = record["permissions_created"] or perms_created
    record["allow_created"] = record["allow_created"] or allow_created


def drop_rules(plan: Plan, record: dict, rules: list[str]) -> None:
    path = settings_path()
    obj = load_settings(plan)
    gone = set(rules)
    created, made = record["settings_created"], (record["permissions_created"], record["allow_created"])
    record["rules"] = [rule for rule in record["rules"] if rule not in gone]
    if not record["rules"]:
        record.update(settings_created=False, permissions_created=False, allow_created=False)
    perms = obj.get("permissions") if obj else None
    allow = perms.get("allow", []) if perms else []
    found = [rule for rule in allow if rule in gone]
    if not found:
        if obj is not None:
            plan.same(path, "no Forge rule")
        return
    perms["allow"] = [rule for rule in allow if rule not in gone]
    if not perms["allow"] and made[1]:
        del perms["allow"]
        if not perms and made[0]:
            del obj["permissions"]
    if not obj and created:
        plan.remove(path, _dump_settings(obj), "file removed (it held only Forge's rules)")
    else:
        plan.put(path, _dump_settings(obj), "rules removed: " + ", ".join(dict.fromkeys(found)))


# --- OpenCode's boot skill ------------------------------------------------------------------------------------


def render_opencode_skill(root: Path) -> bytes:
    """The boot skill OpenCode lists as forge:boot: it points at the boot entry and the plugin's boot skill and
    copies none of their prose."""
    root = norm(root)
    quoted = shlex.quote(str(root))
    text = (
        "---\n"
        "name: forge:boot\n"
        "description: >\n"
        "  Start Buddy, Forge's orchestrator, on OpenCode. Use when the project's or\n"
        "  the user's AGENTS.md asks for the forge:boot skill before the first answer.\n"
        "---\n"
        "\n"
        "# Skill: forge:boot (OpenCode)\n"
        "\n"
        f"Forge's setup wrote this file; `python3 {shlex.quote(str(root / 'scripts' / 'forge_setup.py'))} remove` "
        "takes it out.\n"
        "\n"
        f"Framework root: `{root}`\n"
        "\n"
        "Run, as its own call, and follow the printed entry before the first answer:\n"
        "\n"
        f"`python3 {shlex.quote(str(root / 'scripts' / 'user_scope.py'))} --framework-root {quoted} --boot-entry`\n"
        "\n"
        "The rest of the procedure (whether the boot is already running, what to do when the command fails) is in "
        f"`{root / 'skills' / 'boot' / 'SKILL.md'}`.\n"
    )
    return text.encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _owned(record: dict, path: Path, data: bytes) -> bool:
    """True when the record owns path and data matches any hash it lists (an interrupted update lists several)."""
    entry = record["opencode_skill"]
    return bool(entry) and entry["path"] == str(path) and _sha(data) in entry["sha256"]


def write_skill(plan: Plan, record: dict) -> None:
    """Write the boot skill: missing → written, equal → unchanged, Forge's earlier render → updated; anything else
    (an edited or foreign file, a link) refuses before the first write."""
    path = opencode_skill_path()
    if os.path.islink(path):
        raise Refusal(f"{path}: a link; Forge's OpenCode boot skill is written only as a file of its own")
    root, note = opencode_root()
    if note:
        plan.notes.append(note)
    want = render_opencode_skill(root)
    data = plan.read(path)
    if data == want:
        plan.same(path, "OpenCode boot skill present")
    elif data is None:
        plan.put(path, want, "OpenCode boot skill written")
    elif _owned(record, path, data):
        plan.put(path, want, "OpenCode boot skill updated")
    else:
        raise Refusal(f"{path}: holds content Forge's setup did not write (edited, or another forge-boot skill)")
    record["opencode_skill"] = {"path": str(path), "sha256": [_sha(want)]}


def drop_skill(plan: Plan, record: dict) -> None:
    """Delete the boot skill when its bytes are Forge's (a recorded hash or the current render); keep an edited one
    or a link with a note. Its forge-boot folder is pruned when left empty; the skills folder never is."""
    entry = record["opencode_skill"]
    path = Path(entry["path"]) if entry else opencode_skill_path()
    record["opencode_skill"] = None
    if os.path.islink(path):
        plan.notes.append(f"{path}: a link, kept (Forge's setup writes no link there)")
        return
    data = plan.read(path)
    if data is None:
        return
    if data == render_opencode_skill(opencode_root()[0]) or (entry and _sha(data) in entry["sha256"]):
        plan.put(path, None, "OpenCode boot skill removed")
        plan.prune.append(str(path.parent))
    else:
        plan.notes.append(f"{path}: edited after Forge's setup wrote it, kept; delete it by hand if it is not wanted")


def opencode_agents(record: dict) -> Path:
    """OpenCode's global AGENTS.md: the recorded one, else the current location."""
    return Path(record["opencode"]["path"]) if record["opencode"] else opencode_dir() / ACTIVATION_FILE


def opencode_parts(plan: Plan, record: dict, every_session: bool) -> None:
    """OpenCode's share: the boot skill and, for every session, the line in its global AGENTS.md."""
    skill, agents = opencode_skill_path(), opencode_dir() / ACTIVATION_FILE
    if not plan.host("opencode"):
        plan.skip(skill, "opencode not selected (--host)")
        return
    if opencode_cli() is None:
        plan.skip(skill, "OpenCode not found (no opencode on PATH)")
        return
    write_skill(plan, record)
    if every_session:
        added = add_line(plan, agents)
        if added:
            record["opencode"] = added


# --- the machine setting ---------------------------------------------------------------------------------------


def need_yaml():
    try:
        import yaml
    except ImportError as exc:
        raise Refusal("PyYAML missing (install it with pip install pyyaml)") from exc
    return yaml


def load_setting(plan: Plan) -> tuple[Path, dict | None]:
    path = config_path(os.environ)
    if path is None:
        raise Refusal("HOME not set: no machine setting path")
    warning = unusable_setting(os.environ)
    if warning:
        raise Refusal(f"{path}: {warning}")
    if plan.read(path) is None:
        return path, None
    return path, load_config(path)[0]


def put_setting(plan: Plan, path: Path, data: dict, what: str) -> None:
    yaml = need_yaml()
    raw = plan.read(path) or b""
    if any(line.lstrip().startswith(b"#") or b" #" in line for line in raw.splitlines()):
        plan.notes.append(f"comments in {path} are not kept (its keys and values are)")
    text = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    plan.put(path, text.encode("utf-8"), what)


# --- the ownership record --------------------------------------------------------------------------------------


def empty_record() -> dict:
    return {"version": 1, "projects": [], "codex": None, "opencode": None, "opencode_skill": None, "rules": [],
            "settings_created": False, "permissions_created": False, "allow_created": False}


def load_record() -> dict:
    record = empty_record()
    try:
        data = json.loads(record_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return record
    if not isinstance(data, dict):
        return record
    entry_ok = lambda e: isinstance(e, dict) and isinstance(e.get("path"), str)  # noqa: E731
    record["projects"] = [e for e in data.get("projects", []) if entry_ok(e)] if isinstance(
        data.get("projects"), list) else []
    record["codex"] = data["codex"] if entry_ok(data.get("codex")) else None
    record["opencode"] = data["opencode"] if entry_ok(data.get("opencode")) else None
    skill = data.get("opencode_skill")
    if entry_ok(skill):
        hashes = skill.get("sha256")
        hashes = [hashes] if isinstance(hashes, str) else hashes  # an older record: one hash as a string
        if isinstance(hashes, list) and hashes and all(isinstance(h, str) for h in hashes):
            record["opencode_skill"] = {"path": skill["path"], "sha256": list(dict.fromkeys(hashes))}
    record["rules"] = [r for r in data.get("rules", []) if isinstance(r, str)] if isinstance(
        data.get("rules"), list) else []
    for flag in ("settings_created", "permissions_created", "allow_created"):
        record[flag] = data.get(flag) is True
    return record


def save_record(plan: Plan, before: dict, record: dict) -> None:
    if record == before:
        return
    path = record_path()
    if record == empty_record():
        if plan.read(path) is not None:
            plan.put(path, None, "ownership record cleared")
        return
    plan.put(path, (json.dumps(record, indent=2) + "\n").encode("utf-8"), "ownership record updated")


def union_record(before: dict, after: dict) -> dict:
    """Everything either record owns: written before the targets, so `remove` can undo a run that failed midway."""
    projects = {e["path"]: e for e in before["projects"]}
    projects.update({e["path"]: e for e in after["projects"]})
    merged = {"version": 1, "projects": list(projects.values()), "codex": after["codex"] or before["codex"],
              "opencode": after["opencode"] or before["opencode"],
              "opencode_skill": _union_skill(before["opencode_skill"], after["opencode_skill"]),
              "rules": list(dict.fromkeys(before["rules"] + after["rules"]))}
    for flag in ("settings_created", "permissions_created", "allow_created"):
        merged[flag] = before[flag] or after[flag]
    return merged


def _union_skill(before: dict | None, after: dict | None) -> dict | None:
    """Every hash either record owns for the same skill path: until the file on disk matches one, Forge owns it."""
    if before and after and before["path"] == after["path"]:
        return {"path": after["path"], "sha256": list(dict.fromkeys(before["sha256"] + after["sha256"]))}
    return after or before


def _entry(entries: list[dict], path: Path) -> dict | None:
    return next((e for e in entries if e["path"] == str(path)), None)


def _without(entries: list[dict], path: Path) -> list[dict]:
    return [e for e in entries if e["path"] != str(path)]


# --- commands --------------------------------------------------------------------------------------------------


def project_dir_arg(value: str) -> Path:
    path = norm(value)
    if not path.is_dir():
        raise Refusal(f"{path}: project folder not found")
    return path


def claude_rules(plan: Plan, record: dict, repo: Path | None, repo_required: bool) -> None:
    """Claude's share: the plugin-root rule and, with a usable user repo, its rule."""
    path = settings_path()
    if not plan.host("claude-code"):
        plan.skip(path, "claude-code not selected (--host)")
        return
    root = claude_root()
    if root is None:
        plan.skip(path, "Claude Code plugin not found")
        if repo_required:
            plan.skip(path, "user-repo rule skipped: Claude Code plugin not found")
        return
    add_rules(plan, record, [root_rule(root)] + ([read_rule(repo)] if repo else []))


def cmd_project(args, plan: Plan, record: dict) -> None:
    agents = project_dir_arg(args.project[0]) / ACTIVATION_FILE
    entry = _entry(record["projects"], agents)
    if args.off:
        drop_line(plan, agents, entry)
        record["projects"] = _without(record["projects"], agents)
        return
    added = add_line(plan, agents)
    if added:
        record["projects"] = _without(record["projects"], agents) + [added]
    found = ((plan.host("claude-code") and claude_root()) or (plan.host("codex") and codex_root())
             or (plan.host("opencode") and opencode_cli()))
    if not found:
        plan.notes.append("no selected host found (no Forge plugin on Claude Code or Codex, no opencode on PATH); "
                          "the line takes effect once one is installed")
    claude_rules(plan, record, configured_repo(), repo_required=False)
    opencode_parts(plan, record, every_session=False)


def cmd_every_session(args, plan: Plan, record: dict) -> None:
    need_yaml()
    setting, data = load_setting(plan)
    codex_agents = codex_dir() / ACTIVATION_FILE
    if args.off:
        if data is not None and BUDDY_KEY in data:
            put_setting(plan, setting, {k: v for k, v in data.items() if k != BUDDY_KEY}, "Buddy switch removed")
        else:
            plan.same(setting, "Buddy switch not set")
        if plan.host("codex"):
            drop_line(plan, codex_agents, record["codex"])
            record["codex"] = None
        if plan.host("opencode"):  # the boot skill stays: projects may still carry the line
            drop_line(plan, opencode_agents(record), record["opencode"])
            record["opencode"] = None
        return
    if args.user_repo:
        repo = norm(args.user_repo)
    else:
        repo = configured_repo()
        if repo is None:
            raise Refusal(f"{setting}: names no usable user repo; pass --user-repo PATH")
    if not usable_repo(repo):
        if not args.create_user_repo:
            raise Refusal(f"{repo}: holds no context/user/ folder; pass --create-user-repo to create it")
        for path in (repo, repo / "context", repo / "context" / "user"):
            if os.path.lexists(path) and not path.is_dir():
                raise Refusal(f"{path}: exists and is not a folder")
    if args.create_user_repo:
        for name, text in USER_SCOPE_SCAFFOLD.items():
            path = repo / "context" / "user" / name
            if os.path.lexists(path):
                plan.same(path, "user-scope file present, kept")
            else:
                plan.put(path, text.encode("utf-8"), "user-scope scaffold (headings only)")
    wanted = dict(data or {})
    wanted.update({"version": 1, "user_repo": str(repo), BUDDY_KEY: BUDDY_EVERY_SESSION})
    if wanted != data:
        put_setting(plan, setting, wanted, f"machine setting: user_repo {repo}, buddy: every-session")
    else:
        plan.same(setting, "machine setting already names this user repo with the switch on")
    if not plan.host("codex"):
        plan.skip(codex_agents, "codex not selected (--host)")
    elif codex_root() is None:
        plan.skip(codex_agents, "Codex plugin not found")
    else:
        added = add_line(plan, codex_agents)
        if added:
            record["codex"] = added
    claude_rules(plan, record, repo, repo_required=True)
    opencode_parts(plan, record, every_session=True)


def cmd_remove(args, plan: Plan, record: dict) -> None:
    need_yaml()
    setting, data = load_setting(plan)
    named = [project_dir_arg(value) / ACTIVATION_FILE for value in args.project or []]
    for agents in dict.fromkeys(named + [Path(e["path"]) for e in record["projects"]]):
        drop_line(plan, agents, _entry(record["projects"], agents))
        record["projects"] = _without(record["projects"], agents)
    repo = data.get("user_repo") if data else None
    if data is not None:
        rest = {k: v for k, v in data.items() if k != BUDDY_KEY}
        if set(rest) <= SETTING_REMOVABLE:
            if os.path.islink(setting):
                put_setting(plan, setting, rest, "machine setting reduced at the link's target, the link kept")
            else:
                plan.put(setting, None, "machine setting removed")
        elif rest != data:
            put_setting(plan, setting, rest, "Buddy switch removed")
        else:
            plan.same(setting, "machine setting keeps keys of its own")
    if plan.host("codex"):
        codex_agents = Path(record["codex"]["path"]) if record["codex"] else codex_dir() / ACTIVATION_FILE
        drop_line(plan, codex_agents, record["codex"])
        record["codex"] = None
    if plan.host("claude-code"):
        rules = list(record["rules"])
        root = claude_root()
        if root is not None:
            rules.append(root_rule(root))
        if isinstance(repo, str) and os.path.isabs(repo):
            rules.append(read_rule(Path(repo)))
        drop_rules(plan, record, rules)
    if plan.host("opencode"):
        drop_line(plan, opencode_agents(record), record["opencode"])
        record["opencode"] = None
        drop_skill(plan, record)
    if os.path.lexists(marker_path()):
        plan.put(marker_path(), None, "offer marker removed")


def cmd_status(args) -> dict:
    root, croot = claude_root(), codex_root()
    skill, oc_root = opencode_skill_path(), opencode_root()[0]
    setting = config_path(os.environ)
    data = None
    if setting is not None and os.path.lexists(setting):
        data = load_config(setting)[0]
    warning = unusable_setting(os.environ)
    repo = configured_repo()
    try:
        obj = load_settings(Plan("status", True, []))
    except Refusal:
        obj = None
    allow = (obj or {}).get("permissions", {}).get("allow", [])
    rule = root_rule(root) if root else None
    user_rule = read_rule(repo) if repo else None
    project = None
    if args.project:
        folder = norm(args.project[0])
        agents = folder / ACTIVATION_FILE
        line = has_activation_line(agents)
        project = {"dir": str(folder), "agents_md": str(agents), "line": line,
                   "line_inherited": not line and activation_found(folder)}
    user_repo = data.get("user_repo") if data else None
    return {
        "hosts": {
            "claude-code": {
                "cli": shutil.which("claude"), "plugin_root": str(root) if root else None,
                "settings": str(settings_path()),
                "rules": {"plugin_root": rule, "plugin_root_present": rule is not None and rule in allow,
                          "user_repo": user_rule, "user_repo_present": user_rule is not None and user_rule in allow},
            },
            "codex": {
                "cli": shutil.which("codex"), "plugin_root": str(croot) if croot else None,
                "agents_md": str(codex_dir() / ACTIVATION_FILE),
                "line": has_activation_line(codex_dir() / ACTIVATION_FILE),
            },
            "opencode": {
                "cli": opencode_cli(), "framework_root": str(oc_root), "skill": str(skill),
                "skill_present": _read_quiet(skill) == render_opencode_skill(oc_root),
                "agents_md": str(opencode_dir() / ACTIVATION_FILE),
                "line": has_activation_line(opencode_dir() / ACTIVATION_FILE),
            },
        },
        "setting": {
            "path": str(setting) if setting else None, "exists": bool(setting and os.path.lexists(setting)),
            "usable": warning is None, "warning": warning,
            "user_repo": user_repo if isinstance(user_repo, str) else None,
            "user_repo_ready": repo is not None, "switch": switch_on(data),
        },
        "project": project,
        "offered": os.path.lexists(marker_path()),
        "record": str(record_path()),
    }


def offer_check(args) -> None:
    """Print the offer once per machine, only after its marker was written; any error prints nothing."""
    try:
        folder = Path(args.project[0]) if args.project else Path(os.getcwd())
        marker = marker_path()
        if os.path.lexists(marker) or activation_found(norm(folder)):
            return
        setting = config_path(os.environ)
        if setting is not None and os.path.lexists(setting):
            data, _ = load_config(setting)
            if data is None or switch_on(data):
                return
        marker.parent.mkdir(parents=True, exist_ok=True)
        with open(marker, "x"):
            pass
    except (OSError, ValueError):
        return
    print(OFFER_LINE)


# --- CLI -------------------------------------------------------------------------------------------------------


def _common(host_dest: str) -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS,
                        help="compute and print the changes, write nothing")
    common.add_argument("--host", action="append", choices=HOSTS, default=[], dest=host_dest,
                        help="limit the hosts written (repeatable)")
    return common


def parser() -> argparse.ArgumentParser:
    """--dry-run and --host before or after the subcommand; the --host lists of both places are merged."""
    top = argparse.ArgumentParser(description=__doc__.splitlines()[0], parents=[_common("host")])
    sub = top.add_subparsers(dest="command", required=True)
    for name in ("status", "project", "every-session", "remove", "offer-check"):
        cmd = sub.add_parser(name, parents=[_common("host_sub")])
        if name == "project":
            cmd.add_argument("--project", action="append", required=True)
        elif name != "every-session":
            cmd.add_argument("--project", action="append", default=[])
        if name in ("project", "every-session"):
            cmd.add_argument("--off", action="store_true")
        if name == "every-session":
            cmd.add_argument("--user-repo")
            cmd.add_argument("--create-user-repo", action="store_true")
    return top


COMMANDS = {"project": cmd_project, "every-session": cmd_every_session, "remove": cmd_remove}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "offer-check":
        offer_check(args)
        return 0
    if args.command == "status":
        print(json.dumps(cmd_status(args), indent=2))
        return 0
    if args.command == "project" and len(args.project) > 1:
        print("forge setup: project takes one --project", file=sys.stderr)
        return 2
    hosts = list(dict.fromkeys(args.host + args.host_sub)) or list(HOSTS)
    plan = Plan(args.command, getattr(args, "dry_run", False), hosts)
    record = load_record()
    before = json.loads(json.dumps(record))
    try:
        COMMANDS[args.command](args, plan, record)
        save_record(plan, before, record)
    except Refusal as exc:
        print(f"forge setup: {exc}; nothing written", file=sys.stderr)
        return 2
    if not plan.dry_run:
        done: list[str] = []
        try:
            merged = union_record(before, record)
            if merged != before:
                write_atomic(record_path(), (json.dumps(merged, indent=2) + "\n").encode("utf-8"))
            plan.apply(done)
        except OSError as exc:
            print(f"forge setup: write failed ({exc}); already written: {', '.join(done) or 'nothing'}; "
                  f"the ownership record {record_path()} lists them, so remove undoes them", file=sys.stderr)
            return 2
    print(json.dumps(plan.result(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
