import os
import json

def test_interactive_display():
    """Test what the interactive selection displays to users"""
    
    origin_app = "amb_w_spc"
    module = "sfc_manufacturing"
    
    print("🔍 TESTING INTERACTIVE SELECTION DISPLAY")
    print("=" * 50)
    
    # This simulates what happens in select_doctypes_interactive
    doctypes = ['sfc_operator', 'mrp_planning', 'mrp_work_order', 'sfc_operator_skill', 'tds_product_specification', 'sfc_transaction', 'container_barrels', 'batch_amb', 'sfc_operator_attendance', 'coa_amb', 'mrp_material_requirement', 'work_order_routing_operation', 'mrp_planning_item', 'tds_settings', 'tds_default_parameter', 'work_order_routing', 'batch_processing_history']
    
    print("What users see in interactive selection:")
    print("(Directory name → JSON name)")
    print("-" * 40)
    
    for i, doctype_dir in enumerate(doctypes, 1):
        json_file = f"/home/frappe/frappe-bench/apps/{origin_app}/{origin_app}/{module}/doctype/{doctype_dir}/{doctype_dir}.json"
        
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                data = json.load(f)
            json_name = data.get('name', 'NOT FOUND')
            
            # This is what users see
            if json_name != doctype_dir:
                print(f"{i:2d}. {doctype_dir} → {json_name}")
            else:
                print(f"{i:2d}. {doctype_dir} (no change)")
        else:
            print(f"{i:2d}. {doctype_dir} (JSON missing)")
    
    print()
    print("🎯 PROBLEM: Some JSON files have incorrect 'name' fields!")
    print("   - batch_amb should be 'Batch AMB' but is 'batch_amb'")
    print("   - container_barrels should be 'Container Barrels' but is 'container_barrels'")
    print("   - batch_processing_history should be 'Batch Processing History' but is 'batch_processing_history'")

test_interactive_display()
