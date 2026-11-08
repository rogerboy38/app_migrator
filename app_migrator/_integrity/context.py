"""Read-only inventory of a bench's apps directory.

Every integrity check needs the same answers to the same questions:

- which apps are installed, and where is each app's Python package?
- which DocTypes does each app ship, and what fields does each have?
- which Custom Fields / Property Setters does each app ship in its fixtures?
- what does each app's ``hooks.py`` declare?

Collecting that once, up front, keeps each check a small pure function and
keeps the whole family fast enough to run on every commit.

Nothing here imports ``frappe`` or touches the database: the inventory is
purely a filesystem + parse view, so the checks are bench-free and testable
in-process.
"""
from __future__ import annotations

import ast
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

#: Environment variables that point at the bench root.
BENCH_ROOT_ENV_VARS = ("FRAPPE_BENCH", "BENCH_PATH")

#: Environment variables that point at the ``apps/`` directory itself.
APPS_ROOT_ENV_VARS = ("BENCH_APPS_ROOT", "FRAPPE_APPS_ROOT")

#: Last-resort default, used only when nothing else can be discovered.
FALLBACK_APPS_ROOT = "/home/frappe/frappe-bench/apps"


def _looks_like_bench(path: str) -> bool:
    """True when ``path`` is a Frappe bench root.

    Detection triple: an ``apps/`` directory, ``sites/apps.txt`` and a
    ``Procfile``. This mirrors ``app_migrator.commands._shared.find_bench_root``
    but is written out here on purpose: importing that module would import
    ``app_migrator.commands``, whose ``__init__`` imports ``frappe`` — and
    this package must stay import-safe on a host that has no bench.
    """
    return (
        os.path.isdir(os.path.join(path, "apps"))
        and os.path.isfile(os.path.join(path, "sites", "apps.txt"))
        and os.path.isfile(os.path.join(path, "Procfile"))
    )


def discover_apps_root() -> str:
    """Locate the bench ``apps/`` directory to scan.

    Resolution order:

    1. ``BENCH_APPS_ROOT`` / ``FRAPPE_APPS_ROOT`` — the apps directory itself.
    2. ``FRAPPE_BENCH`` / ``BENCH_PATH`` — a bench root; ``apps/`` is
       appended when that directory exists.
    3. The current working directory, walked upwards for a bench root.
    4. ``~/frappe-bench``, when it exists.
    5. The historical ``/home/frappe/frappe-bench/apps`` default.

    The old behaviour was that last path *unconditionally*, so on any bench
    that is not laid out exactly that way the scan silently looked at a
    directory that does not exist and reported nothing at all.
    """
    for var in APPS_ROOT_ENV_VARS:
        value = os.environ.get(var)
        if value:
            return value

    for var in BENCH_ROOT_ENV_VARS:
        bench = os.environ.get(var)
        if bench:
            apps = os.path.join(bench, "apps")
            return apps if os.path.isdir(apps) else bench

    try:
        current = os.path.abspath(os.getcwd())
    except OSError:  # pragma: no cover - defensive
        current = ""
    candidate = current
    while candidate:
        if _looks_like_bench(candidate):
            return os.path.join(candidate, "apps")
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent

    home_bench = os.path.expanduser("~/frappe-bench")
    if os.path.isdir(home_bench):
        return os.path.join(home_bench, "apps")

    return FALLBACK_APPS_ROOT


DEFAULT_APPS_ROOT = discover_apps_root()


def scrub(name: str) -> str:
    """Frappe's folder slug for a DocType name (``Movement Type`` -> ``movement_type``)."""
    return (name or "").strip().lower().replace(" ", "_").replace("-", "_")

# Directories that never contain app source we want to reason about.
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "env", "dist", "build",
    ".eggs", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages",
}

# Fixture files we know how to read.
CUSTOM_FIELD_FIXTURE = "custom_field.json"
PROPERTY_SETTER_FIXTURE = "property_setter.json"
# A DocType export: a list of DocType records (each with ``name`` + ``fields``).
DOCTYPE_FIXTURE = "doctype.json"
# A Workflow export. Each record names the ``document_type`` it governs and the
# ``workflow_state_field`` Frappe creates as a Custom Field on that DocType.
WORKFLOW_FIXTURE = "workflow.json"


