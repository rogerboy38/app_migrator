"""app-migrator skills sub-group, v0.5-alpha W1.

This file lives in the active bench app's commands dir (ceda510) as a tactical
bridge to register the v0.5 skills layer with the bench CLI. The actual skills
state (registry.py, SKILL.md files) lives in the new v0.5 scaffold at
/home/frappe/app_migrator/ - this file just wires the click surface.

Loaded by the active bench app's commands/__init__.py:
  from . import skills
  app_migrator.add_command(skills)
"""
import os

import click
import yaml

SKILLS_DIR = "/home/frappe/app_migrator/app_migrator/skills/frappe"
REQUIRED_FRONTMATTER = {"name", "version", "description", "tools", "app_migrator"}


@click.group("skills")
def skills():
    """Skills layer commands (v0.5-alpha W1)."""


@skills.command("list")
def skills_list():
    """List all skills."""
    if not os.path.isdir(SKILLS_DIR):
        click.echo("No skills directory found")
        return
    found = False
    for name in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "SKILL.md")):
            click.echo(name)
            found = True
    if not found:
        click.echo("No skills found")


@skills.command("show")
@click.argument("name")
def skills_show(name):
    """Show a skill's body."""
    skill_file = os.path.join(SKILLS_DIR, name, "SKILL.md")
    if not os.path.isfile(skill_file):
        raise click.ClickException(f"Skill not found: {name}")
    with open(skill_file) as f:
        click.echo(f.read())


@skills.command("validate")
def skills_validate():
    """Validate all skills (YAML frontmatter)."""
    if not os.path.isdir(SKILLS_DIR):
        click.echo("No skills to validate")
        return
    errors = 0
    for name in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, name)
        if not (os.path.isdir(path) and os.path.isfile(os.path.join(path, "SKILL.md"))):
            continue
        with open(os.path.join(path, "SKILL.md")) as f:
            content = f.read()
        if not content.startswith("---"):
            click.echo(f"FAIL: {name}: missing YAML frontmatter")
            errors += 1
            continue
        try:
            end = content.index("---", 3)
            fm = yaml.safe_load(content[3:end])
        except (ValueError, yaml.YAMLError) as e:
            click.echo(f"FAIL: {name}: invalid YAML: {e}")
            errors += 1
            continue
        if fm is None:
            click.echo(f"FAIL: {name}: empty frontmatter")
            errors += 1
            continue
        missing = REQUIRED_FRONTMATTER - fm.keys()
        if missing:
            click.echo(f"FAIL: {name}: missing keys: {missing}")
            errors += 1
            continue
        click.echo(f"OK: {name}")
    if errors > 0:
        raise click.ClickException(f"{errors} skill(s) failed validation")
