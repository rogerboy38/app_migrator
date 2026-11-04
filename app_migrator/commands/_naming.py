"""Pure naming helpers (no frappe import, unit-testable without a bench)."""

import json
import os


def controller_class_name(doctype_name):
    """The controller class Frappe looks for in a DocType's module.

    Frappe derives it from the DocType *name* by dropping spaces and hyphens, preserving case:
    "TDS Settings" -> "TDSSettings". Title-casing each word ("TdsSettings") produces a class
    Frappe cannot find for any DocType with an acronym in its name.
    """
    return doctype_name.replace(" ", "").replace("-", "")


def doctype_name_from_json(json_path, fallback_folder_name):
    """The real DocType name from its .json (`name`), else a best-effort title-case of the folder name."""
    try:
        with open(json_path, encoding="utf-8") as f:
            name = json.load(f).get("name")
        if name:
            return name
    except (OSError, ValueError, AttributeError):
        pass
    return " ".join(w.capitalize() for w in os.path.basename(fallback_folder_name).split("_"))
