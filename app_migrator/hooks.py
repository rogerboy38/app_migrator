app_name = "app_migrator"
app_title = "App Migrator"
app_version = "6.0.0"
app_publisher = "Your Team"
app_description = "AI-Powered App Migration Tool"

# REMOVE app_include_js - it's conflicting with frappe's hooks
# app_include_js = {
#     "desk": "public/js/app_migrator.bundle.js"
# }

# Simple scheduler events only
scheduler_events = {
    "daily": ["app_migrator.utils.cleanup_old_sessions"]
}
