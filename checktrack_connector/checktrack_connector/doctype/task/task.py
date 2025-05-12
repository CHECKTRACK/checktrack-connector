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
	if user == "Administrator":
		return ""

	# Match Employee by work_email
	employee = frappe.db.get_value("Employee", {"work_email": user}, "name")
	if employee:
		return f"`tabTask`.`assign_to` = '{employee}'"
	else:
		return "1=0"  # Deny access if no employee found

def has_permission(doc, user):
	if user == "Administrator":
		return True

	employee = frappe.db.get_value("Employee", {"work_email": user}, "name")
	return doc.assign_to == employee