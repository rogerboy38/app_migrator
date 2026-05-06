"""One-shot absorb helpers — production cleanup for the 5 stuck DocTypes.
Run via: bench execute app_migrator.commands._oneshot_absorb.<func>
"""
import frappe, json, shutil
from datetime import datetime
from pathlib import Path

INT_PROPS = {"in_list_view", "in_standard_filter", "reqd", "hidden",
             "read_only", "bold", "translatable", "no_copy",
             "print_hide", "report_hide", "allow_in_quick_entry"}


def _absorb(dt, json_path_str):
    JSON_PATH = Path(json_path_str)
    print("=" * 75)
    print(f"  ABSORB: {dt}")
    print("=" * 75)

    backup = JSON_PATH.with_suffix(
        JSON_PATH.suffix + datetime.now().strftime(".bak_%Y%m%d_%H%M%S")
    )
    shutil.copy2(JSON_PATH, backup)
    print(f"backup: {backup}")

    with open(JSON_PATH) as f:
        j = json.load(f)
    fields = j.get("fields", [])
    fields_by_name = {f.get("fieldname"): f for f in fields if "fieldname" in f}
    print(f"JSON before: custom={j.get('custom')}  fields={len(fields)}")

    ps_rows = frappe.db.sql(
        "SELECT name, doctype_or_field, field_name, property, value "
        "FROM `tabProperty Setter` WHERE doc_type=%s",
        dt, as_dict=True,
    )
    print(f"\nProcessing {len(ps_rows)} Property Setter row(s):")

    ps_to_delete = []
    for ps in ps_rows:
        raw_val = ps.value
        if ps.property in INT_PROPS:
            new_val = int(raw_val) if str(raw_val).isdigit() else 0
        else:
            new_val = raw_val

        target = None
        if ps.doctype_or_field == "DocField" and ps.field_name:
            target = fields_by_name.get(ps.field_name)

        if ps.doctype_or_field == "DocField" and not target:
            print(f"  ORPHAN    {ps.field_name}.{ps.property} (field gone)")
            ps_to_delete.append(ps.name)
            continue

        if target is not None:
            cur_val = target.get(ps.property)
            scope = ps.field_name
        else:
            cur_val = j.get(ps.property)
            scope = "(doctype)"

        redundant = (cur_val == new_val) or (cur_val in (None, 0) and new_val == 0)

        if redundant:
            print(f"  REDUNDANT {scope}.{ps.property}={new_val!r}")
        else:
            if target is not None:
                target[ps.property] = new_val
            else:
                j[ps.property] = new_val
            print(f"  ABSORB    {scope}.{ps.property}: {cur_val!r} -> {new_val!r}")
        ps_to_delete.append(ps.name)

    cf_rows = frappe.db.sql(
        "SELECT name, fieldname, label, fieldtype, options, insert_after, "
        "reqd, in_list_view, depends_on, fetch_from, `default`, "
        "description, hidden, read_only "
        "FROM `tabCustom Field` WHERE dt=%s",
        dt, as_dict=True,
    )
    print(f"\nProcessing {len(cf_rows)} Custom Field row(s):")

    cf_to_delete = []
    for cf in cf_rows:
        if cf.fieldname in fields_by_name:
            print(f"  REDUNDANT {cf.fieldname} already in JSON")
            cf_to_delete.append(cf.name)
            continue
        nf = {"fieldname": cf.fieldname, "label": cf.label, "fieldtype": cf.fieldtype}
        for k in ["options", "reqd", "in_list_view", "depends_on", "fetch_from",
                  "default", "description", "hidden", "read_only"]:
            v = cf.get(k)
            if v not in (None, "", 0):
                nf[k] = v
        idx = len(fields)
        if cf.insert_after:
            for i, ff in enumerate(fields):
                if ff.get("fieldname") == cf.insert_after:
                    idx = i + 1
                    break
        fields.insert(idx, nf)
        fields_by_name[cf.fieldname] = nf
        print(f"  ABSORB    {cf.fieldname} ({cf.fieldtype}) -> JSON fields[{idx}]")
        cf_to_delete.append(cf.name)

    j["fields"] = fields
    if j.get("custom") == 1:
        j["custom"] = 0
        print("\nJSON custom: 1 -> 0")
    for k in ["creation", "idx", "modified_by", "owner"]:
        j.pop(k, None)

    with open(JSON_PATH, "w") as f:
        json.dump(j, f, indent=1, sort_keys=False)
        f.write("\n")
    print(f"JSON written: {len(fields)} fields")

    for n in ps_to_delete:
        frappe.db.sql("DELETE FROM `tabProperty Setter` WHERE name=%s", n)
    for n in cf_to_delete:
        frappe.db.sql("DELETE FROM `tabCustom Field` WHERE name=%s", n)
    frappe.db.sql("UPDATE tabDocType SET custom=0 WHERE name=%s AND custom=1", dt)
    frappe.db.commit()
    frappe.clear_cache()

    print(f"\nCLEAR: deleted {len(ps_to_delete)} PS, {len(cf_to_delete)} CF")

    ps_left = frappe.db.count("Property Setter", {"doc_type": dt})
    cf_left = frappe.db.count("Custom Field", {"dt": dt})
    print(f"\nFinal: PS={ps_left}  CF={cf_left}")
    print("=" * 75)


