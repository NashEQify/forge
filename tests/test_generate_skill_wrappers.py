"""
TC-1..TC-15 for scripts/generate_skill_wrappers.py (Task 326 Gate 4).

The generator derives `.claude/skills/<kebab>/SKILL.md` wrappers from
`skills/*/SKILL.md` frontmatter. These tests build a synthetic repo
under tmp_path (a `framework/` dir so repo_root resolves, a `skills/`
tree, a `.claude/skills/` tree) and drive the module by function call
and via `main(["--repo", ...])`.

TC-2 is source-fidelity + drift-correction: a generated wrapper's
`description` must equal its source skill's `description` (normalized);
a pre-existing hand-authored wrapper that diverged from source IS
rewritten on the first run (that diff is the drift fix, expected and
desired). Idempotence is measured run-vs-run (TC-1), never against the
old hand files.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
if str(_FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_ROOT))

from scripts.generate_skill_wrappers import (  # noqa: E402
    GENERATED_MARKER,
    CollisionError,
    FrontmatterValueError,
    RepoRootError,
    build_desired,
    extract_frontmatter,
    is_eligible,
    kebab_normalize,
    main,
    normalize_description,
    render_wrapper,
    repo_root,
)


# --------------------------------------------------------------------------
# Fixture helpers
# --------------------------------------------------------------------------


def _make_repo(tmp_path: Path) -> Path:
    """Synthetic repo root: framework/ marker + skills/ + .claude/skills/."""
    (tmp_path / "framework").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    return tmp_path


def _write_skill(root: Path, dir_name: str, frontmatter: str, body: str = "x") -> None:
    d = root / "skills" / dir_name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\n{frontmatter}\n---\n\n# Skill: {dir_name}\n\n{body}\n",
        encoding="utf-8",
    )


def _write_raw_skill(root: Path, dir_name: str, content: str) -> None:
    d = root / "skills" / dir_name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(content, encoding="utf-8")


def _write_wrapper(root: Path, name: str, content: str) -> Path:
    d = root / ".claude" / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(content, encoding="utf-8")
    return p


def _wrapper_path(root: Path, name: str) -> Path:
    return root / ".claude" / "skills" / name / "SKILL.md"


def _frontmatter(text: str) -> dict:
    # Use the generator's robust line-anchored fence parser so a
    # literal `---` inside a description value does not mis-split the
    # test's own assertion helper (C-002).
    data = extract_frontmatter(text)
    assert data is not None
    return data


_USER_FACING = (
    "name: {name}\n"
    "description: >\n"
    "  Does the thing.\n"
    "  Triggers when the user asks for the thing.\n"
    "status: active\n"
    "invocation:\n"
    "  primary: user-facing\n"
    "disable-model-invocation: false\n"
)


def _uf(name: str) -> str:
    return _USER_FACING.format(name=name)


# --------------------------------------------------------------------------
# TC-1 idempotent (AC-1)
# --------------------------------------------------------------------------


def test_tc1_idempotent_run_vs_run(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))
    _write_skill(root, "beta", _uf("beta"))

    assert main(["--repo", str(root)]) == 0
    snapshot = {
        p.relative_to(root): p.read_text(encoding="utf-8")
        for p in (root / ".claude" / "skills").rglob("SKILL.md")
    }
    assert main(["--repo", str(root)]) == 0
    after = {
        p.relative_to(root): p.read_text(encoding="utf-8")
        for p in (root / ".claude" / "skills").rglob("SKILL.md")
    }
    assert snapshot == after
    # generate then --check ⇒ exit 0, zero diff between generator runs
    assert main(["--repo", str(root), "--check"]) == 0


# --------------------------------------------------------------------------
# TC-2 source-fidelity + drift-correction (AC-1/2)
# --------------------------------------------------------------------------


def test_tc2_source_fidelity_and_drift_correction(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(
        root,
        "code_review_board",
        "name: code-review-board\n"
        "description: >\n"
        "  Multi-perspective code review. 2 levels: L1 + L2.\n"
        "  Triggers when a code diff needs multi-perspective review.\n"
        "status: active\n"
        "cc_wrapper: true\n"
        "invocation:\n"
        "  primary: workflow-step\n",
    )
    # Pre-existing STALE hand-authored wrapper whose description diverged
    # from the (now current) source frontmatter.
    _write_wrapper(
        root,
        "code-review-board",
        "---\nname: code-review-board\n"
        "description: STALE hand-written text that no longer matches source\n"
        "---\n\n# old hand body with per-skill parenthetical\n",
    )

    assert main(["--repo", str(root)]) == 0

    wrapper = _wrapper_path(root, "code-review-board").read_text(encoding="utf-8")
    fm = _frontmatter(wrapper)
    src_fm = _frontmatter(
        (root / "skills" / "code_review_board" / "SKILL.md").read_text(
            encoding="utf-8"
        )
    )
    # Gate (a): wrapper description == source description, normalized.
    assert fm["description"] == normalize_description(src_fm["description"])
    # Drift correction: the stale hand text is gone (rewritten from source).
    assert "STALE hand-written text" not in wrapper
    assert "per-skill parenthetical" not in wrapper
    assert "Triggers when a code diff needs multi-perspective review." in wrapper


# --------------------------------------------------------------------------
# TC-3 criterion-implicit (AC-2)
# --------------------------------------------------------------------------


def test_tc3_criterion_implicit(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "uf_skill", _uf("uf-skill"))
    _write_skill(
        root,
        "ws_skill",
        "name: ws-skill\ndescription: >\n  X. Triggers when Y.\n"
        "status: active\ninvocation:\n  primary: workflow-step\n",
    )
    desired = build_desired(root / "skills")
    assert "uf-skill" in desired
    assert "ws-skill" not in desired


# --------------------------------------------------------------------------
# TC-4 criterion-cross-cutting (AC-2)
# --------------------------------------------------------------------------


def test_tc4_criterion_cross_cutting(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(
        root,
        "consistency_check",
        "name: consistency-check\ndescription: >\n  Struct check. Triggers when drift.\n"
        "status: active\ninvocation:\n  primary: cross-cutting\n"
        "disable-model-invocation: false\n",
    )
    desired = build_desired(root / "skills")
    assert "consistency-check" in desired


def test_secondary_user_facing_is_eligible(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(
        root,
        "get_api_docs",
        "name: get-api-docs\ndescription: >\n  Fetch docs. Triggers when API.\n"
        "status: active\ninvocation:\n  primary: workflow-step\n"
        "  secondary: [user-facing, sub-skill]\n",
    )
    desired = build_desired(root / "skills")
    assert "get-api-docs" in desired


# --------------------------------------------------------------------------
# TC-5 override-true (AC-2)
# --------------------------------------------------------------------------


def test_tc5_override_true(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(
        root,
        "get_api_docs",
        "name: get-api-docs\ndescription: >\n  Fetch docs. Triggers when API.\n"
        "status: active\ncc_wrapper: true\ninvocation:\n  primary: workflow-step\n",
    )
    desired = build_desired(root / "skills")
    assert "get-api-docs" in desired


# --------------------------------------------------------------------------
# TC-6 override-false (AC-2)
# --------------------------------------------------------------------------


def test_tc6_override_false(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(
        root,
        "hidden",
        "name: hidden\ndescription: >\n  Thing. Triggers when X.\n"
        "status: active\ncc_wrapper: false\ninvocation:\n  primary: user-facing\n",
    )
    desired = build_desired(root / "skills")
    assert "hidden" not in desired


# --------------------------------------------------------------------------
# TC-7 dmi-exclude (AC-2)
# --------------------------------------------------------------------------


def test_tc7_dmi_exclude(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(
        root,
        "zoom_out",
        "name: zoom-out\ndescription: >\n  Z. Triggers when Y.\n"
        "status: active\ndisable-model-invocation: true\n"
        "invocation:\n  primary: user-facing\n",
    )
    desired = build_desired(root / "skills")
    assert "zoom-out" not in desired


# --------------------------------------------------------------------------
# TC-8 status-exclude (AC-2)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["deprecated", "archived"])
def test_tc8_status_exclude(tmp_path: Path, status: str) -> None:
    root = _make_repo(tmp_path)
    _write_skill(
        root,
        "spec_update",
        f"name: spec-update\ndescription: >\n  S. Triggers when T.\n"
        f"status: {status}\ninvocation:\n  primary: user-facing\n",
    )
    desired = build_desired(root / "skills")
    assert "spec-update" not in desired


# --------------------------------------------------------------------------
# TC-9 orphan-removal (AC-1/3)
# --------------------------------------------------------------------------


def test_tc9_orphan_removal(tmp_path: Path) -> None:
    """
    A *generated* wrapper whose source skill disappears is swept.

    The orphan must be generator-authored (carry GENERATED_MARKER) —
    the sweep is scoped to provably-generated dirs (C-001). We create
    the orphan via the generator itself (so it carries the marker),
    then delete its source skill and re-run.
    """
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))
    _write_skill(root, "ghost", _uf("ghost"))
    assert main(["--repo", str(root)]) == 0
    assert _wrapper_path(root, "ghost").is_file()
    assert GENERATED_MARKER in _wrapper_path(root, "ghost").read_text(
        encoding="utf-8"
    )

    # Source skill removed → wrapper is now a generated orphan.
    import shutil as _sh

    _sh.rmtree(root / "skills" / "ghost")
    assert main(["--repo", str(root)]) == 0
    assert _wrapper_path(root, "alpha").is_file()
    assert not (root / ".claude" / "skills" / "ghost").exists()


# --------------------------------------------------------------------------
# C-001 regression (GATING): a non-generated dir SURVIVES orphan-sweep
# --------------------------------------------------------------------------


def test_c001_non_generated_dir_with_skillmd_survives_sweep(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))
    # Hand-authored CC-plugin wrapper: a SKILL.md with NO generator
    # marker (mimics /review, init, etc.).
    hand = _write_wrapper(
        root,
        "review",
        "---\nname: review\ndescription: Review a pull request\n"
        "---\n\n# hand-authored CC-plugin wrapper, NOT generated\n",
    )
    hand_before = hand.read_text(encoding="utf-8")

    assert main(["--repo", str(root)]) == 0

    # Survives untouched.
    assert hand.is_file()
    assert hand.read_text(encoding="utf-8") == hand_before
    assert _wrapper_path(root, "alpha").is_file()
    err = capsys.readouterr().err
    assert "unmanaged dir" in err and "review" in err


def test_c001_non_generated_dir_without_skillmd_survives_sweep(
    tmp_path: Path,
) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))
    # Asset dir: no SKILL.md at all.
    asset = root / ".claude" / "skills" / "_assets"
    asset.mkdir(parents=True)
    (asset / "logo.png").write_bytes(b"\x89PNG not-really")

    assert main(["--repo", str(root)]) == 0

    assert asset.is_dir()
    assert (asset / "logo.png").is_file()


def test_c001_check_mode_ignores_unmanaged_dir(tmp_path: Path) -> None:
    """An unmanaged dir must not make --check perpetually red."""
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))
    _write_wrapper(
        root,
        "review",
        "---\nname: review\ndescription: hand\n---\n\n# not generated\n",
    )
    assert main(["--repo", str(root)]) == 0
    # Tree is in sync as far as the generator is concerned.
    assert main(["--repo", str(root), "--check"]) == 0


def test_f_ca_dv_001_symlinked_orphan_dir_survives_sweep(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    F-CA-DV-001 regression (GATING): a *symlinked* orphan dir under
    .claude/skills/ must NOT be classified as a generated wrapper.

    `is_dir()` follows symlinks, so without the symlink pre-guard a
    symlinked dir whose target carries a SKILL.md + GENERATED_MARKER
    would be treated as a generated wrapper and `shutil.rmtree` would
    raise an unhandled OSError (it refuses to recurse a symlink),
    exiting 1. The fix rejects symlinks before any is_dir()/marker/
    rmtree logic → the symlink is left in place + WARNed (parity with
    the unmanaged-dir path), the target is untouched, exit 0.
    """
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))

    # A real generated-looking wrapper dir OUTSIDE the sweep root, used
    # as the symlink target. It carries SKILL.md + GENERATED_MARKER so
    # that the (buggy) is_dir()-follows-symlink path would have matched.
    target = tmp_path / "external_target"
    target.mkdir()
    target_skill = target / "SKILL.md"
    target_skill.write_text(
        f"---\nname: linked\ndescription: x\n---\n\n{GENERATED_MARKER}\n",
        encoding="utf-8",
    )
    target_skill_before = target_skill.read_text(encoding="utf-8")

    # An orphan symlinked dir under .claude/skills/ (no matching source
    # skill ⇒ orphan-sweep candidate).
    link = root / ".claude" / "skills" / "linked"
    link.symlink_to(target, target_is_directory=True)

    # No exception, exit 0.
    assert main(["--repo", str(root)]) == 0

    # The symlink itself survives in place.
    assert link.is_symlink()
    assert link.exists()
    # The symlink target is completely untouched.
    assert target.is_dir()
    assert target_skill.is_file()
    assert target_skill.read_text(encoding="utf-8") == target_skill_before
    # The legitimate wrapper was still generated.
    assert _wrapper_path(root, "alpha").is_file()
    # Parity with the unmanaged-dir path: stderr WARN, not removed.
    err = capsys.readouterr().err
    assert "unmanaged dir" in err and "linked" in err


