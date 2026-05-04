"""
Enhanced Payment Gateway Migrator
Version: 1.1.0
Purpose: Improved gateway configuration detection
"""

import os
import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class PaymentGatewayMigrator:
    """
    Enhanced migrator with better gateway detection patterns
    """
    
    def __init__(self):
        # Broader patterns for gateway detection
        self.enhanced_patterns = {
            'gateway_indicators': [
                # Generic payment patterns
                r'payment.*gateway',
                r'gateway.*payment',
                r'payment_processor',
                r'payment_method',
                
                # Gateway-specific patterns (broader)
                r'stripe',
                r'razorpay', 
                r'paypal',
                r'mpesa',
                r'braintree',
                r'authorize',
                r'square',
                
                # Configuration patterns
                r'api_key',
                r'secret_key', 
                r'client_id',
                r'client_secret',
                r'webhook',
                r'endpoint',
                r'payment.*config'
            ],
            
            'file_patterns': [
                # File names that indicate gateway configurations
                'payment_gateway',
                'gateway_settings',
                'payment_config',
                'stripe',
                'razorpay',
                'paypal',
                'mpesa'
            ]
        }
        
        self.supported_gateways = [
            'stripe', 'razorpay', 'paypal', 'mpesa', 'braintree', 
            'authorize', 'square', 'worldpay', 'adyen'
        ]
    
    def analyze_gateway_configurations(self, app_path: str) -> Dict[str, Any]:
        """
        Enhanced gateway configuration analysis
        """
        print(f"🔍 Enhanced analysis: {app_path}")
        
        if not os.path.exists(app_path):
            return self._create_error_result("App path does not exist")
        
        try:
            analysis = {
                'app_path': app_path,
                'gateway_files_found': [],
                'gateway_indicators': [],
                'potential_gateways': [],
                'configuration_files': [],
                'analysis_method': 'enhanced_patterns'
            }
            
            # Use multiple detection methods
            analysis.update(self._scan_with_enhanced_patterns(app_path))
            analysis.update(self._scan_gateway_directories(app_path))
            analysis.update(self._scan_configuration_files(app_path))
            
            print(f"✅ Enhanced analysis complete")
            return analysis
            
        except Exception as e:
            return self._create_error_result(f"Enhanced analysis failed: {str(e)}")
    
    def _scan_with_enhanced_patterns(self, app_path: str) -> Dict[str, Any]:
        """Scan using enhanced pattern matching"""
        results = {
            'gateway_indicators': [],
            'potential_gateways': []
        }
        
        gateway_hits = {}
        
        for root, dirs, files in os.walk(app_path):
            # Skip non-relevant directories
            if any(skip in root for skip in ['env', 'venv', '.git', '__pycache__', 'node_modules']):
                continue
                
            for file in files:
                if file.endswith(('.py', '.js', '.json', '.yaml', '.yml', '.html', '.md')):
                    file_path = os.path.join(root, file)
                    relative_path = file_path.replace(app_path, '')
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().lower()
                            
                            # Check for gateway indicators
                            for indicator in self.enhanced_patterns['gateway_indicators']:
                                if re.search(indicator, content, re.IGNORECASE):
                                    results['gateway_indicators'].append({
                                        'file': relative_path,
                                        'indicator': indicator,
                                        'context': self._get_context(content, indicator)
                                    })
                            
                            # Check for specific gateways
                            for gateway in self.supported_gateways:
                                if gateway in content:
                                    if gateway not in gateway_hits:
                                        gateway_hits[gateway] = []
                                    gateway_hits[gateway].append(relative_path)
                                    
                    except Exception:
                        continue
        
        # Process gateway hits
        for gateway, files in gateway_hits.items():
            if len(files) > 0:  # If found in at least one file
                results['potential_gateways'].append({
                    'gateway': gateway,
                    'files': files[:5],  # Limit to first 5 files
                    'file_count': len(files),
                    'confidence': 'medium' if len(files) > 1 else 'low'
                })
        
        return results
    
    def _scan_gateway_directories(self, app_path: str) -> Dict[str, Any]:
        """Scan for gateway-specific directories"""
        results = {
            'gateway_directories': []
        }
        
        # Look for directories that indicate gateway configurations
        gateway_dir_indicators = [
            'payment_gateway', 'gateways', 'payments', 'payment',
            'stripe', 'razorpay', 'paypal', 'mpesa'
        ]
        
        for root, dirs, files in os.walk(app_path):
            for directory in dirs:
                dir_lower = directory.lower()
                for indicator in gateway_dir_indicators:
                    if indicator in dir_lower:
                        full_path = os.path.join(root, directory)
                        relative_path = full_path.replace(app_path, '')
                        
                        results['gateway_directories'].append({
                            'directory': relative_path,
                            'indicator': indicator,
                            'file_count': len([f for f in os.listdir(full_path) if os.path.isfile(os.path.join(full_path, f))])
                        })
        
        return results
    
    def _scan_configuration_files(self, app_path: str) -> Dict[str, Any]:
        """Scan for configuration files"""
        results = {
            'configuration_files': []
        }
        
        config_file_patterns = [
            'config', 'setting', 'configuration', 'env', 'secret',
            'payment', 'gateway', 'stripe', 'razorpay', 'paypal'
        ]
        
        for root, dirs, files in os.walk(app_path):
            for file in files:
                file_lower = file.lower()
                if any(pattern in file_lower for pattern in config_file_patterns):
                    full_path = os.path.join(root, file)
                    relative_path = full_path.replace(app_path, '')
                    
                    results['configuration_files'].append({
                        'file': relative_path,
                        'type': self._classify_config_file(file)
                    })
        
        return results
    
    def _get_context(self, content: str, pattern: str, context_chars: int = 100) -> str:
        """Get context around a pattern match"""
        try:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                start = max(0, match.start() - context_chars)
                end = min(len(content), match.end() + context_chars)
                return content[start:end].replace('\\n', ' ').strip()
        except:
            pass
        return "Context unavailable"
    
    def _classify_config_file(self, filename: str) -> str:
        """Classify configuration file type"""
        filename_lower = filename.lower()
        
        if any(ext in filename_lower for ext in ['.py', '.js']):
            return 'code_config'
        elif any(ext in filename_lower for ext in ['.json', '.yaml', '.yml']):
            return 'data_config'
        elif any(ext in filename_lower for ext in ['.env', '.ini', '.cfg']):
            return 'environment_config'
        else:
            return 'other_config'
    
    def _create_error_result(self, message: str) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            'error': message,
            'gateway_files_found': [],
            'gateway_indicators': [],
            'potential_gateways': [],
            'configuration_files': []
        }
    
    def generate_enhanced_report(self, analysis: Dict[str, Any]) -> str:
        """Generate enhanced analysis report"""
        report = []
        report.append("=" * 60)
        report.append("🔍 ENHANCED GATEWAY ANALYSIS REPORT")
        report.append("=" * 60)
        report.append(f"App: {analysis.get('app_path', 'Unknown')}")
        report.append(f"Analysis Method: {analysis.get('analysis_method', 'Unknown')}")
        report.append("")
        
        # Potential Gateways
        potential_gateways = analysis.get('potential_gateways', [])
        if potential_gateways:
            report.append("💳 POTENTIAL PAYMENT GATEWAYS:")
            for gateway_info in potential_gateways:
                report.append(f"  • {gateway_info['gateway'].title()} (confidence: {gateway_info['confidence']})")
                report.append(f"    Found in {gateway_info['file_count']} files")
                for file in gateway_info['files'][:3]:  # Show first 3 files
                    report.append(f"    - {file}")
            report.append("")
        else:
            report.append("❌ No specific payment gateways detected")
            report.append("")
        
        # Gateway Indicators
        indicators = analysis.get('gateway_indicators', [])
        if indicators:
            report.append("📊 GATEWAY INDICATORS FOUND:")
            unique_indicators = {}
            for indicator in indicators:
                pattern = indicator['indicator']
                if pattern not in unique_indicators:
                    unique_indicators[pattern] = 0
                unique_indicators[pattern] += 1
            
            for pattern, count in list(unique_indicators.items())[:10]:  # Show top 10
                report.append(f"  • {pattern}: {count} occurrences")
            report.append("")
        
        # Configuration Files
        config_files = analysis.get('configuration_files', [])
        if config_files:
            report.append("⚙️ CONFIGURATION FILES:")
            for config in config_files[:10]:  # Show first 10
                report.append(f"  • {config['file']} ({config['type']})")
            report.append("")
        
        return "\n".join(report)


# Test the enhanced migrator
def test_enhanced_migrator():
    migrator = PaymentGatewayMigrator()
    payments_path = '/home/frappe/frappe-bench-v533/apps/payments'
    
    print("🧪 TESTING ENHANCED GATEWAY MIGRATOR")
    print("=" * 50)
    
    if os.path.exists(payments_path):
        analysis = migrator.analyze_gateway_configurations(payments_path)
        report = migrator.generate_enhanced_report(analysis)
        print(report)
    else:
        print("❌ Payments app not found")

if __name__ == "__main__":
    test_enhanced_migrator()
