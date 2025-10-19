"""
App Migrator Commands
Version: 6.3.0
Safe import structure to avoid circular dependencies
"""

__version__ = "6.3.0"

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

# Import Payment Gateway Migrator
from .payment_gateway_migrator import (
    PaymentGatewayMigrator,
    analyze_payment_gateways,
    migrate_payment_gateways,
    generate_gateway_report
)

# Update __all__ exports with gateway migrator
__all__.extend([
    "PaymentGatewayMigrator",
    "analyze_payment_gateways", 
    "migrate_payment_gateways",
    "generate_gateway_report"
])

print("✅ Payment Gateway Migrator added to commands")