def test_tc9_orphan_when_source_becomes_ineligible(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))
    assert main(["--repo", str(root)]) == 0
    assert _wrapper_path(root, "alpha").is_file()
    # Source flips to cc_wrapper: false → wrapper must be removed.
    _write_skill(
        root,
        "alpha",
        "name: alpha\ndescription: >\n  A. Triggers when X.\n"
        "status: active\ncc_wrapper: false\ninvocation:\n  primary: user-facing\n",
    )
    assert main(["--repo", str(root)]) == 0
    assert not (root / ".claude" / "skills" / "alpha").exists()


# --------------------------------------------------------------------------
# TC-10 name-normalize (AC-1)
# --------------------------------------------------------------------------


def test_tc10_name_normalize_and_trigger_preserved(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(
        root,
        "my_skill",
        "name: my_skill\ndescription: >\n  Body text.\n"
        '  Triggers when user says "do the thing" exactly.\n'
        "status: active\ninvocation:\n  primary: user-facing\n",
    )
    assert main(["--repo", str(root)]) == 0
    # snake `name:` → kebab wrapper dir
    assert _wrapper_path(root, "my-skill").is_file()
    fm = _frontmatter(
        _wrapper_path(root, "my-skill").read_text(encoding="utf-8")
    )
    assert fm["name"] == "my-skill"
    # trigger string preserved verbatim (inter-token whitespace only)
    assert 'Triggers when user says "do the thing" exactly.' in fm["description"]


# --------------------------------------------------------------------------
# TC-11 kebab-collision (failure-mode)
# --------------------------------------------------------------------------


def test_tc11_kebab_collision_hard_error_no_partial_write(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "foo_bar", _uf("foo_bar"))
    _write_skill(root, "foo-bar", _uf("foo-bar"))

    with pytest.raises(CollisionError):
        build_desired(root / "skills")

    # main() surfaces it as a non-zero exit with NO partial write.
    assert main(["--repo", str(root)]) == 1
    assert not any((root / ".claude" / "skills").iterdir())


# --------------------------------------------------------------------------
# TC-12 cc_wrapper-nonbool (failure-mode)
# --------------------------------------------------------------------------


def test_tc12_cc_wrapper_nonbool_hard_error(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(
        root,
        "bad",
        'name: bad\ndescription: >\n  B. Triggers when X.\n'
        'status: active\ncc_wrapper: "yes"\ninvocation:\n  primary: user-facing\n',
    )
    with pytest.raises(FrontmatterValueError):
        build_desired(root / "skills")
    assert main(["--repo", str(root)]) == 1
    assert not any((root / ".claude" / "skills").iterdir())


# --------------------------------------------------------------------------
# TC-13 malformed-frontmatter (failure-mode)
# --------------------------------------------------------------------------


def test_tc13_malformed_frontmatter_skipped_others_written(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "good", _uf("good"))
    # No frontmatter at all.
    _write_raw_skill(root, "broken_none", "# just a heading, no frontmatter\n")
    # Invalid YAML inside the frontmatter fence.
    _write_raw_skill(
        root, "broken_yaml", "---\nname: x\n  : : bad\n---\n\nbody\n"
    )

    rc = main(["--repo", str(root)])
    assert rc == 0  # does not crash
    assert _wrapper_path(root, "good").is_file()
    assert not (root / ".claude" / "skills" / "broken-none").exists()
    assert not (root / ".claude" / "skills" / "broken-yaml").exists()


def test_tc13_emits_no_crash_on_eligible_missing_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _make_repo(tmp_path)
    # Parsable frontmatter, eligible, but `name` missing.
    _write_raw_skill(
        root,
        "noname",
        "---\ndescription: >\n  X. Triggers when Y.\n"
        "status: active\ninvocation:\n  primary: user-facing\n---\n\nbody\n",
    )
    _write_skill(root, "good", _uf("good"))
    assert main(["--repo", str(root)]) == 0
    assert _wrapper_path(root, "good").is_file()
    err = capsys.readouterr().err
    assert "noname" in err


# --------------------------------------------------------------------------
# TC-14 check-mode (AC-3)
# --------------------------------------------------------------------------


def test_tc14_check_mode(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))

    # Clean (freshly generated) tree → --check exit 0.
    assert main(["--repo", str(root)]) == 0
    assert main(["--repo", str(root), "--check"]) == 0

    # Drift it by hand → --check non-zero, no write (file unchanged).
    p = _wrapper_path(root, "alpha")
    before = p.read_text(encoding="utf-8")
    p.write_text(before + "\nhand edit\n", encoding="utf-8")
    assert main(["--repo", str(root), "--check"]) == 1
    assert p.read_text(encoding="utf-8") == before + "\nhand edit\n"

    # Missing wrapper for an eligible skill → --check non-zero.
    import shutil as _sh

    _sh.rmtree(root / ".claude" / "skills" / "alpha")
    assert main(["--repo", str(root), "--check"]) == 1


# --------------------------------------------------------------------------
# TC-15 consistency_check-drift (AC-3)
# --------------------------------------------------------------------------


def test_tc15_consistency_check_drift_then_regenerate(tmp_path: Path) -> None:
    """
    The consistency_check wrapper-drift check (check 10) is mechanically
    `generate_skill_wrappers.py --check`. Hand-edit a wrapper → it
    fails; regenerate → it passes again.
    """
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))
    assert main(["--repo", str(root)]) == 0
    assert main(["--repo", str(root), "--check"]) == 0  # CLEAN

    p = _wrapper_path(root, "alpha")
    p.write_text(
        p.read_text(encoding="utf-8").replace("alpha", "tampered"),
        encoding="utf-8",
    )
    assert main(["--repo", str(root), "--check"]) == 1  # drift flagged

    assert main(["--repo", str(root)]) == 0  # regenerate
    assert main(["--repo", str(root), "--check"]) == 0  # CLEAN again


