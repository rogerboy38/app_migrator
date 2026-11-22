"""Live half of the fixture pre-flight: compare every app-level fixture
record against the live row on this site.

READ-ONLY.  Every statement is a SELECT.  Nothing is written, nothing is
imported, no migrate is run.

Run it inside a bench console, so that `frappe` is imported and bound to the
site:

    bench --site <site> console < scripts/live_fixture_diff.py

It answers three questions, per app:

1.  Which folder will sync_fixtures() read for this app?  Frappe 16 reads
    exactly ONE `fixtures/` folder per app - frappe.get_app_path(app,
    "fixtures") - and does not recurse, so any other `fixtures/` folder the
    app ships is never applied.  This prints the path Frappe uses and the
    folders it ignores.

2.  Which records differ from the live row, field by field?  That is the
    per-record answer to "which side is right" for the records the handoff
    lists.  Differences confined to a metadata flag are listed separately:
    the values are equal, so a value-only diff reports nothing, yet the
    row's ownership changes.

3.  Which Custom DocPerm rows grant a right that the controller refuses?
    A permission fixture outliving the rule it served leaves the Desk
    offering an action that is refused at submit time.

The static half of the pre-flight is a separate script and needs no site:
app_migrator/_integrity/fixture_audit.py.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys

try:
    import frappe
except ImportError:  # pragma: no cover - the pure helpers below are testable offline
    frappe = None

# Fields that are metadata rather than configuration.  A difference confined
# to one of these changes row ownership without changing any value.
METADATA_FLAGS = ("is_system_generated", "migration_hash", "idx", "owner", "creation")

# Fields that are never compared: identity, bookkeeping, and the record's own
# bookkeeping timestamps (the `modified` gap is reported separately).
SKIP_FIELDS = frozenset(
    {
        "doctype",
        "name",
        "modified",
        "modified_by",
        "creation",
        "owner",
        "idx",
        "__islocal",
        "__unsaved",
        "parent",
        "parenttype",
        "parentfield",
        "docstatus",
    }
)

# The controller method that governs each permission.
RIGHT_TO_METHOD = {
    "submit": "submit",
    "cancel": "cancel",
    "amend": "amend",
    "delete": "on_trash",
}


def scrub(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text or "").strip("_").lower()


def normalise(value) -> str:
    """Comparable form of a field value.

    A fixture JSON carries "1" where the column is an integer, so compare
    everything as text; lists and dicts compare by their JSON form.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return json.dumps([str(v) for v in value], sort_keys=True)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value).strip()


