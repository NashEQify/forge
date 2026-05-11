"""
Shared Fixtures fuer Spec 299 Fabrication-Mitigation Tests.

RED-Skeletons. Implementation steht noch aus.

Pflicht-Reads beim Schreiben dieser Fixtures: spec + test-plan v1 + adversary.
NICHT gelesen: Implementation-Code (scripts/workflow_engine.py,
scripts/lib/yaml_loader.py, scripts/validate_evidence_pointers.py,
orchestrators/claude-code/hooks/*).
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# Framework-Checkout importierbar machen — gleicher Pattern wie
# tests/test_workflow_engine_drift.py
_FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_ROOT))


# ---------------------------------------------------------------------------
# Path-Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def framework_root() -> Path:
    """Repo-root als Path."""
    return _FRAMEWORK_ROOT


@pytest.fixture
def spec_path(framework_root: Path) -> Path:
    return framework_root / "docs/specs/299-fabrication-mitigation.md"


# ---------------------------------------------------------------------------
# Engine-Isolation (Pattern aus test_workflow_engine_drift.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    """Redirect PROJECT_ROOT + STATE_DIR auf tmp_path. Engine-isoliert."""
    # Importiert hier (lazy) — Engine-Modul existiert; wir mutieren nur Pfade.
    from scripts import workflow_engine as we  # noqa: E402

    state_dir = tmp_path / ".workflow-state"
    state_dir.mkdir()
    archive_dir = state_dir / "archive"
    archive_dir.mkdir()

    monkeypatch.setattr(we, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(we, "STATE_DIR", state_dir)
    monkeypatch.setattr(we, "ARCHIVE_DIR", archive_dir)
    if hasattr(we, "REPO_ROOT"):
        monkeypatch.setattr(we, "REPO_ROOT", tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Synthetic Source-Files mit echten Bytes (kein Mock — Validator nutzt grep -F)
# ---------------------------------------------------------------------------


@pytest.fixture
def fixture_source_hello(tmp_path: Path) -> Path:
    """Source-File mit Inhalt 'Hello World' in Z.1."""
    src = tmp_path / "source.txt"
    src.write_text("Hello World\n", encoding="utf-8")
    return src


@pytest.fixture
def fixture_source_10_lines(tmp_path: Path) -> Path:
    """Source-File mit 10 Zeilen (fuer out-of-range tests)."""
    src = tmp_path / "ten_lines.txt"
    src.write_text("\n".join(f"line {i}" for i in range(1, 11)) + "\n",
                   encoding="utf-8")
    return src


# ---------------------------------------------------------------------------
# Pointer-File-Builder (Output-Files mit Frontmatter + evidence)
# ---------------------------------------------------------------------------


def _write_top_level_pointer_file(
    path: Path,
    schema_version: int | None,
    evidence: str,
) -> Path:
    """Helper: schreibt File mit YAML-Frontmatter im top_level layout.

    `evidence` ist YAML-Text (kein Python-Objekt) damit alle YAML-Variants
    (`[]`, `~`, missing, fabricated) testbar sind.

    CC-008 Pass-1-Fix: pre-fix nutzte textwrap.dedent mit f-string-
    interpoliertem multi-line `evidence` ohne gemeinsames Indent. `dedent`
    fuhr common-prefix auf 0 zurueck, `---`-Marker behielten 8-Space-Indent,
    evidence-Sub-Lines landeten bei 0 Indent. Production-Validator hatte
    `_normalize_fm_indent`-Helper rein um diese Test-Fixture-Schwaeche zu
    absorbieren.
    Fix: explizite Frontmatter-Konstruktion ohne dedent — sauberes
    0-indented YAML.
    C2-002 Pass-2-Fix: `_normalize_fm_indent` wurde komplett aus dem
    Validator entfernt; mixed-indent ist jetzt parse-error (nicht silent-fix).
    Diese Fixture muss daher sauberes 0-indented YAML emittieren — was sie
    bereits seit Pass-1-Fix tut.
    """
    sv_line = f"schema_version: {schema_version}\n" if schema_version is not None else ""
    # Build frontmatter explicitly at column 0
    body = "---\n" + sv_line + evidence
    if not body.endswith("\n"):
        body += "\n"
    body += "---\n\nBody\n"
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture
def make_pointer_file(tmp_path: Path):
    """Factory: erzeugt Output-File mit konfigurierbarem Frontmatter."""

    def _make(
        name: str = "out.md",
        schema_version: int | None = 1,
        evidence: str = "evidence: []",
    ) -> Path:
        return _write_top_level_pointer_file(
            tmp_path / name, schema_version, evidence
        )

    return _make


@pytest.fixture
def valid_pointer_file(tmp_path: Path, fixture_source_hello: Path):
    """File mit schema_version: 1 + valid file_range pointer gegen real source."""
    rel = fixture_source_hello.relative_to(tmp_path)
    evidence = textwrap.dedent(
        f"""\
        evidence:
          - kind: file_range
            path: {rel}
            lines: 1-1
            quote: "Hello World"
        """
    )
    out = tmp_path / "valid.md"
    return _write_top_level_pointer_file(out, schema_version=1, evidence=evidence)


@pytest.fixture
def fabricated_quote_file(tmp_path: Path, fixture_source_hello: Path):
    """File mit schema_version: 1 + pointer mit fabricated quote (Mismatch)."""
    rel = fixture_source_hello.relative_to(tmp_path)
    evidence = textwrap.dedent(
        f"""\
        evidence:
          - kind: file_range
            path: {rel}
            lines: 1-1
            quote: "Goodbye World"
        """
    )
    out = tmp_path / "fabricated.md"
    return _write_top_level_pointer_file(out, schema_version=1, evidence=evidence)


@pytest.fixture
def out_of_range_file(tmp_path: Path, fixture_source_10_lines: Path):
    """File mit Pointer der lines: 9999-9999 in 10-line source claimt."""
    rel = fixture_source_10_lines.relative_to(tmp_path)
    evidence = textwrap.dedent(
        f"""\
        evidence:
          - kind: file_range
            path: {rel}
            lines: 9999-9999
            quote: "line 1"
        """
    )
    out = tmp_path / "out_of_range.md"
    return _write_top_level_pointer_file(out, schema_version=1, evidence=evidence)


@pytest.fixture
def empty_evidence_list_file(tmp_path: Path, make_pointer_file):
    """schema_version: 1 + evidence: []"""
    return make_pointer_file(name="empty_list.md", schema_version=1,
                             evidence="evidence: []")


@pytest.fixture
def empty_evidence_null_file(tmp_path: Path, make_pointer_file):
    """schema_version: 1 + evidence: ~"""
    return make_pointer_file(name="empty_null.md", schema_version=1,
                             evidence="evidence: ~")


@pytest.fixture
def empty_evidence_missing_file(tmp_path: Path, make_pointer_file):
    """schema_version: 1 + 'evidence:' (kein Value)."""
    return make_pointer_file(name="empty_missing.md", schema_version=1,
                             evidence="evidence:")


@pytest.fixture
def legacy_v0_file(tmp_path: Path, fixture_source_hello: Path):
    """schema_version: 0 + fabricated evidence (silent skip per Spec)."""
    rel = fixture_source_hello.relative_to(tmp_path)
    evidence = textwrap.dedent(
        f"""\
        evidence:
          - kind: file_range
            path: {rel}
            lines: 1-1
            quote: "fabricated never matches anything legacy"
        """
    )
    out = tmp_path / "legacy.md"
    return _write_top_level_pointer_file(out, schema_version=0, evidence=evidence)


@pytest.fixture
def legacy_no_field_file(tmp_path: Path):
    """File ohne schema_version-Field. Legacy per Spec §1.4."""
    out = tmp_path / "legacy_no_field.md"
    out.write_text("---\n# no schema_version\n---\nBody\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Validator-CLI-Helper
# ---------------------------------------------------------------------------


@pytest.fixture
def validator_cli():
    """Helper: ruft scripts/validate_evidence_pointers.py CLI-style.

    Implementation steht aus — Fixture liefert nur Aufruf-Helper. Tests die
    es nutzen sollen RED bleiben bis Validator existiert.
    """
    import subprocess

    def _run(file_path: Path | str, *args: str, cwd: Path | None = None):
        cmd = [
            sys.executable,
            str(_FRAMEWORK_ROOT / "scripts/validate_evidence_pointers.py"),
            str(file_path),
            *args,
        ]
        return subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(cwd) if cwd else str(_FRAMEWORK_ROOT),
        )

    return _run