# --------------------------------------------------------------------------
# Unit-level guards for the predicate / helpers
# --------------------------------------------------------------------------


def test_kebab_normalize() -> None:
    assert kebab_normalize("foo_bar") == "foo-bar"
    assert kebab_normalize("foo-bar") == "foo-bar"
    assert kebab_normalize(" baz_qux ") == "baz-qux"


def test_normalize_description_collapses_folded_scalar() -> None:
    raw = "Line one.\n  Triggers when    X happens.\n"
    assert normalize_description(raw) == "Line one. Triggers when X happens."


def test_is_eligible_predicate_matrix() -> None:
    base = {"status": "active", "invocation": {"primary": "user-facing"}}
    assert is_eligible(base) == (True, None)
    assert is_eligible({**base, "cc_wrapper": False}) == (False, None)
    assert is_eligible(
        {"status": "active", "invocation": {"primary": "workflow-step"}}
    ) == (False, None)
    assert is_eligible(
        {
            "status": "active",
            "invocation": {
                "primary": "workflow-step",
                "secondary": ["user-facing"],
            },
        }
    ) == (True, None)
    assert is_eligible(
        {
            "status": "active",
            "cc_wrapper": True,
            "invocation": {"primary": "workflow-step"},
        }
    ) == (True, None)
    ok, err = is_eligible({**base, "cc_wrapper": "yes"})
    assert ok is False and err is not None
    assert is_eligible(None) == (False, None)


