from . import __version__ as version

app_name = "app_migrator"
app_title = "App Migrator"
app_publisher = "Frappe Community"
app_description = "Frappe App Migration Toolkit"
app_email = "fcrm@amb-wellness.com"
app_license = "mit"
app_icon = "octicon octicon-rocket"
app_color = "blue"

# Includes in desktop
app_include_css = []
app_include_js = []

# Boot includes
boot_session = []
web_include_js = []
web_include_css = []

# Fixtures
fixtures = []

# Scheduled Tasks
scheduler_events = {}

# Testing
before_tests = []

# Frappe auto-discovers commands from commands module
# Remove the custom get_commands function - let Frappe handle it automatically
