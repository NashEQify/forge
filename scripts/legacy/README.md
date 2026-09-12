# Codex Pre-Managed Migration Evidence

`codex-pre-managed-v1.json` pins exact SHA256 values for the pre-managed
role templates and generated Codex skill wrappers. It is independent of
today's generated `.codex` templates and neutral role/skill descriptions.
`skill_sources` records relative input paths and their SHA256 values; the
generator and installer hashes identify the producers without embedding
Git history or machine-specific paths.

The Buddy installer emitted different bytes from the portable template.
Its exact historical heredoc is retained with `$FRAMEWORK_DIR` as its
only substitution. The migration renderer substitutes the active framework
root, never a root extracted from installed content. A different root or
any other customization remains a conflict for explicit review.

`--migrate-legacy` permits these per-target hashes only for files absent
from the ownership manifest. It does not override a changed managed file,
follow destination symlinks, trust a filename/marker alone, or create
backups. Review unknown content and preserve it outside discovery before
resolving a conflict. Never extend this data merely by copying hashes from
an unclassified installation. Neutral sources remain canonical for new
generation.

The installer validates the mandatory `skills/` input before any managed
planning, including role, skill, boot and hook cleanup. A missing source
directory is not an intentional empty inventory.

Use `bash scripts/setup-codex.sh --check` for a write-free launcher check.
It passes Python `-B`; directly invoked generators disable bytecode before
project imports. For suppression that also covers Python's own startup
imports, invoke direct entry points with `python3 -B` as well. Checks never
apply managed-file changes.

Regression coverage includes exact historical migrations, custom-file
preservation, missing-source rejection, cold-cache checks, and idempotent
installation. The published package does not include the test fixtures.
