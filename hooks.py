app_name = "app_migrator"
app_title = "App Migrator"
app_version = "5.5.3"
app_publisher = "Frappe Community"
app_description = "App Migration Toolkit"
app_icon = "octicon octicon-rocket"
app_color = "blue"
app_email = "community@frappe.io"
app_license = "MIT"

app_include_css = "/assets/app_migrator/css/app_migrator.css"
app_include_js = "/assets/app_migrator/js/app_migrator.js"

scheduler_events = {
    "daily": [
        "app_migrator.utils.cleanup_old_sessions"
    ]
}

fixtures = []

# Frappe v15 automatically discovers commands from app/commands/ modules
# No need for get_app_commands function
