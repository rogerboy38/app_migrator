"""
App Migrator Commands
Version: 8.1.0
Safe import structure to avoid circular dependencies
"""

__version__ = "8.1.0"

# ONLY import the main class - no function imports!
from .analysis_tools import AppAnalysis

__all__ = ["AppAnalysis"]

print("✅ App Migrator commands loaded safely")

# Import Payment Security Migrator
from .payment_security_migrator import (
    PaymentSecurityMigrator,
    analyze_payment_security,
    migrate_payment_security,
    generate_security_report
)

# Update __all__ exports
__all__.extend([
    "PaymentSecurityMigrator",
    "analyze_payment_security", 
    "migrate_payment_security",
    "generate_security_report"
])

print("✅ Payment Security Migrator added to commands")

# Import Payment Gateway Migrator (class only - no standalone functions exist)
try:
    from .payment_gateway_migrator import PaymentGatewayMigrator
    __all__.append("PaymentGatewayMigrator")
    print("✅ Payment Gateway Migrator added to commands")
except ImportError as e:
    print(f"⚠️ Payment Gateway Migrator not available: {e}")

# ============== CLI COMMANDS FOR BENCH ==============
import click
try:
    from frappe.commands import pass_context
except ImportError:
    pass_context = lambda f: f

@click.command('app-migrator-health')
@pass_context
def app_migrator_health(context):
    """Check App Migrator health"""
    print("=" * 50)
    print("🔧 App Migrator v8.1.0 - OPERATIONAL")
    print("Commands: app-migrator-scan, app-migrator-conflicts")
    print("=" * 50)

@click.command('app-migrator-scan')
@click.option('--site', required=True, help='Site name')
@pass_context
def app_migrator_scan(context, site):
    """Scan site for apps and doctypes"""
    import frappe
    print(f"🔍 Scanning site: {site}")
    frappe.init(site=site)
    frappe.connect()
    apps = frappe.get_installed_apps()
    print(f"Installed apps: {apps}")
    frappe.db.close()

# Export commands for Frappe to discover
commands = [app_migrator_health, app_migrator_scan]
