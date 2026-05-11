# Buddy — Permissions

Source of truth for Buddy's execution permissions.
Adapters translate these categories into orchestrator-specific formats.

Changes here → update the CC adapter (`.claude/settings.json`) and
the OC adapter.

## Principle

Buddy is the user's personal agent with full Linux admin rights on
all of the user's machines (soul.md: "Self-hosting / Linux admin —
Buddy does that directly"). The sudo password is supplied by the
user at runtime.

Default: **allow without asking** for every category below.
Side effects on infrastructure (systemd changes, package install,
SSH actions) run without a clarifying question — Buddy decides on
its own whether an action makes sense. The user does not want
unnecessary clarifying questions on standard actions.

## Categories

### Filesystem (read + write)
ls, cat, head, tail, find, tree, file, stat, du, df, wc, sort, uniq,
basename, dirname, realpath, readlink, diff, sha256sum, md5sum,
mkdir, cp, mv, rm, touch, chmod, chown, ln, tar, zip, unzip, gzip, gunzip

### Git
git (all subcommands), gh (GitHub CLI)

### System info
uname, hostname, date, id, whoami, pwd, env, printenv, uptime, free,
vmstat, iostat, iotop, sensors, acpi, top, htop, dmesg, coredumpctl,
lspci, lsusb, lsblk, lscpu, lsmem, lshw, lsmod, lsof, dmidecode,
nvidia-smi, glxinfo, xrandr

### Network
ss, ip, nmcli, ping, traceroute, dig, nslookup, curl, wget,
tailscale (all subcommands), mmcli

### Process management
ps, pgrep, kill, killall, nohup, jobs, bg, fg

### Services + systemd
systemctl (all subcommands incl. start/stop/restart/enable/disable),
journalctl, systemd-analyze

### Package management
apt, apt-get, apt-cache, dpkg, pip, pip3, pipx,
snap, flatpak, npm, npx, cargo, go, make

### Docker
docker (all subcommands incl. compose)

### SSH
ssh (all hosts), scp, rsync

### Sudo
sudo (all commands). Password supplied at runtime via pipe or user
input.

### Dev tools / scripting
python, python3, node, sed, awk, grep, rg, fd, jq,
echo, printf, test, read, which, whereis, type, tee, xargs,
zgrep, zcat, zless, zmore, zdiff

### Desktop / GUI
gsettings, gnome-extensions, gnome-shell, xdg-open, xdg-desktop-menu,
xmodmap, dbus-send, wmctrl, update-desktop-database, desktop-file-validate,
code (VS Code), convert (ImageMagick)

### Special tools
~/.local/bin/yt-dlp

### Web (CC-specific)
WebSearch: allowed (research is required).
WebFetch: all domains allowed. The CC adapter lists known domains
explicitly (CC needs per-domain patterns); new domains are added on
demand.

### Read access outside the repo
Unrestricted — any path, no clarifying question. Applies to the Read
tool, ls, cat, head, tail, journalctl, dmesg, and anything else that
only reads. `ls` is reading — no clarifying question, no approval.

## Explicitly NOT without asking

- Nothing. Buddy has full rights. The user trusts Buddy's judgment.
  Side-effect verification is Buddy's responsibility (soul.md:
  "double-check").

## Adapter paths

| Orchestrator | File | Format |
|---|---|---|
| CC | `.claude/settings.json` | `permissions.allow: ["Bash(cmd:*)"]` |
| OC | `orchestrators/opencode/.opencode/agent/buddy.md` | `permission.bash: {"cmd*": allow}` |
