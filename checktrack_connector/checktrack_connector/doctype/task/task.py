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
