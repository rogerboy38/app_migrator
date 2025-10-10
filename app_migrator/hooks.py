app_name = "app_migrator"
app_title = "App Migrator Ultimate"
app_publisher = "Frappe Community"
app_description = "Ultimate Frappe App Migration System v5.0.0 with Enhanced DocType Classification"
app_email = "fcrm@amb-wellness.com"
app_license = "mit"
app_version = "5.0.0"

# Required apps
required_apps = ["frappe"]

# Bench Commands
# Register CLI commands
# Format: bench --site [site] migrate-app <command>
commands = [
    {
        "cmd": "migrate-app",
        "callable": "app_migrator.commands"
    }
]

# Scheduled Tasks
# ---------------
# scheduler_events = {
#     "daily": [
#         "app_migrator.tasks.daily"
#     ]
# }

# Testing
# -------
# before_tests = "app_migrator.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#     "frappe.desk.doctype.event.event.get_events": "app_migrator.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#     "Task": "app_migrator.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["app_migrator.utils.before_request"]
# after_request = ["app_migrator.utils.after_request"]

# Job Events
# ----------
# before_job = ["app_migrator.utils.before_job"]
# after_job = ["app_migrator.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#     {
#         "doctype": "{doctype_1}",
#         "filter_by": "{filter_by}",
#         "redact_fields": ["{field_1}", "{field_2}"],
#         "partial": 1,
#     },
#     {
#         "doctype": "{doctype_2}",
#         "filter_by": "{filter_by}",
#         "partial": 1,
#     },
#     {
#         "doctype": "{doctype_3}",
#         "strict": False,
#     },
#     {
#         "doctype": "{doctype_4}"
#     }
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#     "app_migrator.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
#     "Logging DocType Name": 30  # days to retain logs
# }
