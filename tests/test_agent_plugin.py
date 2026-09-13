"""The repository root is one Agent Plugin with a single canonical skill.

  plugin.json                        portable Agent Plugins 1.0.0 manifest (Codex CLI)
  .agents/plugins/marketplace.json   Codex repo marketplace, source "./"
  .claude-plugin/plugin.json         Claude Code plugin manifest
  .claude-plugin/marketplace.json    Claude Code marketplace, source "."
  gemini-extension.json              Gemini CLI extension manifest

Every manifest resolves to the repository root, whose only skill is
`skills/csv-quality-gate/SKILL.md`. No host carries its own copy, and every
identity field matches pyproject.toml so the manifests cannot drift. The live
tests install into an isolated HOME and are skipped when the CLI is absent.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PORTABLE_MANIFEST = ROOT / "plugin.json"
CODEX_MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
CLAUDE_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
GEMINI_MANIFEST = ROOT / "gemini-extension.json"
SKILL = ROOT / "skills" / "csv-quality-gate" / "SKILL.md"
PYPROJECT = ROOT / "pyproject.toml"
SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
NAME_PATTERN = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
PORTABLE_KEYS = {
    "$schema", "name", "version", "description", "author", "homepage",
    "repository", "license", "keywords", "extensions",
}
IGNORED_DIRS = {".git", ".venv", "venv", "build", "dist", ".pytest_cache", ".ruff_cache"}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pyproject_field(name: str) -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(rf'^{re.escape(name)}\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    assert match, f"{name} not found in pyproject.toml"
    return match.group(1)


def test_portable_manifest_follows_agent_plugins_schema():
    manifest = _json(PORTABLE_MANIFEST)
    assert manifest["$schema"] == SCHEMA_ID
    assert NAME_PATTERN.match(manifest["name"]) and len(manifest["name"]) <= 64
    assert set(manifest) <= PORTABLE_KEYS, set(manifest) - PORTABLE_KEYS
    author = manifest.get("author", {})
    assert isinstance(author, dict), author
    assert set(author) <= {"name", "email", "url"}
    assert all(isinstance(value, str) and value for value in author.values()), author


def test_every_manifest_identity_matches_pyproject():
    name, version = _pyproject_field("name"), _pyproject_field("version")
    description = _pyproject_field("description")
    for path in (PORTABLE_MANIFEST, CLAUDE_MANIFEST, GEMINI_MANIFEST):
        manifest = _json(path)
        assert manifest["name"] == name, path
        assert manifest["version"] == version, path
        assert manifest["description"] == description, path
    portable, claude = _json(PORTABLE_MANIFEST), _json(CLAUDE_MANIFEST)
    for key in ("author", "homepage", "repository", "license"):
        assert portable[key] == claude[key], key


def test_every_marketplace_resolves_to_the_repository_root():
    name = _pyproject_field("name")
    codex = _json(CODEX_MARKETPLACE)
    (entry,) = codex["plugins"]
    assert codex["name"] == entry["name"] == name
    assert entry["source"] == {"source": "local", "path": "./"}
    assert (CODEX_MARKETPLACE.parents[2] / entry["source"]["path"]).resolve() == ROOT
    assert "version" not in entry

    claude = _json(CLAUDE_MARKETPLACE)
    (entry,) = claude["plugins"]
    assert claude["name"] == entry["name"] == name
    assert entry["source"] == "."
    assert (CLAUDE_MARKETPLACE.parents[1] / entry["source"]).resolve() == ROOT


def test_single_canonical_skill():
    """Every host loads skills/ from the root; no second, driftable copy may exist."""
    found = sorted(
        path.relative_to(ROOT)
        for path in ROOT.rglob("SKILL.md")
        if not IGNORED_DIRS.intersection(path.relative_to(ROOT).parts)
    )
    assert found == [SKILL.relative_to(ROOT)], found
    text = SKILL.read_text(encoding="utf-8")
    frontmatter = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    assert frontmatter, "SKILL.md needs YAML frontmatter"
    assert re.search(r"^name: csv-quality-gate$", frontmatter.group(1), flags=re.MULTILINE)
    assert re.search(r"^description: \S", frontmatter.group(1), flags=re.MULTILINE)


def test_skill_pins_a_published_runner():
    text = SKILL.read_text(encoding="utf-8")
    pins = set(re.findall(r"csv-quality-gate==(\d+\.\d+\.\d+)", text))
    assert len(pins) == 1, pins


def test_documented_gemini_install_pins_a_ref():
    """Unpinned GitHub installs take the latest release, which predates the manifest."""
    pattern = re.compile(
        r"gemini extensions install https://github\.com/hermes-labs-ai/csv-quality-gate[^\n`]*"
    )
    for doc in (ROOT / "README.md", ROOT / "llms.txt"):
        commands = pattern.findall(doc.read_text(encoding="utf-8"))
        assert commands, f"{doc.name} no longer documents the Gemini install"
        for command in commands:
            assert "--ref " in command, f"{doc.name}: {command!r} must pass --ref"


def _package(tmp_path: Path) -> Path:
    pkg = tmp_path / "csv-quality-gate"
    pkg.mkdir()
    for rel in ("plugin.json", "gemini-extension.json"):
        shutil.copy2(ROOT / rel, pkg / rel)
    for rel in (".agents", ".claude-plugin", "skills"):
        shutil.copytree(ROOT / rel, pkg / rel)
    return pkg


def _run(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False, env=env, timeout=120)


@pytest.mark.skipif(shutil.which("codex") is None, reason="codex CLI not installed")
def test_codex_marketplace_install_reads_back_the_skill(tmp_path):
    pkg = _package(tmp_path)
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    env = {"HOME": str(home), "CODEX_HOME": str(home / ".codex"),
           "PATH": os.environ.get("PATH", "/usr/bin:/bin")}

    add = _run(["codex", "plugin", "marketplace", "add", str(pkg)], env)
    assert add.returncode == 0, f"{add.stdout}\n{add.stderr}"
    install = _run(["codex", "plugin", "add", "csv-quality-gate@csv-quality-gate"], env)
    assert install.returncode == 0, f"{install.stdout}\n{install.stderr}"
    listed = _run(["codex", "plugin", "list"], env)
    assert "csv-quality-gate@csv-quality-gate" in listed.stdout, listed.stdout
    cached = list((home / ".codex" / "plugins").rglob("skills/csv-quality-gate/SKILL.md"))
    assert cached and all(p.read_bytes() == SKILL.read_bytes() for p in cached), cached


@pytest.mark.skipif(shutil.which("gemini") is None, reason="gemini CLI not installed")
def test_gemini_extension_install_discovers_the_skill(tmp_path):
    pkg = _package(tmp_path)
    home = tmp_path / "home"
    (home / ".gemini").mkdir(parents=True)
    # Listing is local, but the CLI refuses to start without an auth method.
    (home / ".gemini" / "settings.json").write_text(
        '{"security":{"auth":{"selectedType":"gemini-api-key"}}}', encoding="utf-8")
    env = {"HOME": str(home), "GEMINI_API_KEY": "placeholder-not-a-key",
           "PATH": os.environ.get("PATH", "/usr/bin:/bin")}

    install = _run(["gemini", "extensions", "install", str(pkg), "--consent"], env)
    assert install.returncode == 0, f"{install.stdout}\n{install.stderr}"
    skills = _run(["gemini", "skills", "list"], env)
    assert skills.returncode == 0, skills.stderr
    installed = (home / ".gemini" / "extensions" / "csv-quality-gate" / "skills"
                 / "csv-quality-gate" / "SKILL.md")
    assert str(installed) in skills.stdout + skills.stderr
    assert installed.read_bytes() == SKILL.read_bytes()