def test_render_wrapper_shape() -> None:
    out = render_wrapper("foo-bar", "Does X.  Triggers when Y.", "foo_bar")
    assert out.startswith("---\nname: foo-bar\n")
    assert "description: Does X. Triggers when Y.\n" in out
    assert "**SoT:** `skills/foo_bar/SKILL.md`" in out
    assert "Claude-Code-discoverable wrapper" in out
    assert GENERATED_MARKER in out
    assert out.endswith("\n")


def test_codex_output_root_and_tool_label(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))
    codex_root = tmp_path / "home" / ".agents" / "skills"

    assert (
        main(
            [
                "--repo",
                str(root),
                "--output-root",
                str(codex_root),
                "--tool-label",
                "Codex",
            ]
        )
        == 0
    )

    wrapper = codex_root / "alpha" / "SKILL.md"
    assert wrapper.is_file()
    text = wrapper.read_text(encoding="utf-8")
    assert "Codex-discoverable wrapper" in text
    assert "**SoT:** `skills/alpha/SKILL.md`" in text
    assert not (root / ".claude" / "skills" / "alpha").exists()
    assert (
        main(
            [
                "--repo",
                str(root),
                "--output-root",
                str(codex_root),
                "--tool-label",
                "Codex",
                "--check",
            ]
        )
        == 0
    )


