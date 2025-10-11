app_name = "app_migrator"
app_title = "App Migrator Ultimate"
app_publisher = "Frappe Community"
app_description = "Ultimate Frappe App Migration System v5.0.4 with Enhanced DocType Classification"
app_email = "fcrm@amb-wellness.com"
app_license = "mit"
app_version = "5.0.4"

# Required apps
required_apps = ["frappe"]

# Bench Commands
commands = [
    {
        "cmd": "migrate-app",
        "callable": "app_migrator.commands"
    }
]
