"""Check: whitelisted endpoints that bypass Frappe's permission model.

Why this check exists
---------------------
Audited evidence (both audits, 2026-11-05):

- ``amb_w_tds`` publishes ``cleanup_test_data`` — a whitelisted endpoint that
  deletes rows — plus two FoxPro migration helpers, also whitelisted. A
  migration helper reachable over HTTP is no longer a migration helper.
- Neither ``amb_w_tds`` nor ``rnd_warehouse_management`` shipped a single
  ``allow_guest=True`` endpoint, so a guest endpoint is a defect rather
  than a house style. ``amb_w_spc`` ships two: ``receive_weight_event``
  (guest-writable — a real defect) and ``bot_authenticate`` (a **login**
  endpoint, where guest access is the point).

Guest access is not the same thing as a permission bypass
-------------------------------------------------------
An endpoint that both accepts guests and hands out a credential is an
**authentication** endpoint. Calling it "a guest permission bypass" says
something false: establishing the session is its job. It is still reported
— a credential-minting endpoint that anyone can reach is exactly what a
human should look at — but under its own framing, and at ``medium``: the
question is not "why is there no permission check" but "is the credential
check sound".

Why it matters
--------------
``@frappe.whitelist()`` publishes a plain Python function as an HTTP endpoint.
Frappe's permission model guards *document* operations; raw SQL and
``frappe.get_all`` walk straight past it. A whitelisted function that reads or
writes without a permission guard of its own is therefore callable by any
logged-in user — and by anyone at all when ``allow_guest=True``.

What is reported
----------------
One finding per endpoint that is whitelisted, reaches the database through a
permission-bypassing API and carries no guard of its own. Write-capable
endpoints are ``high``; read-only ones are ``medium``. A whitelisted function
defined in a test or migration module is always ``high``, because such a
function is reachable over HTTP whether or not it touches the database. A
guest endpoint that returns a credential is reported as an authentication
endpoint at ``medium``.

The check is a pure AST + filesystem read: it never imports ``frappe`` and
never touches a bench, a database or the network.
"""
from __future__ import annotations

import ast
import os
import re
from collections.abc import Iterator
from typing import Any

from ..base import CheckResult, CheckSpec, Finding
from ..context import Inventory, iter_python_files, parse_python, read_text

CHECK_ID = "endpoint-permission-gap"

# --------------------------------------------------------------------------
# The bypass surface
# --------------------------------------------------------------------------
SQL_API = "frappe.db.sql"
GET_ALL_API = "frappe.get_all"
GET_VALUE_API = "frappe.db.get_value"
SET_VALUE_API = "frappe.db.set_value"
DELETE_API = "frappe.db.delete"
COMMIT_API = "frappe.db.commit"

#: APIs that reach the database without passing Frappe's permission model.
BYPASS_APIS = frozenset({SQL_API, GET_ALL_API, GET_VALUE_API, SET_VALUE_API, DELETE_API})

#: Bypass APIs that can change data on their own.
WRITE_APIS = frozenset({SET_VALUE_API, DELETE_API})

#: Document methods that skip permissions only when they are told to.
IGNORE_PERMISSION_METHODS = frozenset({"save", "insert", "delete"})

#: Any of these tokens in a function body counts as a permission guard.
GUARD_TOKENS = (
    "has_permission",
    "check_permission",
    "only_for",
    "has_role",
    "get_roles",
    "permissionerror",
    "roles",
)

#: Keys that mark a returned dict as handing out a credential. A guest
#: endpoint that returns one of these is an **authentication** endpoint, not
#: a permission bypass: it is supposed to be reachable without a session,
#: because establishing the session is its job.
CREDENTIAL_KEYS = frozenset({
    "access_token",
    "api_key",
    "api_token",
    "auth_token",
    "id_token",
    "jwt",
    "refresh_token",
    "secret",
    "session_token",
    "token",
})