# --------------------------------------------------------------------------
# C-002 regression: literal `---` inside description must NOT un-discover
# --------------------------------------------------------------------------


def test_c002_literal_triple_dash_in_description_still_wrapped(
    tmp_path: Path,
) -> None:
    root = _make_repo(tmp_path)
    _write_raw_skill(
        root,
        "dashy",
        "---\n"
        "name: dashy\n"
        'description: "Use a --- separator. Triggers when X."\n'
        "status: active\n"
        "invocation:\n"
        "  primary: user-facing\n"
        "---\n\n# body\n",
    )
    assert main(["--repo", str(root)]) == 0
    wp = _wrapper_path(root, "dashy")
    assert wp.is_file()
    fm = _frontmatter(wp.read_text(encoding="utf-8"))
    assert "Triggers when X." in fm["description"]


def test_c002_block_scalar_with_triple_dash_line_still_wrapped(
    tmp_path: Path,
) -> None:
    # A `---`-only line *inside* a block scalar value (indented) must
    # not be mistaken for the closing fence.
    root = _make_repo(tmp_path)
    _write_raw_skill(
        root,
        "blocky",
        "---\n"
        "name: blocky\n"
        "description: |\n"
        "  Intro line.\n"
        "  ---\n"
        "  Triggers when the divider appears.\n"
        "status: active\n"
        "invocation:\n"
        "  primary: user-facing\n"
        "---\n\n# body\n",
    )
    assert main(["--repo", str(root)]) == 0
    fm = _frontmatter(_wrapper_path(root, "blocky").read_text(encoding="utf-8"))
    assert "Triggers when the divider appears." in fm["description"]


