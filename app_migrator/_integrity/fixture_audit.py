"""Static audit of Frappe 16 fixture files: what the next `bench migrate` will rewrite.

Pure and bench-free: it reads files on disk and never touches a site.  The
live half (fixture record vs. live row) needs a site and is a separate
concern - see `LiveDiff` below for the seam.

Why a static half is worth having on its own
--------------------------------------------
Frappe 16 reads app content through four different mechanisms, and only one
of them is what people call "the fixtures".  Which mechanism owns a file
decides whether `bench migrate --skip-fixtures` protects it:

| mechanism | reads | skip-protected |
|---|---|---|
| `sync_fixtures()` | `<app>/fixtures/*.json` (primary module, non-recursive) | YES |
| `sync_all()` | `<module>/<doctype>/<name>/<name>.json` doc-files | no |
| `sync_customizations()` | `<module>/custom/**` | no |
| `remove_orphan_entities()` | deletes rows whose backing file is gone | no |

So "the fixtures are fine" is not a safe statement about a site.  This
module finds the files each mechanism will read and reports the record
classes that get rewritten.

The rewrite rules, from frappe 16 source
---------------------------------------
- App-level `fixtures/*.json` -> `sync_fixtures()` -> `import_doc(file)` ->
  `import_file_by_path(..., force=True)`.  `force=True` bypasses the skip
  check, so **every** record in those files is deleted and re-inserted on
  every migrate, whether or not it carries `modified`.
- Doc-files -> `sync_all()` -> `import_file_by_path(..., force=0)`.  Here the
  `modified` comparison applies, and a record *without* `modified` is
  always re-imported, because `frappe.utils.get_datetime(None)` returns
  `now_datetime()` - "modified now" always beats the stored timestamp.  A
  record *with* an older `modified` is skipped.
- `sync_customizations()` replaces the whole Custom DocPerm set for a
  DocType (delete + re-insert), and re-inserts Property Setters.

See app_migrator's L520/L521/L522 memory entries for the receipts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, NamedTuple

SCHEMA_VERSION = "1.0.0"

# frappe/model/sync.py IMPORTABLE_DOCTYPES - the doctypes a module may ship
# as a doc-file, i.e. `<module>/<doctype>/<scrubbed name>/<scrubbed name>.json`.
IMPORTABLE_DOCTYPES = (
    "permission_type",
    "doctype",
    "page",
    "report",
    "dashboard_chart_source",
    "print_format",
    "web_page",
    "website_theme",
    "web_form",
    "web_template",
    "notification",
    "print_style",
    "workspace",
    "workspace_sidebar",
    "sidebar",
    "onboarding_step",
    "module_onboarding",
    "form_tour",
    "client_script",
    "server_script",
    "custom_field",
    "property_setter",
)

# frappe/modules/utils.py sync_customizations() - the files under a module's
# `custom/` folder, each of which is a whole-file replace.
CUSTOMIZATION_FILES = (
    "custom_field.json",
    "property_setter.json",
    "custom_docperm.json",
    "client_script.json",
)

# Fields that carry a standard document's body.  An empty body in the file
# blanks the live document when the record is re-inserted.
BODY_FIELDS = ("html", "template", "script", "message", "content", "body", "query")

# Fields Frappe preserves across the delete+insert (frappe/modules/import_file.py
# IGNORE_VALUES).  A difference in one of these is not a revert.
IGNORE_VALUES = {
    "Report": ("disabled", "prepared_report", "add_total_row"),
    "Print Format": ("disabled",),
    "Notification": ("enabled",),
    "Workspace": ("is_hidden",),
}

# Fields that are metadata rather than configuration.  A difference confined
# to these is reported as its own class: the values are equal, so a
# value-only diff reports nothing, yet the row's ownership changes.
METADATA_FLAGS = ("is_system_generated", "migration_hash", "idx", "owner", "creation")

MECHANISM_APP_FIXTURE = "sync_fixtures"
MECHANISM_DOC_FILE = "sync_all"
MECHANISM_CUSTOMIZATION = "sync_customizations"


class FixtureFile(NamedTuple):
    """One file Frappe will read, and the mechanism that reads it."""

    app: str
    path: Path
    mechanism: str
    doctype: str
    module: str | None


class Record(NamedTuple):
    """One record inside a fixture file."""

    doctype: str
    name: str
    data: dict[str, Any]


def _scrub(text: str) -> str:
    """frappe.scrub: 'Sales Invoice' -> 'sales_invoice'."""
    out = []
    for ch in text:
        out.append(ch.lower() if ch.isalnum() else "_")
    return "".join(out).strip("_")


def _read_json(path: Path) -> list[dict[str, Any]]:
    """Read a fixture file into a list of records.

    Three shapes occur, and the third one is the doc-file shape:
      - a list of records              (app-level `fixtures/*.json`)
      - a dict of doctype -> [records] (some exported fixture files)
      - a dict that IS one record      (a doc-file: `<doctype>/<name>/<name>.json`)

    The third shape is easy to miss: reading its values as records yields
    strings, which are not records, so the file silently reads as empty.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        if "doctype" in data or "name" in data:
            return [data]
        out: list[dict[str, Any]] = []
        for value in data.values():
            if isinstance(value, list):
                out.extend(r for r in value if isinstance(r, dict))
            elif isinstance(value, dict):
                out.append(value)
        return out
    return []


