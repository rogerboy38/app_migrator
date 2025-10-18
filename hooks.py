"""
Hooks for App Migrator - V6.1.0
Fixed version without scheduler_events crash
"""

app_name = "app_migrator"
app_title = "App Migrator"
app_publisher = "Roger Boy"
app_description = "Advanced Frappe App Migration Tool"
app_email = "your-email@example.com"
app_license = "MIT"

# Use string version to avoid import issues
app_version = "6.1.0"

# Includes in <head>
# web_include_css = "/assets/app_migrator/css/app_migrator.css"
# web_include_js = "/assets/app_migrator/js/app_migrator.js"

# include js, css files in header of desk.html
app_include_css = "/assets/app_migrator/css/app_migrator.css"
app_include_js = "/assets/app_migrator/js/app_migrator.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "app_migrator/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "app_migrator/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#   "Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#   "methods": "app_migrator.utils.jinja_methods",
#   "filters": "app_migrator.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "app_migrator.install.before_install"
# after_install = "app_migrator.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "app_migrator.uninstall.before_uninstall"
# after_uninstall = "app_migrator.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "app_migrator.utils.before_app_install"
# after_app_install = "app_migrator.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "app_migrator.utils.before_app_uninstall"
# after_app_uninstall = "app_migrator.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "app_migrator.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#   "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#   "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#   "ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#   "*": {
#     "on_update": "method",
#     "on_cancel": "method",
#     "on_trash": "method"
#   }
# }

# Scheduled Tasks
# ---------------

# REMOVED: scheduler_events causing crash loop
# scheduler_events = {
#     "daily": [
#         "app_migrator.utils.cleanup_old_sessions"
#     ]
# }

fixtures = []

# Frappe v15 automatically discovers commands from app/commands/ modules
# No need for get_app_commands function
