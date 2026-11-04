"""DB-free, bench-free tests (frappe/keyring stubbed). Run: python -m unittest discover -s tests -p 'test_*.py'

Guards two regressions found in the v10.0.0-rc1 review:
  1. app_migrator.commands must import - a missing optional module used to abort the whole package
     (and with it every `bench app-migrator` command).
  2. Generated DocType controllers must use Frappe's class name ("TDS Settings" -> TDSSettings),
     not title-cased words (TdsSettings) - the exact bug orphan scenario 01 describes.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

import click  # imported before the stubs so patch.dict does not discard/reload it

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _stubs():
	fc = mock.MagicMock()
	fc.pass_context = lambda f: f
	mods = {n: mock.MagicMock() for n in ("frappe", "frappe.utils", "frappe.model", "frappe.model.document",
	                                       "frappe.database", "keyring")}
	mods["frappe.commands"] = fc
	return mods


def _load_commands():
	for name in [m for m in sys.modules if m == "app_migrator" or m.startswith("app_migrator.")]:
		del sys.modules[name]
	sys.path.insert(0, ROOT)
	try:
		with mock.patch.dict(sys.modules, _stubs()):
			import app_migrator.commands as c
			from app_migrator.commands import _naming, ensure_controllers
			return c, _naming, ensure_controllers
	finally:
		sys.path.remove(ROOT)


class TestPackageLoads(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.c, cls.naming, cls.ensure = _load_commands()

	def test_package_imports_and_registers_commands(self):
		self.assertGreaterEqual(len(self.c.app_migrator.commands), 40)
		for name in ("orphans", "scan", "plan", "execute", "stage", "unstage", "health", "git-push"):
			self.assertIn(name, self.c.app_migrator.commands)
		self.assertTrue(all(isinstance(x, click.Command) for x in self.c.commands))

	def test_missing_audit_module_is_tolerated(self):
		if os.path.exists(os.path.join(ROOT, "app_migrator", "commands", "audit_app_for_antipattern.py")):
			self.skipTest("audit module is present")
		self.assertIsNone(self.c.app_migrator_audit_app_for_antipattern)
		self.assertNotIn(None, self.c.commands)


class TestControllerClassName(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		_, cls.naming, cls.ensure = _load_commands()

	def test_frappe_convention(self):
		f = self.naming.controller_class_name
		self.assertEqual(f("TDS Settings"), "TDSSettings")
		self.assertEqual(f("COA AMB2"), "COAAMB2")
		self.assertEqual(f("KPI Factors"), "KPIFactors")
		self.assertEqual(f("Stock Entry Approval Rule"), "StockEntryApprovalRule")
		self.assertEqual(f("Sales-Order Item"), "SalesOrderItem")

	def test_name_from_json_with_fallback(self):
		with tempfile.TemporaryDirectory() as d:
			p = os.path.join(d, "x.json")
			with open(p, "w") as fh:
				json.dump({"name": "TDS Settings"}, fh)
			self.assertEqual(self.naming.doctype_name_from_json(p, "tds_settings"), "TDS Settings")
			self.assertEqual(self.naming.doctype_name_from_json(os.path.join(d, "none.json"), "third_party_api"),
			                 "Third Party Api")

	def test_ensure_controllers_writes_the_class_frappe_expects(self):
		with tempfile.TemporaryDirectory() as bench:
			dt = os.path.join(bench, "apps", "myapp", "myapp", "mymod", "doctype", "tds_settings")
			os.makedirs(dt)
			with open(os.path.join(dt, "tds_settings.json"), "w") as fh:
				json.dump({"doctype": "DocType", "name": "TDS Settings"}, fh)
			with mock.patch.object(self.ensure, "find_bench_root", return_value=bench):
				dry = self.ensure.ensure_controller_files("myapp", dry_run=True)
				self.assertFalse(os.path.exists(os.path.join(dt, "tds_settings.py")))
				made = self.ensure.ensure_controller_files("myapp", dry_run=False)
			self.assertEqual(len(dry), 1)
			self.assertEqual(len(made), 1)
			with open(os.path.join(dt, "tds_settings.py")) as fh:
				src = fh.read()
			self.assertIn("class TDSSettings(Document):", src)
			self.assertNotIn("TdsSettings", src)

	def test_orphans_uses_the_shared_helper(self):
		with open(os.path.join(ROOT, "app_migrator", "commands", "orphans.py")) as fh:
			src = fh.read()
		self.assertIn("controller_class_name(dt_name)", src)
		self.assertNotIn("word.capitalize()", src)


if __name__ == "__main__":
	unittest.main()
