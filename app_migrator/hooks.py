from . import __version__ as version

app_name = "app_migrator"
app_title = "App Migrator Ultimate v5.2.0 with Auto-Fix"
app_publisher = "Frappe Community"
app_description = "Ultimate Frappe App Migration System v5.2.0 with Enhanced DocType Classification and Auto-Fix"
app_email = "fcrm@amb-wellness.com"
app_license = "mit"
app_version = "5.2.0"

# Required apps
required_apps = ["frappe"]

# App Migrator Commands
from . import commands as app_migrator_commands
commands = app_migrator_commands.commands
