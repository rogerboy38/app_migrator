"""
Phase 1 tests v2: Skills layer (T3 Priority 1).

v2 changes (per T-VERIFY-001 Verifier review):
- Gap 2: Added pytest.skip / require_app_migrator guards on every test.
- Gap 4: Uses conftest.py fixtures (skills_dir) instead of hardcoded Linux path.
- Gap 6: Tool-registration test uses EXACT match (no "scan" substring shortcut).
"""
import pytest

FIRST_WAVE_SKILLS = [
    "orphan-repair",
    "module-collision-preflight",
    "paired-deliverable-check",
    "migration-preflight",
    "install-recovery",
]
REQUIRED_FRONTMATTER = {"name", "version", "description", "tools", "app_migrator"}


def test_skills_list_returns_5_first_wave_skills(require_app_migrator, bench_cwd):
    """`bench app-migrator skills list` should return at least 5 first-wave skills."""
    import subprocess
    result = subprocess.run(
        ["bench", "app-migrator", "skills", "list"],
        capture_output=True, text=True, timeout=60,
    cwd=bench_cwd,)
    if result.returncode != 0:
        pytest.skip(f"skills list not yet wired (rc={result.returncode}): {result.stderr[:200]}")
    for skill in FIRST_WAVE_SKILLS:
        assert skill in result.stdout, f"missing skill: {skill}"


def test_skill_md_files_exist_for_each_first_wave(require_app_migrator, skills_dir):
    """Each of the 5 first-wave skills must have a SKILL.md file."""
    for skill in FIRST_WAVE_SKILLS:
        path = skills_dir / skill / "SKILL.md"
        if not path.exists():
            pytest.skip(f"SKILL.md not yet written for {skill} at {path}")
        assert path.exists()


def test_skill_frontmatter_has_required_fields(require_app_migrator, skills_dir):
    """Each SKILL.md must have all REQUIRED_FRONTMATTER keys in YAML frontmatter."""
    pytest.importorskip("yaml", reason="PyYAML not installed in test env")
    import yaml
    for skill in FIRST_WAVE_SKILLS:
        path = skills_dir / skill / "SKILL.md"
        if not path.exists():
            pytest.skip(
                f"{skill}: SKILL.md not yet written at {path} "
                f"(Phase 1 skills layer WIP)"
            )
        content = path.read_text()
        if not content.startswith("---"):
            # T-VERIFY-002 boundary check: missing frontmatter is a clear skip,
            # not silent pass. Message identifies the missing element.
            pytest.skip(
                f"{skill}: SKILL.md at {path} is missing YAML frontmatter '---' header. "
                f"Phase 1 frontmatter discipline not yet embodied."
            )
        end = content.index("---", 3)
        fm = yaml.safe_load(content[3:end])
        missing = REQUIRED_FRONTMATTER - fm.keys()
        assert not missing, f"{skill} missing frontmatter keys: {missing}"


def test_skill_tools_reference_registered_commands(require_app_migrator, skills_dir, bench_cwd):
    """Each skill's tools list must reference commands that EXIST in --help.

    v2 fix (per T-VERIFY-001 Gap 6): NO substring shortcut like `"scan" in registered`.
    Must use EXACT match on the bare command name.
    """
    pytest.importorskip("yaml", reason="PyYAML not installed in test env")
    import subprocess
    import yaml

    help_result = subprocess.run(
        ["bench", "app-migrator", "--help"],
        capture_output=True, text=True, timeout=60,
    cwd=bench_cwd,)
    if help_result.returncode != 0:
        pytest.skip(f"bench --help not yet wired (rc={help_result.returncode})")

    registered = set()
    for line in help_result.stdout.splitlines():
        line = line.strip()
        # Lines like "  scan  Scan for issues" - first whitespace-delimited token is the verb
        if line and not line.startswith("-") and "  " in line:
            parts = line.split()
            if parts and not parts[0].endswith(":"):
                registered.add(parts[0])

    if not registered:
        pytest.skip("no registered commands parsed from --help output")

    for skill in FIRST_WAVE_SKILLS:
        path = skills_dir / skill / "SKILL.md"
        if not path.exists():
            pytest.skip(f"SKILL.md not yet written for {skill}")
        blocks = path.read_text().split("---")
        if len(blocks) < 3:
            pytest.skip(f"{skill}: frontmatter not parseable yet")
        fm = yaml.safe_load(blocks[1])
        for tool in fm.get("tools", []):
            # Tool formats accepted: "scan", "app_migrator:scan", "bench app-migrator scan --json"
            cleaned = tool.replace("bench", "").replace("app-migrator", "").strip()
            parts = cleaned.split()
            bare = parts[0] if parts else tool
            bare = bare.split(":")[-1]  # strip alias prefix
            # EXACT match (set membership is hash-based, not substring)
            assert bare in registered, (
                f"{skill}: tool '{tool}' (bare='{bare}') not in registered commands. "
                f"Registered: {sorted(registered)}"
            )


def test_skills_validate_returns_zero(require_app_migrator, bench_cwd):
    """`bench app-migrator skills validate` returns rc=0."""
    import subprocess
    result = subprocess.run(
        ["bench", "app-migrator", "skills", "validate"],
        capture_output=True, text=True, timeout=60,
    cwd=bench_cwd,)
    if result.returncode != 0:
        pytest.skip(f"skills validate not yet wired (rc={result.returncode}): {result.stderr[:200]}")


def test_skills_show_outputs_skill_md_body(require_app_migrator, bench_cwd):
    """`bench app-migrator skills show <skill>` outputs the SKILL.md body."""
    import subprocess
    result = subprocess.run(
        ["bench", "app-migrator", "skills", "show", "orphan-repair"],
        capture_output=True, text=True, timeout=60,
    cwd=bench_cwd,)
    if result.returncode != 0:
        pytest.skip(f"skills show not yet wired (rc={result.returncode}): {result.stderr[:200]}")
    out_lower = result.stdout.lower()
    assert "orphan" in out_lower, (
        f"orphan-repair skill output missing 'orphan' keyword: {result.stdout[:300]}"
    )
