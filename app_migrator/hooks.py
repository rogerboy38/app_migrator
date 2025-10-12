app_name = "app_migrator"
app_title = "App Migrator Ultimate"
app_publisher = "Frappe Community"
app_description = "Ultimate Frappe App Migration System with Enhanced Diagnostics"
app_email = "fcrm@amb-wellness.com"
app_license = "mit"

# Import version from single source
from app_migrator import __version__
app_version = __version__

# Required apps
required_apps = ["frappe"]

# Bench Commands
commands = [
    {
        "cmd": "migrate-app",
        "callable": "app_migrator.commands"
    }
]