def iter_python_files(package_dir: str, skip_dirs: set[str] | None = None) -> Iterator[str]:
    """Yield every ``.py`` file under ``package_dir``, skipping build/vendor dirs."""
    skip = SKIP_DIRS if skip_dirs is None else skip_dirs
    if not os.path.isdir(package_dir):
        return
    for dirpath, dirnames, filenames in os.walk(package_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in skip)
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def read_text(path: str) -> str:
    """Read a file as UTF-8, replacing undecodable bytes. Never raises."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def read_json(path: str) -> Any:
    """Load a JSON file; return ``None`` on any failure (best-effort scanner)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def parse_python(path: str) -> ast.Module | None:
    """Parse a Python file; return ``None`` when it does not parse."""
    source = read_text(path)
    if not source.strip():
        return None
    try:
        return ast.parse(source)
    except (SyntaxError, ValueError):
        return None


def literal_or_none(node: ast.AST) -> Any:
    """Evaluate an AST node to a Python literal, or ``None`` if it is not one."""
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return None


def _fieldnames_of(definition: dict[str, Any]) -> set[str]:
    """The fieldnames a DocType definition (JSON record) declares."""
    names: set[str] = set()
    for fielddef in definition.get("fields") or []:
        if isinstance(fielddef, dict) and fielddef.get("fieldname"):
            names.add(fielddef["fieldname"])
    return names


@dataclass
class HookInfo:
    """What an app's ``hooks.py`` declares.

    ``assignments`` maps a top-level name to its literal value when the value
    is a literal (e.g. ``required_apps = ["erpnext"]``), otherwise to ``None``
    with the raw AST node kept in ``nodes`` so checks can inspect it.
    """

    path: str | None
    assignments: dict[str, Any] = field(default_factory=dict)
    nodes: dict[str, ast.AST] = field(default_factory=dict)
    parse_error: bool = False

    def get(self, name: str, default: Any = None) -> Any:
        value = self.assignments.get(name, default)
        return value

    def node(self, name: str) -> ast.AST | None:
        return self.nodes.get(name)

    def literal_dict(self, name: str) -> dict[str, Any]:
        """Return a hook value only when it is a literal dict."""
        value = self.assignments.get(name)
        return value if isinstance(value, dict) else {}