#: SQL leading keywords that mean "this statement changes data".
WRITE_SQL_KEYWORDS = frozenset({
    "insert", "update", "delete", "replace", "create", "drop",
    "alter", "truncate", "rename", "grant", "revoke",
})


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _slug(text: str) -> str:
    """Kebab-case slug, used to build stable finding ids."""
    slug = re.sub(r"[^0-9a-zA-Z]+", "-", str(text)).strip("-").lower()
    return slug or "unknown"


def _rel_path(app: Any, path: str) -> str:
    """Path of ``path`` relative to the app's Python package, posix style."""
    rel = os.path.relpath(path, app.package)
    return rel.replace(os.sep, "/")


def _module_kind(rel_path: str) -> str:
    """Classify a module path as ``test_or_migration`` or ``application``.

    A path is a test/migration module when it contains ``migrations``, when a
    directory segment is ``test`` / ``tests``, or when the file name starts
    with ``test_`` (or ends with ``_test.py``).
    """
    parts = [p for p in rel_path.split("/") if p]
    lowered = [p.lower() for p in parts]
    if "migrations" in rel_path.lower():
        return "test_or_migration"
    if any(segment in ("test", "tests") for segment in lowered):
        return "test_or_migration"
    filename = lowered[-1] if lowered else ""
    if filename.startswith("test_") or filename.endswith("_test.py"):
        return "test_or_migration"
    return "application"