def absorb_tds_product_spec():
    _absorb(
        "TDS Product Specification",
        "/home/frappe/frappe-bench/apps/amb_w_spc/amb_w_spc/sfc_manufacturing/doctype/tds_product_specification/tds_product_specification.json",
    )


def absorb_tds_settings():
    _absorb(
        "TDS Settings",
        "/home/frappe/frappe-bench/apps/amb_w_spc/amb_w_spc/sfc_manufacturing/doctype/tds_settings/tds_settings.json",
    )


def verify_all_5():
    from frappe.model.base_document import import_controller
    targets = [
        "Container Barrels",
        "Batch Processing History",
        "Plant Configuration",
        "TDS Product Specification",
        "TDS Settings",
        "Batch AMB",
    ]
    print("=" * 95)
    print(f"  {'DocType':30} {'cust':4} {'app':12} {'CF':3} {'PS':3} {'controller':30} {'status'}")
    print("=" * 95)
    rows_ok = 0
    for dt in targets:
        row = frappe.db.sql(
            "SELECT custom, app FROM tabDocType WHERE name=%s",
            dt, as_dict=True
        )
        if not row:
            print(f"  {dt:30} (NOT FOUND IN DB)")
            continue
        r = row[0]
        cf = frappe.db.count("Custom Field", {"dt": dt})
        ps = frappe.db.count("Property Setter", {"doc_type": dt})
        ctrl = import_controller(dt)
        is_proper = ctrl.__module__ != "frappe.model.document"
        is_ok = (r.custom == 0 and cf == 0 and ps == 0 and is_proper)
        if is_ok:
            rows_ok += 1
        status = "OK" if is_ok else "FIX"
        print(f"  {dt:30} {r.custom!s:4} {(r.app or '-'):12} {cf:>3} {ps:>3} "
              f"{ctrl.__name__:30} {status}")
    print("=" * 95)
    print(f"\n  {rows_ok}/{len(targets)} DocTypes pass all checks")


def absorb_batch_amb():
    _absorb(
        "Batch AMB",
        "/home/frappe/frappe-bench/apps/amb_w_spc/amb_w_spc/sfc_manufacturing/doctype/batch_amb/batch_amb.json",
    )


def cleanup_and_export():
    """Re-run absorbs for the 3 remaining drifted DocTypes, then export fixtures
    so the fixture files reflect the clean DB state."""
    import frappe
    from frappe.commands.utils import export_fixtures
    
    # Re-absorb for any DB drift that came back from fixtures
    _absorb(
        "TDS Product Specification",
        "/home/frappe/frappe-bench/apps/amb_w_spc/amb_w_spc/sfc_manufacturing/doctype/tds_product_specification/tds_product_specification.json",
    )
    _absorb(
        "TDS Settings",
        "/home/frappe/frappe-bench/apps/amb_w_spc/amb_w_spc/sfc_manufacturing/doctype/tds_settings/tds_settings.json",
    )
    _absorb(
        "Batch AMB",
        "/home/frappe/frappe-bench/apps/amb_w_spc/amb_w_spc/sfc_manufacturing/doctype/batch_amb/batch_amb.json",
    )
    print("\n" + "="*75)
    print("  All absorbs complete. Run bench export-fixtures next.")
    print("="*75)
