"""Pinned evidence for pre-managed Codex installations, independent of templates."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def legacy_hashes(
    surface: str, framework_root: Path | None = None
) -> dict[str, set[str]]:
    """Return exact per-target hashes; only Buddy varies by the active root.

    No installed content is used to infer a root or expand the allowlist. A Buddy
    wrapper pointing elsewhere remains a conflict requiring manual review.
    """
    data = json.loads(
        (Path(__file__).parent / "legacy/codex-pre-managed-v1.json").read_text(
            encoding="utf-8"
        )
    )
    if data.get("version") != 1 or data.get("generation") != "pre-managed-v1":
        raise ValueError("unsupported Codex legacy evidence")
    if surface not in {"roles", "skills"}:
        raise ValueError(f"unsupported Codex legacy surface: {surface}")
    entries = data[surface]
    if not isinstance(entries, dict) or not all(
        isinstance(name, str)
        and isinstance(value, str)
        and re.fullmatch(r"[a-f0-9]{64}", value)
        for name, value in entries.items()
    ):
        raise ValueError("invalid Codex legacy hashes")
    hashes = {name: {value} for name, value in entries.items()}
    if surface == "roles" and framework_root is not None:
        # Exact pre-managed installer heredoc, with its sole variable replaced.
        content = data["buddy_install_template"].replace(
            "$FRAMEWORK_DIR", str(framework_root.resolve())
        )
        hashes["buddy.toml"].add(hashlib.sha256(content.encode()).hexdigest())
    return hashes
