from . import __version__ as version

app_name = "app_migrator"
app_title = "App Migrator Ultimate v5.5.3 with Auto-Fix & REST API"
app_publisher = "Frappe Community"
app_description = "Ultimate Frappe App Migration System v5.5.3 with Enhanced DocType Classification, Auto-Fix, and REST API"
app_email = "fcrm@amb-wellness.com"
app_license = "mit"
app_version = version

# Required apps
required_apps = ["frappe"]

# App Migrator Commands
from . import commands as app_migrator_commands
commands = app_migrator_commands.commands