def test_c002_no_closing_fence_warns_loudly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = "---\nname: x\ndescription: y\n(no closing fence here)\n"
    assert extract_frontmatter(text, "stuck") is None
    err = capsys.readouterr().err
    assert "stuck" in err and "no closing" in err


def test_c002_yaml_error_soft_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = "---\nname: x\n  : : bad\n---\n\nbody\n"
    assert extract_frontmatter(text, "badyaml") is None
    err = capsys.readouterr().err
    assert "badyaml" in err and "YAML failed to parse" in err


def test_c002_no_opening_fence_quiet_none(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert extract_frontmatter("# just a heading\n", "plain") is None
    assert capsys.readouterr().err == ""


# --------------------------------------------------------------------------
# C-003 regression: no framework ancestor => hard error, no fallback
# --------------------------------------------------------------------------


def test_c003_repo_root_no_framework_ancestor_raises(tmp_path: Path) -> None:
    bare = tmp_path / "not_a_repo"
    bare.mkdir()
    with pytest.raises(RepoRootError):
        repo_root(bare)


def test_c003_main_no_framework_returns_1_no_tree_created(
    tmp_path: Path,
) -> None:
    bare = tmp_path / "elsewhere"
    bare.mkdir()
    assert main(["--repo", str(bare)]) == 1
    # No .claude/skills/ materialized in the wrong tree.
    assert not (bare / ".claude").exists()


# --------------------------------------------------------------------------
# C-004 regression: invocation present-but-scalar => WARN-emitting skip
# --------------------------------------------------------------------------


def test_c004_scalar_invocation_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _make_repo(tmp_path)
    _write_raw_skill(
        root,
        "scalarinv",
        "---\nname: scalarinv\ndescription: D. Triggers when Y.\n"
        "status: active\ninvocation: user-facing\n---\n\nbody\n",
    )
    _write_skill(root, "good", _uf("good"))
    assert main(["--repo", str(root)]) == 0
    assert not (root / ".claude" / "skills" / "scalarinv").exists()
    err = capsys.readouterr().err
    assert "scalarinv" in err and "not a mapping" in err


# --------------------------------------------------------------------------
# C-007 regression: case-only kebab collision => hard error every platform
# --------------------------------------------------------------------------


def test_c007_case_only_collision_hard_error(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "foo_a", _uf("Foo"))
    _write_skill(root, "foo_b", _uf("foo"))
    with pytest.raises(CollisionError):
        build_desired(root / "skills")
    assert main(["--repo", str(root)]) == 1
    assert not any((root / ".claude" / "skills").iterdir())


# --------------------------------------------------------------------------
# Sentinel round-trip: a 2nd run does not WARN-skip generated wrappers
# --------------------------------------------------------------------------


def test_sentinel_round_trip_no_unmanaged_warn_on_second_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _make_repo(tmp_path)
    _write_skill(root, "alpha", _uf("alpha"))
    _write_skill(root, "beta", _uf("beta"))
    assert main(["--repo", str(root)]) == 0
    for n in ("alpha", "beta"):
        assert GENERATED_MARKER in _wrapper_path(root, n).read_text(
            encoding="utf-8"
        )
    capsys.readouterr()  # drain first-run output
    # Second run: every wrapper is recognized as generated, none gets
    # the "unmanaged dir" WARN, tree byte-identical, --check green.
    assert main(["--repo", str(root)]) == 0
    err = capsys.readouterr().err
    assert "unmanaged dir" not in err
    assert main(["--repo", str(root), "--check"]) == 0