@dataclass
class AppInfo:
    """One installed Frappe app."""

    name: str
    root: str
    package: str
    hooks: HookInfo = field(default_factory=lambda: HookInfo(path=None))
    _doctype_dirs_cache: list[str] | None = field(default=None, repr=False)
    _fixture_doctypes_cache: dict[str, dict[str, Any]] | None = field(default=None, repr=False)
    _workflow_state_fields_cache: dict[str, set[str]] | None = field(default=None, repr=False)

    # -- DocTypes ---------------------------------------------------------
    def _doctype_dirs(self) -> list[str]:
        """Every ``doctype`` directory under this app's package.

        Frappe apps are not consistent about where their DocTypes live. The
        common shape is ``<app>/<app>/doctype/``, but the audited apps use a
        **doubly nested** package (``<app>/<app>/<app>/doctype/``) and
        ``amb_w_spc`` spreads its modules across sibling directories
        (``core_spc/``, ``fda_compliance/``), each with its own ``doctype/``.
        Rather than hard-code one shape, find them all — a layout assumption
        that silently matches nothing reports zero findings, which is the
        worst possible failure mode for a detector.
        """
        if self._doctype_dirs_cache is not None:
            return self._doctype_dirs_cache
        found: list[str] = []
        package = self.package
        base_depth = package.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, _filenames in os.walk(package):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            if dirpath.count(os.sep) - base_depth > 3:
                dirnames[:] = []
                continue
            if os.path.basename(dirpath) == "doctype":
                found.append(dirpath)
                dirnames[:] = []  # do not descend into a doctype tree
        self._doctype_dirs_cache = sorted(found)
        return self._doctype_dirs_cache

    def _doctype_dir_json_paths(self) -> dict[str, str]:
        """Map DocType name -> path of its package-directory ``.json`` file.

        The DocType name comes from the JSON's ``name`` field when present
        (that is the name Frappe uses), falling back to the folder name.
        """
        found: dict[str, str] = {}
        for doctype_dir in self._doctype_dirs():
            for entry in sorted(os.listdir(doctype_dir)):
                dt_dir = os.path.join(doctype_dir, entry)
                if not os.path.isdir(dt_dir):
                    continue
                json_path = os.path.join(dt_dir, f"{entry}.json")
                if not os.path.isfile(json_path):
                    continue
                data = read_json(json_path)
                name = entry
                if isinstance(data, dict) and isinstance(data.get("name"), str) and data["name"]:
                    name = data["name"]
                found.setdefault(name, json_path)
        return found

    def doctype_json_paths(self) -> dict[str, str]:
        """Map DocType name -> path of its ``.json`` definition.

        The DocType name comes from the JSON's ``name`` field when present
        (that is the name Frappe uses), falling back to the folder name.

        DocTypes shipped as a **fixture** are indexed too. ``rnd_warehouse_
        management`` ships ``Movement Type`` as a ``fixtures/doctype.json``
        export rather than as a package ``doctype/`` directory, so an
        inventory that only walks package directories cannot see that
        DocType at all -- and every check that asks "does this DocType have
        that field?" then answers "no such DocType". The path of a
        fixture-shipped DocType is the fixture file itself, which holds one
        record per DocType.

        When a DocType is shipped both ways the package directory wins for
        the path, but the fixture's fields are kept (see ``fieldnames_for``).
        """
        found = self._doctype_dir_json_paths()
        fixture_path = self.fixture_path(DOCTYPE_FIXTURE)
        if fixture_path:
            package_names = {name.lower() for name in found}
            for name in self.fixture_doctypes():
                if name.lower() in package_names:
                    continue
                found[name] = fixture_path
        return found

    def fixture_doctypes(self) -> dict[str, dict[str, Any]]:
        """DocTypes this app ships as a fixture export (``fixtures/doctype.json``).

        The export is a list of DocType records; each record carries the
        DocType ``name`` and its ``fields``. Returns a mapping of DocType
        name -> record (empty when the app ships no such fixture).
        """
        if self._fixture_doctypes_cache is not None:
            return self._fixture_doctypes_cache
        found: dict[str, dict[str, Any]] = {}
        path = self.fixture_path(DOCTYPE_FIXTURE)
        if path:
            data = read_json(path)
            if isinstance(data, list):
                for record in data:
                    if not isinstance(record, dict):
                        continue
                    name = record.get("name")
                    if isinstance(name, str) and name.strip():
                        found.setdefault(name, record)
        self._fixture_doctypes_cache = found
        return found

    def workflow_state_fields(self) -> dict[str, set[str]]:
        """DocType -> the workflow state field names Frappe creates for it.

        Frappe's workflow sync creates a Custom Field on the governed
        DocType, named after the Workflow's ``workflow_state_field``. That
        name is **configurable** -- the audited apps use both
        ``workflow_state`` and ``workflow_state_1`` -- so it cannot be
        hard-coded. Reading ``doc.workflow_state`` off a DocType that has a
        shipped workflow is therefore *not* a missing field, and reporting
        it would be a false positive.
        """
        if self._workflow_state_fields_cache is not None:
            return self._workflow_state_fields_cache
        found: dict[str, set[str]] = {}
        path = self.fixture_path(WORKFLOW_FIXTURE)
        if path:
            data = read_json(path)
            records = data if isinstance(data, list) else []
            for record in records:
                if not isinstance(record, dict):
                    continue
                doctype = record.get("document_type")
                fieldname = record.get("workflow_state_field")
                if not isinstance(doctype, str) or not doctype.strip():
                    continue
                if not isinstance(fieldname, str) or not fieldname.strip():
                    continue
                found.setdefault(doctype, set()).add(fieldname.strip())
        self._workflow_state_fields_cache = found
        return found

    def _doctype_definition_for(self, doctype: str) -> dict[str, Any] | None:
        """The package-directory definition of ``doctype`` (None when absent)."""
        paths = self._doctype_dir_json_paths()
        path = paths.get(doctype)
        if path is None:
            # Fall back to a case-insensitive match: MariaDB's default
            # collation is case-insensitive, so "Plant Configuration" and
            # "plant configuration" are the same DocType on a real site.
            lowered = doctype.lower()
            for key, candidate in paths.items():
                if key.lower() == lowered:
                    path = candidate
                    break
        if not path:
            return None
        data = read_json(path)
        return data if isinstance(data, dict) else None

    def _fixture_definitions_for(self, doctype: str) -> list[dict[str, Any]]:
        """Fixture records that define ``doctype`` (case-insensitive)."""
        records = self.fixture_doctypes()
        if doctype in records:
            return [records[doctype]]
        lowered = doctype.lower()
        return [record for name, record in records.items() if name.lower() == lowered]

    def fieldnames_for(self, doctype: str) -> set[str]:
        """Field names available on ``doctype`` (standard fields + custom fields).

        Custom fields are the ones an app ships in ``fixtures/custom_field.json``
        for that doctype. Fields of a DocType shipped as a **fixture**
        (``fixtures/doctype.json``) count as well: for such a DocType the
        fixture is the definition, so its fields are the DocType's fields.
        A DocType shipped both as a package directory and as a fixture keeps
        the fields of both.
        """
        names: set[str] = set()
        definition = self._doctype_definition_for(doctype)
        if definition is not None:
            names |= _fieldnames_of(definition)
        for record in self._fixture_definitions_for(doctype):
            names |= _fieldnames_of(record)
        for cf in self.custom_fields():
            if cf.get("dt") == doctype and cf.get("fieldname"):
                names.add(cf["fieldname"])
        # Frappe creates the workflow state field as a Custom Field when the
        # Workflow is synced, so it exists at runtime even though no app
        # ships it in a fixture.
        for fieldname in self.workflow_state_fields().get(doctype, ()):
            names.add(fieldname)
        return names

    # -- Fixtures ---------------------------------------------------------
    def fixture_path(self, filename: str) -> str | None:
        """Locate a fixture file.

        Frappe apps ship fixtures either inside the Python package
        (``<app>/<app>/fixtures/`` — what all three audited apps do) or at
        the app root (``<app>/fixtures/``). Both are checked.
        """
        for base in (self.package, self.root):
            path = os.path.join(base, "fixtures", filename)
            if os.path.isfile(path):
                return path
        return None

    def custom_fields(self) -> list[dict[str, Any]]:
        """Custom Field records shipped by this app (may be empty)."""
        path = self.fixture_path(CUSTOM_FIELD_FIXTURE)
        if not path:
            return []
        data = read_json(path)
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []

    def property_setters(self) -> list[dict[str, Any]]:
        """Property Setter records shipped by this app (may be empty)."""
        path = self.fixture_path(PROPERTY_SETTER_FIXTURE)
        if not path:
            return []
        data = read_json(path)
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []

    def required_apps(self) -> list[str]:
        """``required_apps`` as declared in hooks.py (empty when absent)."""
        value = self.hooks.get("required_apps")
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value]
        return []