def _looks_like_apps_dir(candidate: Path) -> bool:
    """True when a directory holds at least one app-shaped subdirectory.

    Guards against the false positive of an unrelated `apps/` directory
    higher up the tree (there is one under the user's local appdata on this
    host, which a naive walk-to-the-root finds).
    """
    try:
        children = [p for p in candidate.iterdir() if p.is_dir()]
    except OSError:
        return False
    for child in children:
        if (child / "pyproject.toml").is_file() or (child / "hooks.py").is_file():
            return True
        try:
            if any((m / "modules.txt").is_file() for m in child.iterdir() if m.is_dir()):
                return True
        except OSError:
            continue
    return False


def discover_apps_root(start: str | Path) -> Path | None:
    """Find a bench `apps/` directory at or under `start`.

    Returns None when there is none, so a caller can report "no apps root"
    rather than silently scanning nothing.
    """
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        apps = candidate / "apps"
        if apps.is_dir() and _looks_like_apps_dir(apps):
            return apps
    return None


def app_names(apps_root: Path) -> list[str]:
    """Installed app names, i.e. the directories under `apps/` that are apps.

    An app is a directory holding a `pyproject.toml` or a `hooks.py`, or a
    directory that contains at least one module directory (one with its own
    `modules.txt`).  A directory of assets is not an app.
    """
    names = []
    for child in sorted(p for p in apps_root.iterdir() if p.is_dir()):
        if (child / "pyproject.toml").is_file() or (child / "hooks.py").is_file():
            names.append(child.name)
            continue
        if any((m / "modules.txt").is_file() for m in child.iterdir() if m.is_dir()):
            names.append(child.name)
    return names


def _module_dirs(app_dir: Path) -> list[tuple[str, Path]]:
    """(module_name, module_dir) for each module of an app.

    `modules.txt` is authoritative when present; otherwise the app's own
    directory is its single module.  Frappe uses `app.local.app_modules`,
    which is built from modules.txt.
    """
    modules_file = app_dir / "modules.txt"
    if modules_file.is_file():
        try:
            raw = modules_file.read_text(encoding="utf-8")
        except OSError:
            raw = ""
        names = [line.strip() for line in raw.splitlines() if line.strip()]
    else:
        names = []
    dirs: list[tuple[str, Path]] = []
    for name in names:
        candidate = app_dir / _scrub(name)
        if candidate.is_dir():
            dirs.append((name, candidate))
    if not dirs and (app_dir / "__init__.py").is_file():
        dirs.append((app_dir.name, app_dir))
    return dirs


