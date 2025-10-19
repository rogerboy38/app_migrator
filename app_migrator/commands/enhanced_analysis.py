"""
Enhanced Analysis Tools with Modern App Structure Support
"""

import os
from typing import Dict, Any
from .pre_installation_diagnostics import PreInstallationAnalyzer

def analyze_app_comprehensive_modern(source_app: str, detailed: bool = False) -> Dict[str, Any]:
    """
    Enhanced comprehensive analysis with modern app structure support
    """
    print(f"🔍 ENHANCED COMPREHENSIVE ANALYSIS: {source_app}")
    print("=" * 70)
    
    # Use our modern pre-installation analyzer
    analyzer = PreInstallationAnalyzer()
    health_analysis = analyzer.analyze_app_health(source_app)
    
    # Extract modern structure info
    module_registration = health_analysis.get("module_registration", {})
    modern_structure = module_registration.get("modern_structure_detected", False)
    modern_modules = module_registration.get("modern_modules_detected", [])
    app_metadata = module_registration.get("app_metadata", {})
    
    # Build enhanced analysis result
    analysis_result = {
        "source_app": source_app,
        "modern_structure_detected": modern_structure,
        "modules_detected": len(modern_modules),
        "module_list": modern_modules,
        "app_metadata": app_metadata,
        "health_score": health_analysis.get("health_score", 0),
        "structure_validation": health_analysis.get("structure_validation", {}),
        "installation_blockers": health_analysis.get("installation_blockers", []),
        "dependencies": app_metadata.get("dependencies", [])
    }
    
    # Display results
    print(f"\n📦 MODULES IN {source_app}: {len(modern_modules)}")
    if modern_modules and detailed:
        for module in modern_modules[:10]:  # Show first 10 modules
            print(f"  • {module}")
        if len(modern_modules) > 10:
            print(f"  ... and {len(modern_modules) - 10} more")
    
    print(f"\n🏗️  MODERN STRUCTURE: {modern_structure}")
    if modern_structure:
        print(f"  • App Name: {app_metadata.get('app_name', 'Unknown')}")
        print(f"  • Dependencies: {len(app_metadata.get('dependencies', []))}")
        print(f"  • Health Score: {health_analysis.get('health_score', 0)}%")
    
    print(f"\n🔧 INSTALLATION BLOCKERS: {len(health_analysis.get('installation_blockers', []))}")
    for blocker in health_analysis.get('installation_blockers', [])[:5]:
        print(f"  • {blocker}")
    
    print(f"\n📊 ENHANCED SUMMARY")
    print("=" * 40)
    print(f"  • Modern Structure: {modern_structure}")
    print(f"  • Modules Detected: {len(modern_modules)}")
    print(f"  • Health Score: {health_analysis.get('health_score', 0)}%")
    print(f"  • Dependencies: {len(app_metadata.get('dependencies', []))}")
    print(f"  • Installation Blockers: {len(health_analysis.get('installation_blockers', []))}")
    
    return analysis_result
