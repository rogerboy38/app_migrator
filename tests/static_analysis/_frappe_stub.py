"""A permissive, bench-free stand-in for ``frappe``.

The integrity checks live outside ``app_migrator/commands/`` precisely so
they can be imported and tested with no Frappe installed. But the *package*
itself still imports ``frappe`` (through ``commands/analysis_tools.py``), so a
test that wants to prove the package still loads needs a stand-in.

This stub is deliberately permissive: unknown attributes resolve to a dummy
class, so it survives click decorators, ``except`` clauses and class
subclassing. It is **not** a Frappe emulator — it exists only to prove the
import graph is intact.
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
import types
from typing import Any

_STUB_ROOTS = ("frappe", "keyring")


class _StubMeta(type):
    """Permissive metaclass: dunder lookups fail, everything else is a stub."""

    def __getattr__(cls, item):
        if item.startswith("__"):
            raise AttributeError(item)
        return _make_stub_class(f"stub_{item}")

    def __delattr__(cls, item):
        pass


def _make_stub_class(name="stub"):
    def _init(self, *a, **k):
        pass

    def _call(self, *a, **k):
        return None

    def _getattr(self, item):
        if item.startswith("__"):
            raise AttributeError(item)
        return _make_stub_class(f"stub_{item}")

    return _StubMeta(
        name,
        (object,),
        {
            "__init__": _init,
            "__call__": _call,
            "__getattr__": _getattr,
            "__hash__": lambda self: id(self),
            "__eq__": lambda self, other: self is other,
        },
    )


class _StubModule(types.ModuleType):
    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        return _make_stub_class(f"stub_{attr}")


class _StubFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] not in _STUB_ROOTS:
            return None
        return importlib.machinery.ModuleSpec(fullname, self, is_package=True)

    def create_module(self, spec):
        module = _StubModule(spec.name)
        module.__path__ = []
        return module

    def exec_module(self, module):
        pass


def install() -> bool:
    """Install the stub. Returns False when a real frappe is already importable."""
    try:
        importlib.import_module("frappe")
        return False
    except ImportError:
        pass

    if any(isinstance(f, _StubFinder) for f in sys.meta_path):
        return True
    sys.meta_path.insert(0, _StubFinder())

    frappe = importlib.import_module("frappe")
    frappe._ = lambda s: s

    frappe.utils = importlib.import_module("frappe.utils")
    frappe.utils.cint = int
    frappe.utils.flt = float
    frappe.utils.cstr = str
    frappe.utils.now = lambda *a, **k: "2026-01-01 00:00:00"

    frappe.exceptions = importlib.import_module("frappe.exceptions")
    for exc_name in (
        "ValidationError",
        "DoesNotExistError",
        "PermissionError",
        "DoesNotExist",
        "MandatoryError",
        "DuplicateEntryError",
    ):
        setattr(frappe.exceptions, exc_name, type(exc_name, (Exception,), {}))

    import click

    frappe.commands = importlib.import_module("frappe.commands")
    frappe.commands.pass_context = click.pass_context
    frappe.commands.get_site = lambda *a, **k: None
    return True


def frappe_installed() -> Any:
    """The stubbed (or real) ``frappe`` module."""
    return importlib.import_module("frappe")
