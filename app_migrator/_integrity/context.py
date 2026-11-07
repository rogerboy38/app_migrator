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
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

DEFAULT_APPS_ROOT = os.environ.get("BENCH_APPS_ROOT", "/home/frappe/frappe-bench/apps")

# Directories that never contain app source we want to reason about.
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "env", "dist", "build",
    ".eggs", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages",
}

# Fixture files we know how to read.
CUSTOM_FIELD_FIXTURE = "custom_field.json"
PROPERTY_SETTER_FIXTURE = "property_setter.json"


def iter_python_files(package_dir: str, skip_dirs: Optional[Set[str]] = None) -> Iterator[str]:
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


def parse_python(path: str) -> Optional[ast.Module]:
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


@dataclass
class HookInfo:
    """What an app's ``hooks.py`` declares.

    ``assignments`` maps a top-level name to its literal value when the value
    is a literal (e.g. ``required_apps = ["erpnext"]``), otherwise to ``None``
    with the raw AST node kept in ``nodes`` so checks can inspect it.
    """

    path: Optional[str]
    assignments: Dict[str, Any] = field(default_factory=dict)
    nodes: Dict[str, ast.AST] = field(default_factory=dict)
    parse_error: bool = False

    def get(self, name: str, default: Any = None) -> Any:
        value = self.assignments.get(name, default)
        return value

    def node(self, name: str) -> Optional[ast.AST]:
        return self.nodes.get(name)

    def literal_dict(self, name: str) -> Dict[str, Any]:
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
    _doctype_dirs_cache: Optional[List[str]] = field(default=None, repr=False)

    # -- DocTypes ---------------------------------------------------------
    def _doctype_dirs(self) -> List[str]:
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
        found: List[str] = []
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

    def doctype_json_paths(self) -> Dict[str, str]:
        """Map DocType name -> path of its ``.json`` definition.

        The DocType name comes from the JSON's ``name`` field when present
        (that is the name Frappe uses), falling back to the folder name.
        """
        found: Dict[str, str] = {}
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

    def fieldnames_for(self, doctype: str) -> Set[str]:
        """Field names available on ``doctype`` (standard fields + custom fields).

        Custom fields are the ones an app ships in ``fixtures/custom_field.json``
        for that doctype.
        """
        names: Set[str] = set()
        paths = self.doctype_json_paths()
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
        if path:
            data = read_json(path)
            if isinstance(data, dict):
                for fielddef in data.get("fields") or []:
                    if isinstance(fielddef, dict) and fielddef.get("fieldname"):
                        names.add(fielddef["fieldname"])
        for cf in self.custom_fields():
            if cf.get("dt") == doctype and cf.get("fieldname"):
                names.add(cf["fieldname"])
        return names

    # -- Fixtures ---------------------------------------------------------
    def fixture_path(self, filename: str) -> Optional[str]:
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

    def custom_fields(self) -> List[Dict[str, Any]]:
        """Custom Field records shipped by this app (may be empty)."""
        path = self.fixture_path(CUSTOM_FIELD_FIXTURE)
        if not path:
            return []
        data = read_json(path)
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []

    def property_setters(self) -> List[Dict[str, Any]]:
        """Property Setter records shipped by this app (may be empty)."""
        path = self.fixture_path(PROPERTY_SETTER_FIXTURE)
        if not path:
            return []
        data = read_json(path)
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []

    def required_apps(self) -> List[str]:
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
        app_names: Optional[List[str]] = None,
    ) -> None:
        self.apps_root = apps_root
        self.apps: List[AppInfo] = []
        self._by_name: Dict[str, AppInfo] = {}
        self._doctype_paths: Dict[str, Dict[str, str]] = {}
        self._load(app_names)

    # -- construction -----------------------------------------------------
    def _load(self, app_names: Optional[List[str]]) -> None:
        for name in (app_names if app_names is not None else self._iter_app_names()):
            app = self._build_app(name)
            if app is None:
                continue
            self.apps.append(app)
            self._by_name[name] = app

    def _iter_app_names(self) -> List[str]:
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

    def _build_app(self, name: str) -> Optional[AppInfo]:
        root = os.path.join(self.apps_root, name)
        if not os.path.isdir(root):
            return None
        package = os.path.join(root, name)
        if not os.path.isdir(package):
            package = root
        hooks = self._load_hooks(self._find_hooks_py(root, package))
        return AppInfo(name=name, root=root, package=package, hooks=hooks)

    @staticmethod
    def _find_hooks_py(root: str, package: str) -> Optional[str]:
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

    def _load_hooks(self, path: Optional[str]) -> HookInfo:
        if not path:
            return HookInfo(path=None)
        tree = parse_python(path)
        if tree is None:
            return HookInfo(path=path, parse_error=True)
        info = HookInfo(path=path)
        for node in tree.body:
            targets: List[str] = []
            value_node: Optional[ast.AST] = None
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
    def app(self, name: str) -> Optional[AppInfo]:
        return self._by_name.get(name)

    def doctype_paths(self, app_name: str) -> Dict[str, str]:
        cached = self._doctype_paths.get(app_name)
        if cached is None:
            app = self.app(app_name)
            cached = app.doctype_json_paths() if app else {}
            self._doctype_paths[app_name] = cached
        return cached

    def all_shipped_doctypes(self) -> Dict[str, Set[str]]:
        """DocType name -> set of apps that ship it."""
        shipped: Dict[str, Set[str]] = {}
        for app in self.apps:
            for dt in self.doctype_paths(app.name):
                shipped.setdefault(dt, set()).add(app.name)
        return shipped

    def app_for_doctype(self, doctype: str) -> List[str]:
        """Apps that ship a DocType with this name (case-insensitive match)."""
        exact = self.all_shipped_doctypes()
        if doctype in exact:
            return sorted(exact[doctype])
        lowered = doctype.lower()
        return sorted(
            {owner for name, owners in exact.items() if name.lower() == lowered for owner in owners}
        )

    def stats(self) -> Dict[str, Any]:
        return {
            "apps_root": self.apps_root,
            "apps_scanned": len(self.apps),
            "app_names": [a.name for a in self.apps],
        }


def app_pair_key(record: Dict[str, Any], kind: str) -> str:
    """Stable key for a Custom Field / Property Setter record.

    Custom Field: ``<dt>-<fieldname>``. Property Setter:
    ``<doc_type>-<field_name>-<property>``.
    """
    if kind == "custom_field":
        return f"{record.get('dt')}-{record.get('fieldname')}"
    return (
        f"{record.get('doc_type')}-{record.get('field_name')}-{record.get('property')}"
    )


def comparable_record(record: Dict[str, Any], ignore: Tuple[str, ...]) -> Dict[str, Any]:
    """Record minus volatile keys (timestamps), so two copies can be compared."""
    return {k: v for k, v in record.items() if k not in ignore}
