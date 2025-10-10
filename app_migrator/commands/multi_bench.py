"""
🏗️ Multi-Bench Management - Cross-Bench Operations
"""

import os
import subprocess
from pathlib import Path

def compare_benches(bench1, bench2):
    """Compare two benches and show differences"""
    print(f"🔀 COMPARING BENCHES: {bench1} vs {bench2}")
    
    apps1 = get_bench_apps_simple(bench1)
    apps2 = get_bench_apps_simple(bench2)
    
    common = set(apps1) & set(apps2)
    unique1 = set(apps1) - set(apps2)
    unique2 = set(apps2) - set(apps1)
    
    print(f"📊 COMPARISON RESULTS:")
    print(f"   ✅ Common apps: {len(common)}")
    print(f"   📦 Unique to {bench1}: {len(unique1)}")
    print(f"   📦 Unique to {bench2}: {len(unique2)}")
    
    if unique1:
        print(f"\n🎯 Migration targets ({bench1} → {bench2}):")
        for app in sorted(unique1):
            print(f"   • {app}")
    
    return {
        "common": common,
        "unique1": unique1,
        "unique2": unique2
    }

def get_bench_apps_simple(bench_path):
    """Simple bench apps getter without complex output"""
    try:
        result = subprocess.run(
            f"cd {bench_path} && bench version",
            shell=True, capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().split('\n')
        apps = []
        for line in lines:
            if ' ' in line and not line.startswith('✅'):
                app = line.split()[0]
                apps.append(app)
        return sorted(apps)
    except:
        return []

def bench_health_check():
    """Perform health check on all benches"""
    print("🏥 BENCH HEALTH CHECK")
    benches = detect_available_benches_simple()
    
    for bench in benches:
        bench_path = f"/home/frappe/{bench}"
        size = get_bench_size_simple(bench_path)
        apps = get_bench_apps_simple(bench_path)
        
        print(f"\n📦 {bench}:")
        print(f"   📊 Size: {size}")
        print(f"   🎯 Apps: {len(apps)}")
        print(f"   ✅ Status: Healthy" if apps else "   ⚠️ Status: Empty")

def detect_available_benches_simple():
    """Simple bench detection"""
    benches = []
    frappe_home = os.path.expanduser('~')
    for item in os.listdir(frappe_home):
        if item.startswith('frappe-bench') and os.path.isdir(os.path.join(frappe_home, item)):
            benches.append(item)
    return sorted(benches)

def get_bench_size_simple(bench_path):
    """Simple size getter"""
    try:
        result = subprocess.run(f"du -sh {bench_path}", shell=True, capture_output=True, text=True)
        return result.stdout.strip().split()[0]
    except:
        return "unknown"

