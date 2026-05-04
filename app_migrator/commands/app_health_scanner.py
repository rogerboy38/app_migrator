#!/usr/bin/env python3
"""
🔍 APP HEALTH SCANNER
Quick health checks for multiple apps
"""

import os
from typing import Any


class AppHealthScanner:
    """Batch health scanning for multiple apps"""

    def __init__(self):
        self.bench_path = os.getenv('BENCH_PATH', os.path.expanduser('~/frappe-bench-v5'))

    def scan_bench_apps(self) -> dict[str, Any]:
        """Scan all apps in the bench"""
        apps_path = os.path.join(self.bench_path, 'apps')

        if not os.path.exists(apps_path):
            return {"error": "Apps directory not found"}

        apps_health = {}
        for app_name in os.listdir(apps_path):
            app_path = os.path.join(apps_path, app_name)
            if os.path.isdir(app_path):
                try:
                    from .pre_installation_diagnostics import PreInstallationAnalyzer
                    analyzer = PreInstallationAnalyzer()
                    health_report = analyzer.analyze_app_health(app_path)
                    apps_health[app_name] = health_report
                except Exception as e:
                    apps_health[app_name] = {"error": str(e)}

        return {
            "total_apps_scanned": len(apps_health),
            "apps_health": apps_health,
            "summary": self._generate_bench_summary(apps_health)
        }

    def _generate_bench_summary(self, apps_health: dict[str, Any]) -> dict[str, Any]:
        """Generate bench-wide health summary"""
        healthy_apps = 0
        warning_apps = 0
        critical_apps = 0
        total_blockers = 0

        for _app_name, health in apps_health.items():
            if "error" in health:
                critical_apps += 1
                continue

            score = health.get("health_score", 0)
            blockers = len(health.get("installation_blockers", []))
            total_blockers += blockers

            if score >= 80 and blockers == 0:
                healthy_apps += 1
            elif score >= 50:
                warning_apps += 1
            else:
                critical_apps += 1

        return {
            "healthy_apps": healthy_apps,
            "warning_apps": warning_apps,
            "critical_apps": critical_apps,
            "total_blockers": total_blockers,
            "bench_health_score": self._calculate_bench_health_score(apps_health)
        }

    def _calculate_bench_health_score(self, apps_health: dict[str, Any]) -> int:
        """Calculate overall bench health score"""
        total_score = 0
        valid_apps = 0

        for _app_name, health in apps_health.items():
            if "error" not in health:
                total_score += health.get("health_score", 0)
                valid_apps += 1

        return int(total_score / valid_apps) if valid_apps > 0 else 0

def scan_bench_health_function():
    """Scan health of all apps in bench"""
    scanner = AppHealthScanner()

    try:
        results = scanner.scan_bench_apps()

        print(f"\n{'='*60}")
        print("🔍 BENCH HEALTH SCAN REPORT")
        print(f"{'='*60}")

        summary = results['summary']
        print(f"📊 Overall Bench Health: {summary['bench_health_score']}%")
        print(f"✅ Healthy Apps: {summary['healthy_apps']}")
        print(f"⚠️  Warning Apps: {summary['warning_apps']}")
        print(f"❌ Critical Apps: {summary['critical_apps']}")
        print(f"🚫 Total Blockers: {summary['total_blockers']}")

        # Show critical apps
        critical_apps = []
        for app_name, health in results['apps_health'].items():
            if "error" in health or health.get("health_score", 0) < 50:
                critical_apps.append(app_name)

        if critical_apps:
            print("\n🚨 CRITICAL APPS NEEDING ATTENTION:")
            for app in critical_apps:
                print(f"  • {app}")

        print(f"\n{'='*60}")

        return results

    except Exception as e:
        print(f"❌ Bench scan failed: {e!s}")

def quick_health_check_function(app_name):
    """Quick health check for a single app"""
    bench_path = os.getenv('BENCH_PATH', os.path.expanduser('~/frappe-bench-v5'))
    app_path = os.path.join(bench_path, 'apps', app_name)

    if not os.path.exists(app_path):
        print(f"❌ App '{app_name}' not found in apps directory")
        return

    try:
        from .pre_installation_diagnostics import PreInstallationAnalyzer
        analyzer = PreInstallationAnalyzer()
        analysis = analyzer.analyze_app_health(app_path)

        print(f"\n🔍 QUICK HEALTH CHECK: {app_name}")
        print(f"📊 Health Score: {analysis['health_score']}%")

        if analysis['installation_blockers']:
            print(f"🚫 Blockers: {len(analysis['installation_blockers'])}")
            for blocker in analysis['installation_blockers'][:3]:
                print(f"  • {blocker}")
        else:
            print("✅ No installation blockers found")

        if analysis['health_score'] >= 80:
            print("🎉 App is healthy and ready for installation!")
        elif analysis['health_score'] >= 50:
            print("⚠️  App has some issues but may install")
        else:
            print("❌ App needs significant repairs before installation")

        return analysis

    except Exception as e:
        print(f"❌ Health check failed: {e!s}")
