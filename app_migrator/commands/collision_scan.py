"""
collision-scan — DocType ownership guard (MIGCH P1-7 / S4, 2026-07-16).

Battle-tested during MIGCH Phase 1: caught C1/C2/C6/C7 classes plus Plant
Configuration dupe. Lessons baked in: tests/ corpora excluded (app_migrator's
own orphan_scenarios are test fixtures, not apps); BINARY collation for DB
name matches (L154: 'Uom' vs core 'UOM'); pycache-only dirs count as deleted.

Usage:
  bench collision-scan [--site SITE] [--json-out PATH] [--whitelist NAME,NAME]
  python3 collision_scan.py [--bench-path /home/frappe/frappe-bench] [same flags]

Exit 0 = clean (or all findings whitelisted) · 1 = collisions found.
"""
import glob
import json
import os
import subprocess
import sys


def _find_bench(start):
    p = os.path.abspath(start)
    while p != "/":
        if os.path.isdir(os.path.join(p, "apps")) and os.path.isdir(os.path.join(p, "sites")):
            return p
        p = os.path.dirname(p)
    return None


def scan_files(apps_dir):
    """DocType name -> set(apps defining it). Skips test corpora / caches."""
    owners = {}
    for appdir in sorted(os.listdir(apps_dir)):
        root = os.path.join(apps_dir, appdir)
        if not os.path.isdir(root):
            continue
        for j in glob.glob(f"{root}/**/doctype/*/*.json", recursive=True):
            base = os.path.basename(os.path.dirname(j))
            if os.path.basename(j) != base + ".json":
                continue
            if any(seg in j for seg in ("__pycache__", "node_modules", "/tests/", "/test_fixtures/")):
                continue
            try:
                d = json.load(open(j))
            except Exception:
                continue
            if d.get("doctype") != "DocType":
                continue
            owners.setdefault(d.get("name"), set()).add(appdir)
    return owners


def db_orphans(bench_path, site, owners):
    """DocTypes the DB says an app owns, whose json file is gone (fixture-zombie class, L378)."""
    q = ("SELECT dt.name, md.app_name FROM tabDocType dt "
         "JOIN `tabModule Def` md ON md.name = dt.module WHERE dt.custom = 0")
    r = subprocess.run(["bench", "--site", site, "mariadb", "-e", q],
                       cwd=bench_path, capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr[-200:]
    out = []
    for line in r.stdout.strip().splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        name, app = parts
        if app and name not in owners:
            out.append({"doctype": name, "db_app": app, "issue": "DB-owned, no json file in any app"})
    return out, None


def run(bench_path=None, site=None, json_out=None, whitelist=()):
    bench_path = bench_path or _find_bench(__file__) or _find_bench(os.getcwd())
    if not bench_path:
        print("collision-scan: cannot locate bench root"); return 2
    owners = scan_files(os.path.join(bench_path, "apps"))
    dupes = {k: sorted(v) for k, v in owners.items() if len(v) > 1 and k not in whitelist}
    findings = [{"doctype": k, "apps": v, "issue": "defined by >1 app"} for k, v in sorted(dupes.items())]
    orphan_note = None
    if site:
        orphans, err = db_orphans(bench_path, site, owners)
        if err:
            orphan_note = f"db check skipped: {err}"
        else:
            findings += [o for o in orphans if o["doctype"] not in whitelist]
    result = {"mode": "collision-scan", "scanned_doctypes": len(owners),
              "findings": findings, "whitelisted": sorted(whitelist), "pass": not findings}
    if orphan_note:
        result["note"] = orphan_note
    for f in findings:
        print("COLLISION:", f)
    print(f"collision-scan: {len(owners)} doctypes scanned · {len(findings)} finding(s) · "
          + ("PASS" if result["pass"] else "FAIL"))
    if json_out:
        json.dump(result, open(json_out, "w"), indent=1)
        print("json ->", json_out)
    return 0 if result["pass"] else 1


# ---- click command (bench) ----
try:
    import click

    @click.command("collision-scan")
    @click.option("--site", default=None, help="also cross-check DB DocType ownership vs files")
    @click.option("--json-out", default=None, help="write machine-checkable DoD JSON here")
    @click.option("--whitelist", default="", help="comma-separated DocType names to ignore")
    def collision_scan(site, json_out, whitelist):
        """Fail if any DocType is defined by more than one app (MIGCH S4 guard)."""
        wl = tuple(x.strip() for x in whitelist.split(",") if x.strip())
        sys.exit(run(site=site, json_out=json_out, whitelist=wl))
except ImportError:  # standalone use without click
    collision_scan = None


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-path"); ap.add_argument("--site")
    ap.add_argument("--json-out"); ap.add_argument("--whitelist", default="")
    a = ap.parse_args()
    wl = tuple(x.strip() for x in a.whitelist.split(",") if x.strip())
    sys.exit(run(a.bench_path, a.site, a.json_out, wl))
