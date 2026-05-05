"""
Payment Security Migrator
Version: 1.0.0
Purpose: Secure migration of payment app security configurations
"""

import os
import re
import json
import hashlib
import secrets
from typing import Dict, List, Any, Optional
import tempfile
import shutil


class PaymentSecurityMigrator:
    """
    Specialized migrator for payment app security configurations
    Handles API keys, webhooks, encryption, and security compliance
    """
    
    def __init__(self):
        self.security_patterns = {
            'api_keys': [
                r'api_key\s*=\s*[\'"]([^\'"]+)[\'"]',
                r'api_key\s*:\s*[\'"]([^\'"]+)[\'"]',
                r'secret_key\s*=\s*[\'"]([^\'"]+)[\'"]',
                r'secret\s*=\s*[\'"]([^\'"]+)[\'"]',
                r'password\s*=\s*[\'"]([^\'"]+)[\'"]',
                r'token\s*=\s*[\'"]([^\'"]+)[\'"]',
            ],
            'webhook_urls': [
                r'webhook_url\s*=\s*[\'"]([^\'"]+)[\'"]',
                r'callback_url\s*=\s*[\'"]([^\'"]+)[\'"]',
                r'endpoint\s*=\s*[\'"]([^\'"]+)[\'"]',
                r'url.*webhook[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]',
            ],
            'encryption_patterns': [
                r'encrypt\(',
                r'decrypt\(',
                r'cryptography',
                r'fernet',
                r'aes',
                r'rsa',
            ]
        }
        
        self.payment_gateways = [
            'stripe', 'razorpay', 'paypal', 'braintree', 'authorize', 
            'square', 'worldpay', 'adyen'
        ]
        
        self.migration_log = []
    
    def analyze_security_configurations(self, app_path: str) -> Dict[str, Any]:
        """
        Comprehensive security configuration analysis for payment apps
        """
        print(f"🔍 Analyzing security configurations: {app_path}")
        
        if not os.path.exists(app_path):
            return self._create_error_result("App path does not exist")
        
        try:
            security_analysis = {
                'app_path': app_path,
                'security_risks': [],
                'api_keys_found': [],
                'webhook_configs': [],
                'encryption_usage': [],
                'gateway_configs': [],
                'migration_risks': [],
                'recommendations': []
            }
            
            # Scan for security patterns
            security_analysis.update(self._scan_security_patterns(app_path))
            
            # Check for hardcoded secrets
            security_analysis.update(self._check_hardcoded_secrets(app_path))
            
            # Analyze webhook configurations
            security_analysis.update(self._analyze_webhooks(app_path))
            
            # Check encryption implementations
            security_analysis.update(self._analyze_encryption(app_path))
            
            # Generate risk assessment
            security_analysis.update(self._generate_risk_assessment(security_analysis))
            
            print(f"✅ Security analysis complete: {len(security_analysis['security_risks'])} risks found")
            return security_analysis
            
        except Exception as e:
            return self._create_error_result(f"Security analysis failed: {str(e)}")
    
    def _scan_security_patterns(self, app_path: str) -> Dict[str, Any]:
        """Scan for security-related patterns in code"""
        results = {
            'api_keys_found': [],
            'webhook_configs': [],
            'encryption_usage': [],
            'gateway_configs': []
        }
        
        for root, dirs, files in os.walk(app_path):
            # Skip virtual environments and git directories
            if any(skip in root for skip in ['env', 'venv', '.git', '__pycache__']):
                continue
                
            for file in files:
                if file.endswith(('.py', '.js', '.json', '.yaml', '.yml')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            # Check for API keys
                            for pattern in self.security_patterns['api_keys']:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    if len(match) > 10:  # Basic validation it's not empty
                                        results['api_keys_found'].append({
                                            'file': file_path.replace(app_path, ''),
                                            'pattern': pattern,
                                            'value_preview': f"{match[:10]}...",  # Don't log full keys
                                            'risk_level': 'high'
                                        })
                            
                            # Check for webhook URLs
                            for pattern in self.security_patterns['webhook_urls']:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    results['webhook_configs'].append({
                                        'file': file_path.replace(app_path, ''),
                                        'pattern': pattern,
                                        'url': match,
                                        'needs_update': True
                                    })
                            
                            # Check for encryption usage
                            for pattern in self.security_patterns['encryption_patterns']:
                                if re.search(pattern, content, re.IGNORECASE):
                                    results['encryption_usage'].append({
                                        'file': file_path.replace(app_path, ''),
                                        'pattern': pattern
                                    })
                            
                            # Check for payment gateway configurations
                            for gateway in self.payment_gateways:
                                if gateway in content.lower():
                                    results['gateway_configs'].append({
                                        'gateway': gateway,
                                        'file': file_path.replace(app_path, ''),
                                        'configured': True
                                    })
                                    
                    except Exception as e:
                        continue  # Skip files we can't read
        
        return results
    
    def _check_hardcoded_secrets(self, app_path: str) -> Dict[str, Any]:
        """Check for hardcoded secrets and security risks"""
        risks = []
        
        # Common secret patterns (partial matches to avoid logging actual secrets)
        secret_indicators = [
            r'sk_[\w]+',  # Stripe secret key pattern
            r'rzp_[\w]+',  # Razorpay key pattern
            r'AKIA[0-9A-Z]{16}',  # AWS key pattern
        ]
        
        for root, dirs, files in os.walk(app_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            for pattern in secret_indicators:
                                if re.search(pattern, content):
                                    risks.append({
                                        'risk': 'Hardcoded secret detected',
                                        'file': file_path.replace(app_path, ''),
                                        'pattern': pattern,
                                        'severity': 'critical'
                                    })
                    
                    except Exception:
                        continue
        
        return {'security_risks': risks}
    
    def _analyze_webhooks(self, app_path: str) -> Dict[str, Any]:
        """Analyze webhook configurations and dependencies"""
        webhook_analysis = {
            'webhook_endpoints': [],
            'migration_actions': []
        }
        
        # Look for webhook configuration files
        webhook_files = []
        for root, dirs, files in os.walk(app_path):
            for file in files:
                if any(term in file.lower() for term in ['webhook', 'callback', 'endpoint']):
                    webhook_files.append(os.path.join(root, file))
        
        for webhook_file in webhook_files:
            webhook_analysis['webhook_endpoints'].append({
                'file': webhook_file.replace(app_path, ''),
                'needs_url_update': True,
                'action_required': 'Update webhook URLs in gateway dashboards'
            })
        
        return webhook_analysis
    
    def _analyze_encryption(self, app_path: str) -> Dict[str, Any]:
        """Analyze encryption implementations and key management"""
        encryption_findings = {
            'encryption_methods': [],
            'key_management': [],
            'recommendations': []
        }
        
        # Look for encryption-related files
        for root, dirs, files in os.walk(app_path):
            for file in files:
                if any(term in file.lower() for term in ['crypto', 'encrypt', 'decrypt', 'key', 'secret']):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            if any(method in content for method in ['AES', 'RSA', 'Fernet', 'cryptography']):
                                encryption_findings['encryption_methods'].append({
                                    'file': file_path.replace(app_path, ''),
                                    'methods_found': self._detect_encryption_methods(content)
                                })
                    
                    except Exception:
                        continue
        
        return encryption_findings
    
    def _detect_encryption_methods(self, content: str) -> List[str]:
        """Detect specific encryption methods used"""
        methods = []
        crypto_patterns = {
            'AES': r'aes|AES',
            'RSA': r'rsa|RSA',
            'Fernet': r'fernet|Fernet',
            'Cryptography': r'cryptography',
            'Hashlib': r'hashlib',
        }
        
        for method, pattern in crypto_patterns.items():
            if re.search(pattern, content):
                methods.append(method)
        
        return methods
    
    def _generate_risk_assessment(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive risk assessment"""
        risks = []
        recommendations = []
        
        # API Key Risks
        if analysis['api_keys_found']:
            risks.append({
                'category': 'API Keys',
                'risk': f"{len(analysis['api_keys_found'])} API keys found in code",
                'severity': 'high',
                'impact': 'Security breach if keys are exposed'
            })
            recommendations.append("Move API keys to environment variables or secure config")
        
        # Webhook Risks
        if analysis['webhook_configs']:
            risks.append({
                'category': 'Webhooks',
                'risk': f"{len(analysis['webhook_configs'])} webhook configurations found",
                'severity': 'medium',
                'impact': 'Payment failures if URLs not updated'
            })
            recommendations.append("Plan webhook URL updates in payment gateway dashboards")
        
        # Encryption Risks
        if analysis['encryption_usage']:
            risks.append({
                'category': 'Encryption',
                'risk': 'Custom encryption implementation detected',
                'severity': 'medium',
                'impact': 'Data decryption failures during migration'
            })
            recommendations.append("Test encryption/decryption in target environment")
        
        return {
            'migration_risks': risks,
            'recommendations': recommendations
        }
    
    def migrate_security_configurations(self, source_path: str, target_path: str, 
                                      dry_run: bool = True) -> Dict[str, Any]:
        """
        Migrate security configurations from source to target
        """
        print(f"🚀 Starting security configuration migration")
        print(f"   Source: {source_path}")
        print(f"   Target: {target_path}")
        print(f"   Dry Run: {dry_run}")
        
        migration_report = {
            'source_path': source_path,
            'target_path': target_path,
            'dry_run': dry_run,
            'migration_steps': [],
            'warnings': [],
            'success': False
        }
        
        try:
            # 1. Analyze source security configurations
            source_analysis = self.analyze_security_configurations(source_path)
            migration_report['source_analysis'] = source_analysis
            
            # 2. Create security migration plan
            migration_plan = self._create_migration_plan(source_analysis, target_path)
            migration_report['migration_plan'] = migration_plan
            
            # 3. Execute migration (or simulate for dry run)
            if not dry_run:
                migration_results = self._execute_migration(migration_plan, source_path, target_path)
                migration_report.update(migration_results)
                migration_report['success'] = True
            else:
                migration_report['migration_steps'] = migration_plan['steps']
                migration_report['success'] = True  # Dry run success
            
            print(f"✅ Security migration {'simulation' if dry_run else 'execution'} completed")
            
        except Exception as e:
            error_msg = f"Security migration failed: {str(e)}"
            print(f"❌ {error_msg}")
            migration_report['error'] = error_msg
            migration_report['success'] = False
        
        return migration_report
    
    def _create_migration_plan(self, analysis: Dict[str, Any], target_path: str) -> Dict[str, Any]:
        """Create detailed security migration plan"""
        plan = {
            'steps': [],
            'pre_migration_checks': [],
            'post_migration_validations': [],
            'rollback_steps': []
        }
        
        # API Key Migration Steps
        if analysis['api_keys_found']:
            plan['steps'].append({
                'step': 'api_key_migration',
                'description': 'Migrate API keys to secure storage',
                'actions': [
                    'Extract API keys from source code',
                    'Store in environment variables',
                    'Update code to read from environment',
                    'Validate key functionality'
                ],
                'risk_level': 'high'
            })
        
        # Webhook Migration Steps
        if analysis['webhook_configs']:
            plan['steps'].append({
                'step': 'webhook_migration',
                'description': 'Update webhook URLs',
                'actions': [
                    'Document current webhook URLs',
                    'Generate new webhook URLs for target',
                    'Update payment gateway configurations',
                    'Test webhook delivery'
                ],
                'risk_level': 'medium'
            })
        
        # Encryption Migration Steps
        if analysis['encryption_usage']:
            plan['steps'].append({
                'step': 'encryption_migration',
                'description': 'Validate encryption compatibility',
                'actions': [
                    'Test encryption/decryption in target',
                    'Verify key compatibility',
                    'Ensure data can be decrypted after migration'
                ],
                'risk_level': 'medium'
            })
        
        return plan
    
    def _execute_migration(self, plan: Dict[str, Any], source_path: str, target_path: str) -> Dict[str, Any]:
        """Execute the security migration plan"""
        results = {
            'executed_steps': [],
            'warnings': [],
            'errors': []
        }
        
        # This would contain the actual migration logic
        # For now, we'll simulate the execution
        
        for step in plan['steps']:
            results['executed_steps'].append({
                'step': step['step'],
                'status': 'simulated',
                'details': f"Would execute: {step['description']}"
            })
        
        return results
    
    def generate_security_report(self, analysis: Dict[str, Any], 
                               output_format: str = 'text') -> str:
        """Generate comprehensive security migration report"""
        if output_format == 'json':
            return json.dumps(analysis, indent=2)
        
        # Text format report
        report = []
        report.append("=" * 60)
        report.append("🔐 PAYMENT SECURITY MIGRATION REPORT")
        report.append("=" * 60)
        report.append(f"App: {analysis.get('app_path', 'Unknown')}")
        report.append(f"Security Risks Found: {len(analysis.get('security_risks', []))}")
        report.append(f"API Keys Found: {len(analysis.get('api_keys_found', []))}")
        report.append(f"Webhook Configs: {len(analysis.get('webhook_configs', []))}")
        report.append("")
        
        # Security Risks
        if analysis.get('security_risks'):
            report.append("🔴 CRITICAL SECURITY RISKS:")
            for risk in analysis['security_risks']:
                report.append(f"  • {risk['risk']} in {risk['file']}")
            report.append("")
        
        # Migration Recommendations
        if analysis.get('recommendations'):
            report.append("🎯 MIGRATION RECOMMENDATIONS:")
            for rec in analysis['recommendations']:
                report.append(f"  • {rec}")
            report.append("")
        
        # API Key Findings
        if analysis.get('api_keys_found'):
            report.append("🔑 API KEY FINDINGS:")
            for key in analysis['api_keys_found'][:5]:  # Show first 5
                report.append(f"  • {key['file']} - {key['pattern']}")
            if len(analysis['api_keys_found']) > 5:
                report.append(f"  ... and {len(analysis['api_keys_found']) - 5} more")
            report.append("")
        
        return "\n".join(report)
    
    def _create_error_result(self, message: str) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            'error': message,
            'security_risks': [],
            'api_keys_found': [],
            'webhook_configs': [],
            'migration_risks': [],
            'recommendations': []
        }


# Convenience functions
def analyze_payment_security(app_path: str) -> Dict[str, Any]:
    """Convenience function for security analysis"""
    migrator = PaymentSecurityMigrator()
    return migrator.analyze_security_configurations(app_path)

def migrate_payment_security(source_path: str, target_path: str, dry_run: bool = True) -> Dict[str, Any]:
    """Convenience function for security migration"""
    migrator = PaymentSecurityMigrator()
    return migrator.migrate_security_configurations(source_path, target_path, dry_run)

def generate_security_report(analysis: Dict[str, Any], output_format: str = 'text') -> str:
    """Convenience function for report generation"""
    migrator = PaymentSecurityMigrator()
    return migrator.generate_security_report(analysis, output_format)


if __name__ == "__main__":
    # Test the migrator
    migrator = PaymentSecurityMigrator()
    print("Payment Security Migrator - Test Mode")
    print("Usage:")
    print("  analyze_payment_security('/path/to/app')")
    print("  migrate_payment_security('/source', '/target', dry_run=True)")
