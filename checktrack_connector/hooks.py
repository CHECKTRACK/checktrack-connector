from frappe import conf
app_name = "checktrack_connector"
app_title = "checktrack_connector"
app_publisher = "satat tech llp"
app_description = "This app will be medium of communication between checktrack app and frappe app while they both will be isolated from each other."
app_email = "app_support@satat.tech"
app_license = "mit"

# Define API URLs as hooks
user_api_url = conf.get("user_api_url")
data_api_url = conf.get("data_api_url")

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "checktrack_connector",
# 		"logo": "/assets/checktrack_connector/logo.png",
# 		"title": "checktrack_connector",
# 		"route": "/checktrack_connector",
# 		"has_permission": "checktrack_connector.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/checktrack_connector/css/checktrack_connector.css"
# app_include_js = "/assets/checktrack_connector/js/checktrack_connector.js"

# include js, css files in header of web template
# web_include_css = "/assets/checktrack_connector/css/checktrack_connector.css"
# web_include_js = "/assets/checktrack_connector/js/checktrack_connector.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "checktrack_connector/public/scss/website"

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
# app_include_icons = "checktrack_connector/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "checktrack_connector.utils.jinja_methods",
# 	"filters": "checktrack_connector.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "checktrack_connector.install.before_install"
# after_install = "checktrack_connector.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "checktrack_connector.uninstall.before_uninstall"
# after_uninstall = "checktrack_connector.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "checktrack_connector.utils.before_app_install"
# after_app_install = "checktrack_connector.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "checktrack_connector.utils.before_app_uninstall"
# after_app_uninstall = "checktrack_connector.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "checktrack_connector.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Task": "checktrack_connector.checktrack_connector.doctype.task.task.get_permission_query_conditions",
# }

# has_permission = {
# 	"Task": "checktrack_connector.checktrack_connector.doctype.task.task.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"checktrack_connector.tasks.all"
# 	],
# 	"daily": [
# 		"checktrack_connector.tasks.daily"
# 	],
# 	"hourly": [
# 		"checktrack_connector.tasks.hourly"
# 	],
# 	"weekly": [
# 		"checktrack_connector.tasks.weekly"
# 	],
# 	"monthly": [
# 		"checktrack_connector.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "checktrack_connector.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "checktrack_connector.event.get_events"
# }

doc_events = {
    "Task": {
       "on_update": "checktrack_connector.sync.sync_or_update_task_in_mongo",
       "on_submit": "checktrack_connector.sync.handle_task_submit",
       "on_cancel": "checktrack_connector.sync.handle_task_cancel"
    },
    "Project": {
       "on_update": "checktrack_connector.sync.sync_or_update_project_in_mongo"
    },
    "*": {
        "on_request": "checktrack_connector.utils.validate_cors",
    },
    "Maintenance Schedule": {
        "on_submit": [
           "checktrack_connector.checktrack_connector.doctype.maintenance_schedule.maintenance_schedule.create_schedule_logs",
        ]
    },
    "User": {
        "after_insert": "checktrack_connector.user.generate_api_credentials"
    },
    "Address": {
        "on_update": "checktrack_connector.hook.address_hooks.update_customer_primary_address"
    }
}

override_whitelisted_methods = {
    "frappe.utils.handle_preflight": "checktrack_connector.utils.handle_preflight",
}

after_request = ["checktrack_connector.utils.add_cors_headers"]


#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "checktrack_connector.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["checktrack_connector.jwt_middleware.authenticate_jwt_token"]
# after_request = ["checktrack_connector.utils.after_request"]

# Job Events
# ----------
# before_job = ["checktrack_connector.utils.before_job"]
# after_job = ["checktrack_connector.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"checktrack_connector.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

