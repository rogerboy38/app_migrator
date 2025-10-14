app_name = "app_migrator"
app_title = "App Migrator"
app_version = "6.1.0"
app_publisher = "Roger Boy"
app_description = "AI-Powered App Migration Tool"

# Command registration - CRITICAL for bench commands
sounds = [
    {"name": "migrate-app", "src": "/assets/app_migrator/sounds/migrate-app.wav"}
]

# Scheduler events
scheduler_events = {
    "daily": ["app_migrator.utils.cleanup_old_sessions"]
}

# Include JS assets
app_include_js = "/assets/app_migrator/js/app_migrator.js"

# Documentation
documentation_url = "https://github.com/rogerboy38/app_migrator"
