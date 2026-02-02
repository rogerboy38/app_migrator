#!/usr/bin/env python3
"""
Quick test for Payment Security Migrator
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, '.')

from app_migrator.commands.payment_security_migrator import (
    PaymentSecurityMigrator, 
    analyze_payment_security
)

def main():
    print("🧪 QUICK TEST: PAYMENT SECURITY MIGRATOR")
    print("=" * 50)
    
    payments_path = '/home/frappe/frappe-bench-v533/apps/payments'
    
    if os.path.exists(payments_path):
        print(f"Testing on: {payments_path}")
        
        # Test 1: Basic analysis
        print("\n1. Basic Security Analysis:")
        analysis = analyze_payment_security(payments_path)
        
        print(f"   ✅ API Keys Found: {len(analysis.get('api_keys_found', []))}")
        print(f"   ✅ Webhook Configs: {len(analysis.get('webhook_configs', []))}")
        print(f"   ✅ Security Risks: {len(analysis.get('security_risks', []))}")
        
        # Test 2: Full migrator
        print("\n2. Full Migrator Test:")
        migrator = PaymentSecurityMigrator()
        report = migrator.generate_security_report(analysis)
        print(report)
        
        print("\n🎉 PAYMENT SECURITY MIGRATOR TEST PASSED!")
        
    else:
        print(f"❌ Payments app not found: {payments_path}")

if __name__ == "__main__":
    main()