def discover_fixture_files(apps_root: Path) -> list[FixtureFile]:
    """Every file Frappe 16 will read for the given apps, with its mechanism.

    Classified by PATH SHAPE rather than by a strict directory layout, because
    an app's on-disk layout varies (the AMB apps are doubly nested, a bench
    checkout is not) and a layout model that assumes one silently matches
    zero - see L515.  Where the shape is ambiguous the finding text says so
    instead of guessing.

      <...>/fixtures/*.json       -> sync_fixtures()      (skippable)
      <...>/custom/*.json         -> sync_customizations() (not skippable)
      <...>/<doctype>/<n>/<n>.json -> sync_all() doc-file  (not skippable)
    """
    found: list[FixtureFile] = []
    for app in app_names(apps_root):
        app_dir = apps_root / app
        for path in sorted(app_dir.rglob("*.json")):
            parts = path.parts
            if len(parts) < 2:
                continue
            parent = parts[-2]
            stem = path.stem

            if parent == "fixtures":
                found.append(
                    FixtureFile(app, path, MECHANISM_APP_FIXTURE, _scrub(stem), None)
                )
                continue
            if parent == "custom":
                found.append(
                    FixtureFile(
                        app, path, MECHANISM_CUSTOMIZATION, _scrub(stem), _scrub(app)
                    )
                )
                continue
            # doc-file: <doctype>/<scrubbed name>/<scrubbed name>.json
            if len(parts) >= 3 and parent == stem and parts[-3] in IMPORTABLE_DOCTYPES:
                found.append(
                    FixtureFile(app, path, MECHANISM_DOC_FILE, parts[-3], None)
                )
                continue
            if len(parts) >= 3 and parent == stem and parts[-3] in (
                "list_filter",
                "kanban_board",
            ):
                found.append(
                    FixtureFile(app, path, MECHANISM_DOC_FILE, parts[-3], None)
                )
    return found


def _finding(
    finding_id: str,
    severity: str,
    title: str,
    detail: str,
    **extra: Any,
) -> dict[str, Any]:
    """A finding with a stable id, so two runs can be diffed."""
    out: dict[str, Any] = {
        "id": finding_id,
        "severity": severity,
        "title": title,
        "detail": detail,
    }
    out.update(extra)
    return out