def _literal_str(node: ast.AST) -> str | None:
    """Return the string value of a literal node, else ``None``."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


# --------------------------------------------------------------------------
# Import resolution
# --------------------------------------------------------------------------
class _Resolver:
    """Resolve a call target to the canonical ``frappe`` dotted path it names.

    The resolver understands the import styles Frappe apps actually use:

    - ``import frappe``            -> ``frappe.db.sql``
    - ``from frappe import db``    -> ``db.sql``
    - ``from frappe import get_all`` -> ``get_all(...)``
    - ``db = frappe.db``           -> ``db.sql``

    Anything it cannot resolve returns ``None`` — the call is then only
    recognised through its method name (``save`` / ``insert`` / ``delete``).
    """

    def __init__(self, tree: ast.Module) -> None:
        self.aliases: dict[str, str] = {}
        self.constants: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    self.aliases[alias.asname or root] = root
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] == "frappe":
                    for alias in node.names:
                        self.aliases[alias.asname or alias.name] = f"frappe.{alias.name}"
        # Second pass: module-level aliases of an already resolved object.
        for node in tree.body:
            if isinstance(node, ast.Assign):
                target_paths = self.resolve(node.value)
                literal = _literal_str(node.value)
                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if target_paths:
                        self.aliases[target.id] = target_paths
                    elif literal is not None:
                        self.constants[target.id] = literal

    def resolve(self, node: ast.AST) -> str | None:
        """Canonical dotted path of ``node``, or ``None`` when unknown."""
        if isinstance(node, ast.Name):
            if node.id in self.aliases:
                return self.aliases[node.id]
            if node.id == "frappe":
                # ``frappe`` is always the frappe package, even when the
                # module forgot to import it.
                return "frappe"
            return None
        if isinstance(node, ast.Attribute):
            base = self.resolve(node.value)
            if base is None:
                return None
            return f"{base}.{node.attr}"
        return None


# --------------------------------------------------------------------------
# AST walking
# --------------------------------------------------------------------------
def _iter_scope_nodes(stmts: list[ast.stmt]) -> Iterator[ast.AST]:
    """Yield every node of ``stmts`` without descending into nested scopes.

    A nested ``def`` / ``class`` gets its own analysis; attributing its calls
    to the enclosing endpoint as well would double-count the same bypass.
    """
    stack: list[ast.AST] = list(stmts)
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _iter_functions(tree: ast.Module) -> Iterator[tuple[str, ast.AST]]:
    """Yield ``(qualified_name, function_node)`` for every function."""
    stack: list[tuple[list[ast.stmt], str]] = [(tree.body, "")]
    while stack:
        stmts, prefix = stack.pop()
        for node in reversed(stmts):
            if isinstance(node, ast.ClassDef):
                stack.append((node.body, f"{prefix}{node.name}."))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = f"{prefix}{node.name}"
                yield qual, node
                stack.append((node.body, f"{qual}."))
    return


# --------------------------------------------------------------------------
# Endpoint analysis
# --------------------------------------------------------------------------
def _decorator_target(decorator: ast.AST) -> ast.AST:
    """The decorated object of a decorator (``Call`` -> its function)."""
    if isinstance(decorator, ast.Call):
        return decorator.func
    return decorator


def _decorator_text(decorator: ast.AST) -> str:
    """Best-effort source text of a decorator."""
    try:
        return ast.unparse(decorator)
    except Exception:  # pragma: no cover - defensive
        return ""


def _is_whitelist_decorator(decorator: ast.AST, resolver: _Resolver) -> bool:
    """True when the decorator marks the function as an HTTP endpoint."""
    target = _decorator_target(decorator)
    canonical = resolver.resolve(target)
    if canonical and canonical.rsplit(".", 1)[-1] == "whitelist":
        return True
    if isinstance(target, ast.Name) and target.id == "whitelist":
        return True
    return "frappe.whitelist" in _decorator_text(decorator)


def _allow_guest(decorator: ast.AST) -> bool:
    """True when the whitelist decorator asks for guest access."""
    if not isinstance(decorator, ast.Call):
        return False
    for keyword in decorator.keywords:
        if keyword.arg == "allow_guest":
            return isinstance(keyword.value, ast.Constant) and bool(keyword.value.value)
    if decorator.args:
        first = decorator.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, bool):
            return first.value
    return False


def _static_text(node: ast.AST, resolver: _Resolver) -> str | None:
    """Recover the static text of an expression, as far as possible.

    Literals, f-string prefixes, string concatenations and module-level
    string constants resolve; anything else returns ``None`` ("unknown").
    """
    literal = _literal_str(node)
    if literal is not None:
        return literal
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            text = _literal_str(value)
            parts.append(text if text is not None else " ")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_text(node.left, resolver)
        right = _static_text(node.right, resolver)
        if left is not None and right is not None:
            return left + right
        return left if left is not None else right
    if isinstance(node, ast.Name):
        return resolver.constants.get(node.id)
    return None


def _sql_verdict(call: ast.Call, resolver: _Resolver) -> bool | None:
    """``True`` for writing SQL, ``False`` for reading SQL, ``None`` unknown."""
    if not call.args:
        return None
    text = _static_text(call.args[0], resolver)
    if text is None:
        return None
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        return None
    head = words[0]
    if head in WRITE_SQL_KEYWORDS:
        return True
    if head in ("select", "show", "pragma", "explain", "desc", "describe"):
        return False
    if head == "with":
        for word in words:
            if word in WRITE_SQL_KEYWORDS:
                return True
        return False
    return None


def _has_ignore_permissions(call: ast.Call) -> bool:
    """True when the call passes ``ignore_permissions=True``."""
    for keyword in call.keywords:
        if keyword.arg == "ignore_permissions":
            return isinstance(keyword.value, ast.Constant) and bool(keyword.value.value)
    return False


def _collect_apis(func: ast.AST, resolver: _Resolver) -> tuple[set[str], bool]:
    """Return ``(bypass_apis, write_capable)`` for one function.

    ``frappe.db.commit`` only counts as a bypass when the function also
    writes — a commit on its own proves nothing.
    """
    apis: set[str] = set()
    write_capable = False
    has_commit = False
    for node in _iter_scope_nodes(func.body):
        if not isinstance(node, ast.Call):
            continue
        canonical = resolver.resolve(node.func)
        if canonical == COMMIT_API:
            has_commit = True
            continue
        if canonical in BYPASS_APIS:
            apis.add(canonical)
            if canonical in WRITE_APIS:
                write_capable = True
            elif canonical == SQL_API:
                # Unknown SQL is treated as write-capable: an unguarded
                # endpoint running arbitrary SQL is the worst case.
                if _sql_verdict(node, resolver) is not False:
                    write_capable = True
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in IGNORE_PERMISSION_METHODS:
            if _has_ignore_permissions(node):
                apis.add(f"{node.func.attr}(ignore_permissions=True)")
                write_capable = True
    if has_commit and write_capable:
        apis.add(COMMIT_API)
    return apis, write_capable


def _has_guard(func: ast.AST) -> bool:
    """True when the function body mentions a permission guard."""
    for node in _iter_scope_nodes(func.body):
        if isinstance(node, ast.Name):
            ident = node.id
        elif isinstance(node, ast.Attribute):
            ident = node.attr
        else:
            continue
        lowered = ident.lower()
        if any(token in lowered for token in GUARD_TOKENS):
            return True
    return False


def _issues_credential(func: ast.AST) -> bool:
    """True when the function returns a dict that carries a credential.

    A ``return {"session_token": ...}`` (or any other credential-bearing key)
    is what makes a guest endpoint an authentication endpoint rather than a
    permission bypass. The key set is explicit on purpose: a heuristic on the
    function name alone would misclassify an endpoint that merely *mentions*
    "auth" in its name.
    """
    for node in ast.walk(func):
        if not isinstance(node, ast.Dict):
            continue
        for key in node.keys:
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and key.value.strip().lower() in CREDENTIAL_KEYS
            ):
                return True
    return False


def _finding_id(app_name: str, rel_path: str, qualname: str) -> str:
    """Stable finding id: no line numbers, so ids survive line shifts."""
    stem = os.path.splitext(rel_path)[0]
    file_slug = _slug(f"{app_name}/{stem}")
    return f"integrity-{CHECK_ID}-{file_slug}-{_slug(qualname)}"


# --------------------------------------------------------------------------
# Check
# --------------------------------------------------------------------------
def scan_endpoints(inventory: Inventory) -> dict[str, Any]:
    """Scan every app for whitelisted endpoints that bypass permissions.

    Returns a dict with an ``endpoints`` map of finding id -> endpoint facts,
    plus scan counters under ``_stats``.
    """
    endpoints: dict[str, Any] = {}
    stats: dict[str, Any] = {
        "apps_scanned": len(inventory.apps),
        "files_scanned": 0,
        "parse_errors": 0,
        "empty_files": 0,
        "functions_scanned": 0,
        "whitelisted_endpoints": 0,
        "guest_endpoints": 0,
        "unprotected_endpoints": 0,
    }
    for app in inventory.apps:
        for path in iter_python_files(app.package):
            stats["files_scanned"] += 1
            tree = parse_python(path)
            if tree is None:
                # An empty file has no code to parse; that is not a parse
                # error. Counting the 200+ empty ``__init__.py`` files of a
                # real bench as "parse errors" would overstate the breakage
                # and hide the genuine failures.
                if read_text(path).strip():
                    stats["parse_errors"] += 1
                else:
                    stats["empty_files"] += 1
                continue
            resolver = _Resolver(tree)
            rel = _rel_path(app, path)
            module_kind = _module_kind(rel)
            for qualname, func in _iter_functions(tree):
                stats["functions_scanned"] += 1
                whitelist_decorators = [
                    decorator
                    for decorator in func.decorator_list
                    if _is_whitelist_decorator(decorator, resolver)
                ]
                if not whitelist_decorators:
                    continue
                stats["whitelisted_endpoints"] += 1
                allow_guest = any(_allow_guest(d) for d in whitelist_decorators)
                if allow_guest:
                    stats["guest_endpoints"] += 1
                apis, write_capable = _collect_apis(func, resolver)
                guarded = _has_guard(func)
                in_test_module = module_kind == "test_or_migration"
                if not in_test_module and (not apis or guarded):
                    continue
                finding_id = _finding_id(app.name, rel, qualname)
                endpoints[finding_id] = {
                    "app": app.name,
                    "file": rel,
                    "line": func.lineno,
                    "function": qualname,
                    "apis": sorted(apis),
                    "write_capable": write_capable,
                    "module_kind": module_kind,
                    "allow_guest": allow_guest,
                    "is_auth_endpoint": allow_guest and _issues_credential(func),
                }
    stats["unprotected_endpoints"] = len(endpoints)
    return {"endpoints": endpoints, "_stats": stats}


def build_findings(scan: dict[str, Any]) -> list[Finding]:
    """Turn the endpoint scan into envelope findings."""
    findings: list[Finding] = []
    for finding_id in sorted(scan.get("endpoints", {})):
        info = scan["endpoints"][finding_id]
        function = info["function"]
        apis = info["apis"]
        in_test_module = info["module_kind"] == "test_or_migration"
        is_auth_endpoint = bool(info.get("is_auth_endpoint"))
        severity = "high" if (info["write_capable"] or in_test_module) else "medium"

        prefix = "GUEST-accessible " if info["allow_guest"] else ""
        if is_auth_endpoint:
            # A login endpoint is *supposed* to be reachable without a
            # session: establishing the session is its job. Reporting it as
            # a permission bypass says something false. It is still reported
            # — a guest credential-minting endpoint is exactly what a human
            # needs to look at — but with the right framing and severity.
            severity = "medium"
            title = f"{prefix}Authentication endpoint '{function}' is reachable without a session"
            detail = (
                f"'{function}' is published as an HTTP endpoint with allow_guest=True and "
                f"returns a credential. Guest access is expected for an authentication "
                f"endpoint, so this is not a permission bypass — but it is reachable by "
                f"anyone at all, with no session. The review focus is the credential "
                f"check itself: how the presented key is compared, whether repeated "
                f"attempts are rate-limited, and what an unauthenticated caller learns "
                f"from the response."
            )
        elif in_test_module:
            severity = "high"
            title = f"{prefix}Whitelisted endpoint '{function}' lives in a test/migration module"
            detail = (
                f"'{function}' is published as an HTTP endpoint via @frappe.whitelist() but "
                f"is defined in a test or migration module ({info['file']}). Such a "
                "function is reachable over HTTP even when it is only meant to run "
                "inside a test run or a migration."
            )
            if info["allow_guest"]:
                detail += (
                    " The decorator asks for allow_guest=True, so the endpoint needs no "
                    "session at all — it is reachable by anyone."
                )
        else:
            severity = "high" if info["write_capable"] else "medium"
            caller = (
                "anyone at all — no session is required"
                if info["allow_guest"]
                else "any logged-in user"
            )
            title = f"{prefix}Whitelisted endpoint '{function}' bypasses the permission model"
            detail = (
                f"'{function}' is published as an HTTP endpoint via @frappe.whitelist() and "
                f"reaches the database through {', '.join(apis)} without a permission guard "
                f"of its own, so {caller} can call it."
            )
        findings.append(
            Finding(
                id=finding_id,
                title=title,
                severity=severity,
                description=detail,
                app=info["app"],
                evidence={
                    "file": info["file"],
                    "line": info["line"],
                    "function": function,
                    "apis": apis,
                    "write_capable": info["write_capable"],
                    "module_kind": info["module_kind"],
                    "allow_guest": info["allow_guest"],
                    "is_auth_endpoint": is_auth_endpoint,
                },
            )
        )
    return findings


def check_endpoint_permission_gap(inventory: Inventory) -> CheckResult:
    """Check entry point."""
    scan = scan_endpoints(inventory)
    return CheckResult(
        check_id=CHECK_ID,
        findings=build_findings(scan),
        stats=scan["_stats"],
    )


CHECK_SPEC = CheckSpec(
    check_id=CHECK_ID,
    title="Whitelisted endpoint without a permission guard",
    description=(
        "Detect @frappe.whitelist() endpoints that reach the database through "
        "frappe.db.sql / frappe.get_all / document writes without a permission "
        "guard of their own, plus whitelisted endpoints shipped in test or "
        "migration modules."
    ),
    fn=check_endpoint_permission_gap,
)
