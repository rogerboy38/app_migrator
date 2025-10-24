from . import __version__ as version
app_name = "app_migrator"
app_title = "App Migrator Enterprise"
app_publisher = "psmhosting.com"
app_description = "AI-Powered Enterprise Application Migration System for Frappe/ERPNext"
app_email = "info@psmhosting.com"
app_license = "MIT"
app_version = "7.0.1"

# Include JS/CSS in assets builder
app_include_js = "/assets/app_migrator/js/app_migrator.js"
app_include_css = "/assets/app_migrator/css/app_migrator.css"

# App includes
app_include_js = [
    "assets/app_migrator/js/core_engine.bundle.js",
    "assets/app_migrator/js/ai_agents.bundle.js",
    "assets/app_migrator/js/enterprise_features.bundle.js"
]

# Scheduled Tasks - COMMENT OUT FOR NOW
# scheduler_events = {
#     "daily": [
#         "app_migrator.monitoring.health_checker.daily_health_check"
#     ],
#     "hourly": [
#         "app_migrator.monitoring.performance_monitor.hourly_metrics"
#     ]
# }

# Fixtures
fixtures = [
    {
        "dt": "Custom Field", 
        "filters": [
            ["module", "=", "App Migrator"]
        ]
    }
]

# REMOVE these lines completely:
# boot_session = "app_migrator.boot.get_bootinfo"
# after_install = "app_migrator.setup.install.after_install"
