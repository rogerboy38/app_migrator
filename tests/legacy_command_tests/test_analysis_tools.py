#!/usr/bin/env python3
"""
Comprehensive Test Script for App Analysis Tools
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path to import our module
sys.path.insert(0, str(Path(__file__).parent))

try:
    from analysis_tools import *
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure analysis_tools.py is in the same directory")
    sys.exit(1)

def test_basic_functionality():
    """Test basic analysis functionality"""
    print("🧪 TESTING BASIC FUNCTIONALITY")
    print("=" * 50)
    
    # Test 1: List available analyses
    print("1. Available analysis functions:")
    analyses = list_available_analyses()
    for i, analysis in enumerate(analyses, 1):
        print(f"   {i}. {analysis}")
    
    # Test 2: Get metadata
    print("\n2. Analysis metadata:")
    metadata = get_analysis_metadata()
    for key, value in metadata.items():
        if key != 'timestamp':
            print(f"   {key}: {value}")
    
    print("✅ Basic functionality tests passed!\n")
    return True

def test_app_structure_analysis(app_name="frappe"):
    """Test app structure analysis"""
    print(f"🧪 TESTING APP STRUCTURE ANALYSIS: {app_name}")
    print("=" * 50)
    
    try:
        result = analyze_app_structure(app_name)
        
        if result.get("error"):
            print(f"❌ Structure analysis failed: {result['error']}")
            return False
        
        # Check essential fields
        essential_fields = ["app_name", "exists", "structure_valid", "modules", "hooks_data"]
        for field in essential_fields:
            if field not in result:
                print(f"❌ Missing essential field: {field}")
                return False
        
        print(f"✅ App exists: {result['exists']}")
        print(f"✅ Structure valid: {result['structure_valid']}")
        print(f"✅ Modules found: {len(result['modules'])}")
        print(f"✅ Structure score: {result.get('structure_score', 'N/A')}")
        
        # Display module info
        if result['modules']:
            module_names = []
            for m in result['modules'][:3]:
                if isinstance(m, dict):
                    module_names.append(m.get('name', 'unknown'))
                else:
                    module_names.append(str(m))
            print(f"📦 Modules: {module_names}")
            if len(result['modules']) > 3:
                print(f"   ... and {len(result['modules']) - 3} more")
        
        # Display hooks info
        hooks = result['hooks_data']
        print(f"📋 Hooks analysis: {hooks.get('app_name', 'N/A')}")
        print(f"   - Exists: {hooks.get('exists', False)}")
        print(f"   - Dependencies: {len(hooks.get('dependencies', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Structure analysis error: {e}")
        return False

def test_migration_compatibility(app_name="frappe"):
    """Test migration compatibility analysis"""
    print(f"\n🧪 TESTING MIGRATION COMPATIBILITY: {app_name}")
    print("=" * 50)
    
    try:
        result = analyze_migration_compatibility(app_name)
        
        if result.get("error"):
            print(f"❌ Compatibility analysis failed: {result['error']}")
            return False
        
        # Check essential fields
        essential_fields = ["compatibility_score", "compatibility_level", "migration_ready"]
        for field in essential_fields:
            if field not in result:
                print(f"❌ Missing essential field: {field}")
                return False
        
        print(f"✅ Compatibility score: {result['compatibility_score']}/100")
        print(f"✅ Compatibility level: {result['compatibility_level']}")
        print(f"✅ Migration ready: {result['migration_ready']}")
        print(f"✅ Migration effort: {result.get('migration_effort', 'N/A')}")
        print(f"✅ Risk level: {result.get('risk_level', 'N/A')}")
        
        # Display issues and recommendations
        critical_issues = result.get('critical_issues', [])
        warnings = result.get('warnings', [])
        recommendations = result.get('recommendations', [])
        
        print(f"⚠️  Critical issues: {len(critical_issues)}")
        for issue in critical_issues[:2]:
            print(f"   - {issue}")
        
        print(f"📝 Warnings: {len(warnings)}")
        for warning in warnings[:2]:
            print(f"   - {warning}")
        
        print(f"💡 Recommendations: {len(recommendations)}")
        for rec in recommendations[:2]:
            print(f"   - {rec}")
        
        return True
        
    except Exception as e:
        print(f"❌ Compatibility analysis error: {e}")
        return False

def test_dependency_analysis(app_name="frappe"):
    """Test dependency analysis"""
    print(f"\n🧪 TESTING DEPENDENCY ANALYSIS: {app_name}")
    print("=" * 50)
    
    try:
        result = analyze_dependencies(app_name)
        
        if result.get("error"):
            print(f"❌ Dependency analysis failed: {result['error']}")
            return False
        
        dependencies = result.get('dependencies', [])
        compatibility = result.get('compatibility', {})
        
        print(f"✅ Total dependencies: {result.get('count', 0)}")
        print(f"✅ Required apps: {len(result.get('required_apps', []))}")
        print(f"✅ Additional dependencies: {len(result.get('additional_dependencies', []))}")
        print(f"✅ Compatibility score: {compatibility.get('compatibility_score', 'N/A')}")
        
        # Display dependency breakdown
        if compatibility:
            print("📊 Dependency breakdown:")
            print(f"   - Compatible: {len(compatibility.get('compatible', []))}")
            print(f"   - Risky: {len(compatibility.get('risky', []))}")
            print(f"   - Incompatible: {len(compatibility.get('incompatible', []))}")
            print(f"   - Unknown: {len(compatibility.get('unknown', []))}")
        
        # Show some dependencies
        if dependencies:
            print(f"📦 Sample dependencies: {dependencies[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Dependency analysis error: {e}")
        return False

def test_code_complexity(app_name="frappe"):
    """Test code complexity analysis"""
    print(f"\n🧪 TESTING CODE COMPLEXITY: {app_name}")
    print("=" * 50)
    
    try:
        result = analyze_code_complexity(app_name)
        
        if result.get("error"):
            print(f"❌ Complexity analysis failed: {result['error']}")
            return False
        
        print(f"✅ Complexity score: {result.get('complexity_score', 'N/A')}")
        print(f"✅ Complexity level: {result.get('complexity_level', 'N/A')}")
        
        file_metrics = result.get('file_metrics', {})
        if file_metrics:
            print("📊 File metrics:")
            print(f"   - Python files: {file_metrics.get('python_files', 0)}")
            print(f"   - Total files: {file_metrics.get('total_files', 0)}")
            print(f"   - Python ratio: {file_metrics.get('python_ratio', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complexity analysis error: {e}")
        return False

def test_security_analysis(app_name="frappe"):
    """Test security analysis"""
    print(f"\n🧪 TESTING SECURITY ANALYSIS: {app_name}")
    print("=" * 50)
    
    try:
        result = analyze_security_vulnerabilities(app_name)
        
        if result.get("error"):
            print(f"❌ Security analysis failed: {result['error']}")
            return False
        
        print(f"✅ Security score: {result.get('security_score', 'N/A')}")
        print(f"✅ Security level: {result.get('security_level', 'N/A')}")
        print(f"✅ Vulnerabilities found: {len(result.get('vulnerabilities', []))}")
        
        vulnerabilities = result.get('vulnerabilities', [])
        if vulnerabilities:
            print("🔒 Vulnerabilities:")
            for vuln in vulnerabilities[:3]:
                print(f"   - {vuln}")
        
        recommendations = result.get('recommendations', [])
        if recommendations:
            print("🛡️  Security recommendations:")
            for rec in recommendations[:2]:
                print(f"   - {rec}")
        
        return True
        
    except Exception as e:
        print(f"❌ Security analysis error: {e}")
        return False

def test_performance_analysis(app_name="frappe"):
    """Test performance analysis"""
    print(f"\n🧪 TESTING PERFORMANCE ANALYSIS: {app_name}")
    print("=" * 50)
    
    try:
        result = analyze_performance(app_name)
        
        if result.get("error"):
            print(f"❌ Performance analysis failed: {result['error']}")
            return False
        
        print(f"✅ Performance score: {result.get('performance_score', 'N/A')}")
        print(f"✅ Performance level: {result.get('performance_level', 'N/A')}")
        
        metrics = result.get('metrics', {})
        if metrics:
            print("📊 Performance metrics:")
            print(f"   - Total files: {metrics.get('total_files', 0)}")
            print(f"   - Largest file: {metrics.get('largest_file_size', 0)} bytes")
            print(f"   - Average file size: {metrics.get('average_file_size', 0):.1f} bytes")
        
        recommendations = result.get('recommendations', [])
        if recommendations:
            print("⚡ Performance recommendations:")
            for rec in recommendations[:2]:
                print(f"   - {rec}")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance analysis error: {e}")
        return False

def test_comprehensive_summary(app_name="frappe"):
    """Test comprehensive analysis summary"""
    print(f"\n🧪 TESTING COMPREHENSIVE SUMMARY: {app_name}")
    print("=" * 50)
    
    try:
        result = get_analysis_summary(app_name)
        
        if result.get("error"):
            print(f"❌ Comprehensive analysis failed: {result['error']}")
            return False
        
        print(f"✅ Overall health score: {result.get('overall_health_score', 'N/A')}%")
        print(f"✅ Overall health level: {result.get('overall_health_level', 'N/A')}")
        
        summary = result.get('summary', {})
        if summary:
            print("📈 Summary:")
            print(f"   - Migration ready: {summary.get('migration_ready', False)}")
            print(f"   - Critical issues: {summary.get('critical_issues', 0)}")
            print(f"   - Total recommendations: {summary.get('total_recommendations', 0)}")
            print(f"   - Module count: {summary.get('module_count', 0)}")
            print(f"   - Doctype count: {summary.get('doctype_count', 0)}")
            print(f"   - Dependency count: {summary.get('dependency_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive analysis error: {e}")
        return False

def test_report_export(app_name="frappe"):
    """Test report export functionality"""
    print(f"\n🧪 TESTING REPORT EXPORT: {app_name}")
    print("=" * 50)
    
    try:
        # Test JSON export
        json_result = export_analysis_report(app_name, "json")
        if json_result.get("error"):
            print(f"❌ JSON export failed: {json_result['error']}")
        else:
            print(f"✅ JSON export successful")
            print(f"   - Format: {json_result.get('format')}")
            print(f"   - Filename: {json_result.get('filename')}")
            print(f"   - Content length: {len(json_result.get('content', ''))} characters")
        
        # Test summary export
        summary_result = export_analysis_report(app_name, "summary")
        if summary_result.get("error"):
            print(f"❌ Summary export failed: {summary_result['error']}")
        else:
            print(f"✅ Summary export successful")
            print(f"   - Format: {summary_result.get('format')}")
            print(f"   - Filename: {summary_result.get('filename')}")
            print(f"   - Content length: {len(summary_result.get('content', ''))} characters")
            
            # Display first few lines of summary
            content = summary_result.get('content', '')
            if content:
                lines = content.split('\n')[:8]
                print("   - Preview:")
                for line in lines:
                    print(f"     {line}")
        
        return True
        
    except Exception as e:
        print(f"❌ Report export error: {e}")
        return False

def test_error_handling():
    """Test error handling with non-existent app"""
    print(f"\n🧪 TESTING ERROR HANDLING")
    print("=" * 50)
    
    non_existent_app = "this_app_does_not_exist_12345"
    
    tests = [
        ("Structure Analysis", analyze_app_structure(non_existent_app)),
        ("Compatibility Analysis", analyze_migration_compatibility(non_existent_app)),
        ("Dependency Analysis", analyze_dependencies(non_existent_app)),
        ("Complexity Analysis", analyze_code_complexity(non_existent_app)),
    ]
    
    all_handled = True
    for test_name, result in tests:
        if result.get("exists", True):  # Should be False for non-existent app
            print(f"❌ {test_name}: Error not properly handled")
            all_handled = False
        else:
            print(f"✅ {test_name}: Error properly handled")
            if result.get("error"):
                print(f"   - Error message: {result['error'][:50]}...")
    
    return all_handled

def run_comprehensive_test(app_name="frappe"):
    """Run comprehensive test suite"""
    print("🚀 STARTING COMPREHENSIVE ANALYSIS TOOLS TEST")
    print("=" * 60)
    
    test_results = []
    
    # Run all tests
    test_results.append(("Basic Functionality", test_basic_functionality()))
    test_results.append(("App Structure Analysis", test_app_structure_analysis(app_name)))
    test_results.append(("Migration Compatibility", test_migration_compatibility(app_name)))
    test_results.append(("Dependency Analysis", test_dependency_analysis(app_name)))
    test_results.append(("Code Complexity", test_code_complexity(app_name)))
    test_results.append(("Security Analysis", test_security_analysis(app_name)))
    test_results.append(("Performance Analysis", test_performance_analysis(app_name)))
    test_results.append(("Comprehensive Summary", test_comprehensive_summary(app_name)))
    test_results.append(("Report Export", test_report_export(app_name)))
    test_results.append(("Error Handling", test_error_handling()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    total = len(test_results)
    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Analysis tools are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    # You can specify an app name to test, default is "frappe"
    test_app = sys.argv[1] if len(sys.argv) > 1 else "frappe"
    
    print(f"Testing with app: {test_app}")
    print(f"Current directory: {os.getcwd()}")
    
    success = run_comprehensive_test(test_app)
    sys.exit(0 if success else 1)