def read_records(path: str) -> list[tuple[str, dict]]:
    """Records in one fixture file.

    Three shapes occur: a list of records, a dict of doctype -> [records],
    and a dict that IS one record.  The third is easy to miss - reading its
    values yields strings, which are not records.
    """
    out: list[tuple[str, dict]] = []
    for filename in sorted(os.listdir(path)):
        if not filename.endswith(".json"):
            continue
        full = os.path.join(path, filename)
        try:
            with open(full, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            print(f"  ! {filename}: unreadable ({exc})")
            continue
        records: list[dict] = []
        if isinstance(data, list):
            records = [r for r in data if isinstance(r, dict)]
        elif isinstance(data, dict):
            if "doctype" in data or "name" in data:
                records = [data]
            else:
                for value in data.values():
                    if isinstance(value, list):
                        records.extend(r for r in value if isinstance(r, dict))
                    elif isinstance(value, dict):
                        records.append(value)
        for rec in records:
            out.append((filename, rec))
    return out


def all_fixture_folders(app_root: str) -> list[str]:
    """Every `fixtures/` folder the app ships, not only the one Frappe reads."""
    found = []
    for dirpath, dirnames, filenames in os.walk(app_root):
        if os.path.basename(dirpath) == "fixtures":
            found.append(dirpath)
    return sorted(found)


def controller_source(app: str, doctype: str) -> str | None:
    """The source of the DocType's controller, if the app ships one."""
    try:
        module = frappe.get_meta(doctype).module
    except Exception:
        return None
    if not module:
        return None
    try:
        module_path = frappe.get_module_path(f"{app}.{scrub(module)}")
    except Exception:
        return None
    if not module_path:
        return None
    candidate = os.path.join(
        module_path, "doctype", scrub(doctype), f"{scrub(doctype)}.py"
    )
    if os.path.isfile(candidate):
        try:
            with open(candidate, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return None
    return None


def controller_refusals(source: str | None, method: str) -> list[str]:
    """The lines in `method` that look like a refusal."""
    if not source:
        return []
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    lines = source.splitlines()
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != method:
            continue
        for sub in ast.walk(node):
            kind = None
            if isinstance(sub, ast.Raise):
                kind = "raise"
            elif isinstance(sub, ast.Call):
                name = getattr(sub.func, "attr", None) or getattr(sub.func, "id", None)
                if name == "throw":
                    kind = "frappe.throw"
            if kind and 0 < sub.lineno <= len(lines):
                hits.append(f"{sub.lineno}: {lines[sub.lineno - 1].strip()[:110]}")
    return hits


def print_paths() -> None:
    print("=" * 100)
    print("1. WHICH fixtures/ FOLDER Frappe 16 WILL READ")
    print("=" * 100)
    for app in frappe.get_installed_apps():
        try:
            read_path = frappe.get_app_path(app, "fixtures")
        except Exception as exc:
            print(f"  {app}: get_app_path failed ({exc})")
            continue
        print(f"\n  {app}")
        print(f"      READS      : {read_path}  (exists={os.path.isdir(read_path)})")
        app_root = os.path.dirname(os.path.dirname(read_path))
        others = [p for p in all_fixture_folders(app_root) if os.path.abspath(p) != os.path.abspath(read_path)]
        for other in others:
            records = sum(len(read_records(other)))
            print(f"      NOT READ   : {other}  ({records} records never applied)")


def print_diffs() -> None:
    print()
    print("=" * 100)
    print("2. FIXTURE RECORDS THAT DIFFER FROM THE LIVE ROW")
    print("=" * 100)
    total_records = 0
    total_differing = 0
    for app in frappe.get_installed_apps():
        try:
            path = frappe.get_app_path(app, "fixtures")
        except Exception:
            continue
        if not os.path.isdir(path):
            continue
        app_differing = 0
        for filename, rec in read_records(path):
            total_records += 1
            doctype = rec.get("doctype")
            name = rec.get("name")
            if not doctype or not name:
                print(f"  ? {app}/{filename}: record without doctype/name - not comparable")
                continue
            if not frappe.db.exists(doctype, name):
                print(f"  + {app}/{doctype} '{name}': NOT ON THIS SITE (a migrate would create it)")
                continue
            live = frappe.db.get_value(doctype, name, "*", as_dict=True) or {}
            value_diffs = []
            flag_diffs = []
            for field, file_value in rec.items():
                if field in SKIP_FIELDS:
                    continue
                live_value = live.get(field)
                if normalise(live_value) == normalise(file_value):
                    continue
                entry = (field, live_value, file_value)
                if field in METADATA_FLAGS:
                    flag_diffs.append(entry)
                else:
                    value_diffs.append(entry)
            if not value_diffs and not flag_diffs:
                continue
            app_differing += 1
            total_differing += 1
            live_modified = live.get("modified")
            file_modified = rec.get("modified")
            print(f"\n  ~ {app}/{doctype} '{name}'   [{filename}]")
            print(f"      live modified={live_modified}   file modified={file_modified}")
            for field, live_value, file_value in value_diffs:
                print(f"      VALUE  {field:26} live={normalise(live_value)[:40]:42} file={normalise(file_value)[:40]}")
            for field, live_value, file_value in flag_diffs:
                print(f"      FLAG   {field:26} live={normalise(live_value)[:40]:42} file={normalise(file_value)[:40]}")
        if app_differing:
            print(f"\n  -- {app}: {app_differing} differing records")
    print(f"\n  TOTAL records compared : {total_records}")
    print(f"  TOTAL differing records: {total_differing}")


def print_permission_checks() -> None:
    print()
    print("=" * 100)
    print("3. PERMISSION FIXTURES THAT GRANT A RIGHT A CONTROLLER REFUSES")
    print("=" * 100)
    hits = 0
    for app in frappe.get_installed_apps():
        try:
            path = frappe.get_app_path(app, "fixtures")
        except Exception:
            continue
        docperm = os.path.join(path, "custom_docperm.json")
        if not os.path.isfile(docperm):
            continue
        for filename, rec in read_records(path):
            if rec.get("doctype") != "Custom DocPerm":
                continue
            parent = rec.get("parent")
            role = rec.get("role")
            if not parent:
                continue
            source = controller_source(app, parent)
            for right, method in RIGHT_TO_METHOD.items():
                try:
                    granted = int(rec.get(right) or 0)
                except (TypeError, ValueError):
                    granted = 0
                if not granted:
                    continue
                refusals = controller_refusals(source, method)
                if not refusals:
                    continue
                hits += 1
                print(f"\n  ! {app}/{parent}: role '{role}' still holds '{right}'")
                print(f"      the controller's {method}() refuses:")
                for line in refusals[:3]:
                    print(f"          {line}")
                print(f"      fixture modified: {'YES' if 'modified' in rec else 'NO'}")
    if not hits:
        print("  none")


class _Tee:
    """Write to stdout and to a file, so a console that echoes oddly still
    leaves a clean report behind."""

    def __init__(self, stream, path: str):
        self.stream = stream
        self.path = path
        self.handle = None
        try:
            self.handle = open(path, "w", encoding="utf-8")
        except OSError:
            self.handle = None

    def write(self, text: str) -> int:
        if self.handle is not None:
            try:
                self.handle.write(text)
            except OSError:
                pass
        return self.stream.write(text)

    def flush(self) -> None:
        if self.handle is not None:
            try:
                self.handle.flush()
            except OSError:
                pass
        try:
            self.stream.flush()
        except OSError:
            pass

    def close(self) -> None:
        if self.handle is not None:
            try:
                self.handle.close()
            except OSError:
                pass
            self.handle = None


def main() -> None:
    tee = _Tee(sys.stdout, "/tmp/live-fixture-diff.txt")
    real_stdout = sys.stdout
    sys.stdout = tee
    try:
        print_paths()
        print_diffs()
        print_permission_checks()
        print()
        print("DONE - read-only run, nothing was written.")
        print("A copy of this report is in /tmp/live-fixture-diff.txt")
    finally:
        sys.stdout = real_stdout
        tee.close()


if frappe is not None:
    main()
