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
