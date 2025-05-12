# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import NestedSet

class Task(NestedSet):
	def on_update(self):
		if self.type and self.task_type_doc:
			try:
				# Check if the document exists
				if frappe.db.exists(self.type, self.task_type_doc):
					frappe.db.set_value(self.type, self.task_type_doc, "status", self.status)
					frappe.log_error(
						title="Task Sync Log",
						message=f"Updated {self.type} {self.task_type_doc} status to {self.status} from Task {self.name}"
					)
				else:
					frappe.log_error(
						title="Task Sync Error",
						message=f"Linked document {self.type} {self.task_type_doc} does not exist for Task {self.name}"
					)
			except Exception as e:
				frappe.log_error(
					title="Task Sync Error",
					message=f"Failed to update {self.type} {self.task_type_doc} from Task {self.name}: {frappe.get_traceback()}"
				)
def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or has_unrestricted_role(user):
		return ""

	user_email = frappe.db.get_value("User", user, "email")

	return """exists (
		select 1 from `tabWatchers Table` watcher
		where watcher.parent = `tabTask`.name
		and watcher.employee_email = '{user_email}'
	)""".format(user_email=user_email)

def has_permission(doc, user=None, permission_type=None):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or has_unrestricted_role(user):
		return True

		# Get email of the logged-in user
	user_email = frappe.db.get_value("User", user, "email")

	watchers = doc.get("watchers", [])
	for watcher in watchers:
		if watcher.employee_email == user_email:
			return True

	return False

def has_unrestricted_role(user):
    """Check if the user has any role that grants unrestricted access to all tasks"""

    unrestricted_roles = ["System Manager","Projects User"]

    user_roles = frappe.get_roles(user)

    for role in unrestricted_roles:
        if role in user_roles:
            return True

    return False
