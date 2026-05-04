#!/usr/bin/env python3
"""
Comprehensive Test for Payment Migration Suite
Tests both Security Migrator and Gateway Migrator
"""

import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, '.')

from payment_security_migrator import PaymentSecurityMigrator, generate_security_report
from payment_gateway_migrator import PaymentGatewayMigrator, generate_gateway_report

def main():
    print("🧪 COMPREHENSIVE PAYMENT MIGRATION SUITE TEST")
    print("=" * 60)
    
    payments_path = '/home/frappe/frappe-bench-v533/apps/payments'
    test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not os.path.exists(payments_path):
        print(f"❌ Payments app not found: {payments_path}")
        return
    
    print(f"📁 Testing on: {payments_path}")
    print(f"⏰ Test timestamp: {test_timestamp}")
    print()
    
    # Initialize migrators
    security_migrator = PaymentSecurityMigrator()
    gateway_migrator = PaymentGatewayMigrator()
    
    # Run comprehensive analysis
    print("1. 🏃 RUNNING COMPREHENSIVE ANALYSIS...")
    
    security_analysis = security_migrator.analyze_security_configurations(payments_path)
    gateway_analysis = gateway_migrator.analyze_gateway_configurations(payments_path)
    
    print("2. 📊 GENERATING REPORTS...")
    
    # Generate individual reports
    security_report = generate_security_report(security_analysis)
    gateway_report = generate_gateway_report(gateway_analysis)
    
    print(security_report)
    print()
    print(gateway_report)
    
    print("3. 🚀 SIMULATING COMPLETE MIGRATION...")
    
    # Simulate migrations
    security_migration = security_migrator.migrate_security_configurations(
        payments_path, f"/tmp/payments_migration_{test_timestamp}", dry_run=True
    )
    
    gateway_migration = gateway_migrator.migrate_gateway_configurations(
        payments_path, f"/tmp/payments_migration_{test_timestamp}", dry_run=True
    )
    
    print("4. 📈 MIGRATION METRICS SUMMARY:")
    print(f"   🔐 Security Analysis:")
    print(f"      - API Keys Found: {len(security_analysis.get('api_keys_found', []))}")
    print(f"      - Security Risks: {len(security_analysis.get('security_risks', []))}")
    print(f"      - Migration Steps: {len(security_migration.get('migration_steps', []))}")
    
    print(f"   💳 Gateway Analysis:")
    print(f"      - Gateways Found: {len(gateway_analysis.get('gateways_found', []))}")
    print(f"      - Gateway Configs: {len(gateway_analysis.get('gateway_configs', {}))}")
    print(f"      - Migration Steps: {len(gateway_migration.get('migration_steps', []))}")
    
    print(f"   📋 Combined Metrics:")
    total_steps = len(security_migration.get('migration_steps', [])) + len(gateway_migration.get('migration_steps', []))
    total_risks = len(security_analysis.get('security_risks', [])) + len(gateway_analysis.get('migration_risks', []))
    print(f"      - Total Migration Steps: {total_steps}")
    print(f"      - Total Risks Identified: {total_risks}")
    
    # Save detailed test results
    test_results = {
        'test_timestamp': test_timestamp,
        'app_path': payments_path,
        'security_analysis': security_analysis,
        'gateway_analysis': gateway_analysis,
        'security_migration': security_migration,
        'gateway_migration': gateway_migration,
        'summary': {
            'total_migration_steps': total_steps,
            'total_risks': total_risks,
            'gateways_found': gateway_analysis.get('gateways_found', []),
            'security_issues': len(security_analysis.get('security_risks', [])),
            'api_keys_found': len(security_analysis.get('api_keys_found', []))
        }
    }
    
    # Save results to file
    results_file = f"/tmp/payment_migration_test_{test_timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\\n💾 Detailed test results saved to: {results_file}")
    print("🎉 PAYMENT MIGRATION SUITE TEST COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