class Inventory:
    """Everything the integrity checks are allowed to look at.

    Constructed once per run and passed read-only to each check.
    """

    def __init__(
        self,
        apps_root: str = DEFAULT_APPS_ROOT,
        app_names: list[str] | None = None,
    ) -> None:
        self.apps_root = apps_root
        self.apps: list[AppInfo] = []
        self._by_name: dict[str, AppInfo] = {}
        self._doctype_paths: dict[str, dict[str, str]] = {}
        self._load(app_names)

    # -- construction -----------------------------------------------------
    def _load(self, app_names: list[str] | None) -> None:
        for name in (app_names if app_names is not None else self._iter_app_names()):
            app = self._build_app(name)
            if app is None:
                continue
            self.apps.append(app)
            self._by_name[name] = app

    def _iter_app_names(self) -> list[str]:
        """Installed app names: ``apps.txt`` when present, else directory scan."""
        apps_txt = os.path.join(self.apps_root, "apps.txt")
        if os.path.isfile(apps_txt):
            names = [ln.strip() for ln in read_text(apps_txt).splitlines() if ln.strip()]
            if names:
                return names
        if not os.path.isdir(self.apps_root):
            return []
        names = []
        for entry in sorted(os.listdir(self.apps_root)):
            if not os.path.isdir(os.path.join(self.apps_root, entry)):
                continue
            # A real app has its package inside the app dir.
            if os.path.isdir(os.path.join(self.apps_root, entry, entry)):
                names.append(entry)
        return names

    def _build_app(self, name: str) -> AppInfo | None:
        root = os.path.join(self.apps_root, name)
        if not os.path.isdir(root):
            return None
        package = os.path.join(root, name)
        if not os.path.isdir(package):
            package = root
        hooks = self._load_hooks(self._find_hooks_py(root, package))
        return AppInfo(name=name, root=root, package=package, hooks=hooks)

    @staticmethod
    def _find_hooks_py(root: str, package: str) -> str | None:
        """Locate the app's ``hooks.py``.

        Frappe reads ``<app>/hooks.py`` relative to the *app* directory, but
        the audited apps keep it **inside** the Python package
        (``<app>/<app>/hooks.py``) because their package is nested. Both
        layouts are checked, app root first.
        """
        for candidate in (os.path.join(root, "hooks.py"), os.path.join(package, "hooks.py")):
            if os.path.isfile(candidate):
                return candidate
        return None

    def _load_hooks(self, path: str | None) -> HookInfo:
        if not path:
            return HookInfo(path=None)
        tree = parse_python(path)
        if tree is None:
            return HookInfo(path=path, parse_error=True)
        info = HookInfo(path=path)
        for node in tree.body:
            targets: list[str] = []
            value_node: ast.AST | None = None
            if isinstance(node, ast.Assign):
                value_node = node.value
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        targets.append(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets.append(node.target.id)
                value_node = node.value
            for target_name in targets:
                info.assignments[target_name] = (
                    literal_or_none(value_node) if value_node is not None else None
                )
                info.nodes[target_name] = node
        return info

    # -- accessors --------------------------------------------------------
    def app(self, name: str) -> AppInfo | None:
        return self._by_name.get(name)

    def doctype_paths(self, app_name: str) -> dict[str, str]:
        cached = self._doctype_paths.get(app_name)
        if cached is None:
            app = self.app(app_name)
            cached = app.doctype_json_paths() if app else {}
            self._doctype_paths[app_name] = cached
        return cached

    def all_shipped_doctypes(self) -> dict[str, set[str]]:
        """DocType name -> set of apps that ship it."""
        shipped: dict[str, set[str]] = {}
        for app in self.apps:
            for dt in self.doctype_paths(app.name):
                shipped.setdefault(dt, set()).add(app.name)
        return shipped

    def app_for_doctype(self, doctype: str) -> list[str]:
        """Apps that ship a DocType with this name.

        Three matches are tried, in order:

        1. exact name,
        2. case-insensitive name (MariaDB's default collation is
           case-insensitive, so the database would resolve it),
        3. the Frappe **folder slug** of the name.

        The slug match matters: Frappe derives a DocType's folder from its
        name (``SPC Deviation`` -> ``spc_deviation``), and a Link field's
        ``options`` in real apps sometimes carries the slug rather than the
        name. Without it, ``amb_w_spc`` was reported as *not shipping*
        ``spc_deviation`` — a DocType it ships, at
        ``fda_compliance/doctype/spc_deviation/``.
        """
        exact = self.all_shipped_doctypes()
        if doctype in exact:
            return sorted(exact[doctype])
        lowered = doctype.lower()
        direct = {
            owner for name, owners in exact.items() if name.lower() == lowered for owner in owners
        }
        if direct:
            return sorted(direct)
        slug = scrub(doctype)
        if not slug:
            return []
        return sorted(
            {
                owner
                for name, owners in exact.items()
                if scrub(name) == slug
                for owner in owners
            }
        )

    def stats(self) -> dict[str, Any]:
        return {
            "apps_root": self.apps_root,
            "apps_scanned": len(self.apps),
            "app_names": [a.name for a in self.apps],
        }


def app_pair_key(record: dict[str, Any], kind: str) -> str:
    """Stable key for a Custom Field / Property Setter record.

    Custom Field: ``<dt>-<fieldname>``. Property Setter:
    ``<doc_type>-<field_name>-<property>``.
    """
    if kind == "custom_field":
        return f"{record.get('dt')}-{record.get('fieldname')}"
    return (
        f"{record.get('doc_type')}-{record.get('field_name')}-{record.get('property')}"
    )


def comparable_record(record: dict[str, Any], ignore: tuple[str, ...]) -> dict[str, Any]:
    """Record minus volatile keys (timestamps), so two copies can be compared."""
    return {k: v for k, v in record.items() if k not in ignore}
