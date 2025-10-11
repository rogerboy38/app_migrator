app_name = "app_migrator"
app_title = "App Migrator Ultimate v5.1.0 with Auto-Fix"
app_publisher = "Frappe Community"
app_description = "Ultimate Frappe App Migration System v5.0.4 with Enhanced DocType Classification"
app_email = "fcrm@amb-wellness.com"
app_license = "mit"
app_version = "5.1.0"

# Required apps
required_apps = ["frappe"]

# Bench Commands
commands = [
    {
        "cmd": "app-migrator",
        "callable": "app_migrator.commands"
    }
]

# App Migrator Commands
from . import commands as app_migrator_commands
commands = app_migrator_commands.commands