def audit_records(ff: FixtureFile, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Findings for one fixture file's records."""
    findings: list[dict[str, Any]] = []
    for rec in records:
        doctype = rec.get("doctype") or ff.doctype
        name = rec.get("name") or "(no name)"
        base = {
            "app": ff.app,
            "module": ff.module,
            "file": str(ff.path),
            "mechanism": ff.mechanism,
            "doctype": doctype,
            "record": name,
        }

        if ff.mechanism == MECHANISM_APP_FIXTURE:
            # force=True: rewritten on every migrate regardless of `modified`.
            findings.append(
                _finding(
                    "FX-REIMPORTED-APP-FIXTURE",
                    "info",
                    "app-level fixture record is rewritten on every migrate",
                    (
                        "sync_fixtures() imports this file with force=True, which bypasses "
                        "the timestamp skip, so the record is deleted and re-inserted on every "
                        "migrate.  A value changed on the site is reverted to the file's value."
                    ),
                    **base,
                )
            )
        elif ff.mechanism == MECHANISM_DOC_FILE:
            if "modified" not in rec:
                findings.append(
                    _finding(
                        "FX-NO-MODIFIED-DOCFILE",
                        "warn",
                        "doc-file record has no `modified` and is re-imported every migrate",
                        (
                            "get_datetime(None) returns now_datetime(), so the file always looks "
                            "newer than the stored row.  The stored `modified` is not bumped by "
                            "the import, so this repeats forever.  --skip-fixtures does not "
                            "protect it: doc-files are read by sync_all()."
                        ),
                        **base,
                    )
                )

        if ff.mechanism == MECHANISM_CUSTOMIZATION and doctype == "Custom DocPerm":
            findings.append(
                _finding(
                    "FX-DOCPERM-WHOLE-SET-REPLACED",
                    "warn",
                    "Custom DocPerm set is replaced, not merged",
                    (
                        "sync_customizations() deletes every Custom DocPerm row for the "
                        "DocType and re-inserts the file's set.  A row added on the site is "
                        "dropped, and the file's rows win."
                    ),
                    **base,
                )
            )

        for field in BODY_FIELDS:
            if field in rec and rec[field] in ("", None, [], {}):
                findings.append(
                    _finding(
                        "FX-EMPTY-BODY",
                        "warn",
                        f"standard document body field `{field}` is empty in the file",
                        (
                            "The record is re-inserted from the file, so the live document is "
                            "written with an empty body.  Restore the body in the source."
                        ),
                        field=field,
                        **base,
                    )
                )
    return findings


def audit_apps_root(apps_root: Path) -> dict[str, Any]:
    """Audit every fixture file under an apps root.

    Returns a report dict: the files read, the records seen, and the
    findings.  Read-only; nothing is written and nothing is executed.
    """
    files = discover_fixture_files(apps_root)
    findings: list[dict[str, Any]] = []
    file_summaries: list[dict[str, Any]] = []
    total_records = 0
    mechanism_counts: dict[str, int] = {}

    # An app can ship more than one `fixtures/` folder - one per module.
    # Frappe 16's sync_fixtures() reads exactly ONE of them, the app's
    # primary-module folder (frappe.get_app_path(app, "fixtures")), and it
    # reads it with os.listdir, so it is not recursive either.  Which one
    # that is can only be settled on the bench; here we report the fact.
    fixture_folders: dict[str, set[str]] = {}
    for ff in files:
        if ff.mechanism == MECHANISM_APP_FIXTURE:
            fixture_folders.setdefault(ff.app, set()).add(str(ff.path.parent))

    for ff in files:
        records = _read_json(ff.path)
        total_records += len(records)
        mechanism_counts[ff.mechanism] = mechanism_counts.get(ff.mechanism, 0) + 1
        findings.extend(audit_records(ff, records))
        file_summaries.append(
            {
                "app": ff.app,
                "module": ff.module,
                "file": str(ff.path),
                "mechanism": ff.mechanism,
                "doctype": ff.doctype,
                "records": len(records),
                "without_modified": sum(1 for r in records if "modified" not in r),
            }
        )

    for app, folders in sorted(fixture_folders.items()):
        if len(folders) > 1:
            for folder in sorted(folders):
                records_here = sum(
                    s["records"]
                    for s in file_summaries
                    if s["mechanism"] == MECHANISM_APP_FIXTURE
                    and str(Path(s["file"]).parent) == folder
                )
                findings.append(
                    _finding(
                        "FX-MULTIPLE-FIXTURE-FOLDERS",
                        "warn",
                        "app ships more than one fixtures/ folder; sync_fixtures() reads one",
                        (
                            f"This app has {len(folders)} `fixtures/` folders.  "
                            "frappe.utils.fixtures.sync_fixtures() reads a single one - "
                            "frappe.get_app_path(app, 'fixtures'), the app's primary-module "
                            "folder - and does not recurse.  Records in the folders it does "
                            "not read are never applied to the site.  Settle which folder "
                            "that is on the bench (frappe.get_app_path(app, 'fixtures')) "
                            "before trusting any count."
                        ),
                        app=app,
                        folder=folder,
                        records_in_folder=records_here,
                    )
                )

    by_id: dict[str, int] = {}
    for f in findings:
        by_id[f["id"]] = by_id.get(f["id"], 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "apps_root": str(apps_root),
        "files": file_summaries,
        "file_count": len(files),
        "record_count": total_records,
        "mechanism_counts": mechanism_counts,
        "fixture_folders_per_app": {k: sorted(v) for k, v in fixture_folders.items()},
        "findings": findings,
        "finding_counts": by_id,
    }


def iter_never_modified(report: dict[str, Any]) -> Iterator[tuple[str, str, str]]:
    """(app, file, record) for every record a migrate will rewrite.

    This is the set that decides whether the next migrate is safe: app-level
    fixture records (always) plus doc-file records with no `modified`.
    """
    for summary in report["files"]:
        if summary["mechanism"] == MECHANISM_APP_FIXTURE:
            for f in report["findings"]:
                if (
                    f["id"] == "FX-REIMPORTED-APP-FIXTURE"
                    and f["file"] == summary["file"]
                    and f["record"] != "(no name)"
                ):
                    yield summary["app"], summary["file"], f["record"]
        elif summary["mechanism"] == MECHANISM_DOC_FILE and summary["without_modified"]:
            for f in report["findings"]:
                if (
                    f["id"] == "FX-NO-MODIFIED-DOCFILE"
                    and f["file"] == summary["file"]
                ):
                    yield summary["app"], summary["file"], f["record"]


# ---------------------------------------------------------------------------
# CLI
#
# Runnable standalone: the module is pure stdlib and imports nothing from the
# app_migrator package, so it can be dropped next to a bench and run with the
# system python - no bench, no site, no frappe import:
#
#     python3 fixture_audit.py --apps-root ~/frappe-bench/apps --summary
#     python3 fixture_audit.py --apps-root ~/frappe-bench/apps --json > audit.json
# ---------------------------------------------------------------------------


def _print_summary(report: dict[str, Any]) -> None:
    print(f"apps_root     : {report['apps_root']}")
    print(f"files read    : {report['file_count']}")
    print(f"records seen  : {report['record_count']}")
    print(f"by mechanism  : {report['mechanism_counts']}")
    print()
    print("FINDING COUNTS")
    for finding_id, count in sorted(report["finding_counts"].items()):
        print(f"  {count:6}  {finding_id}")
    print()
    print("RECORDS A MIGRATE WILL REWRITE (app-level fixtures always; doc-files with no `modified`)")
    by_app: dict[str, int] = {}
    for app, _file, _record in iter_never_modified(report):
        by_app[app] = by_app.get(app, 0) + 1
    for app in sorted(by_app):
        print(f"  {by_app[app]:6}  {app}")
    print(f"  {sum(by_app.values()):6}  TOTAL")
    print()
    print("EMPTY STANDARD-DOCUMENT BODIES")
    for f in report["findings"]:
        if f["id"] == "FX-EMPTY-BODY":
            print(f"  {f['app']} / {f['doctype']} / {f['record']} / {f['field']}")
    print()
    print("APPS WITH MORE THAN ONE fixtures/ FOLDER (sync_fixtures() reads only one)")
    for f in report["findings"]:
        if f["id"] == "FX-MULTIPLE-FIXTURE-FOLDERS":
            print(f"  {f['app']}  {f['folder']}  ({f['records_in_folder']} records)")


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        prog="fixture_audit",
        description="Report which fixture records a Frappe 16 migrate will rewrite.",
    )
    parser.add_argument(
        "--apps-root",
        default=None,
        help="path to the bench apps/ directory (default: search upward from cwd)",
    )
    parser.add_argument("--json", action="store_true", help="emit the full report as JSON")
    parser.add_argument(
        "--summary", action="store_true", help="emit a human summary (this is the default)"
    )
    args = parser.parse_args(argv)

    if args.apps_root:
        apps_root = Path(args.apps_root).expanduser().resolve()
        if not apps_root.is_dir():
            print(f"not a directory: {apps_root}", file=sys.stderr)
            return 2
    else:
        apps_root = discover_apps_root(Path.cwd())
        if apps_root is None:
            print("no apps root found; pass --apps-root", file=sys.stderr)
            return 2

    report = audit_apps_root(apps_root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
