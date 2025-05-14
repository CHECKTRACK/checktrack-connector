# Copyright (c) 2025, satat tech llp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FeedbackForm(Document):
    pass

def after_insert(doc, method):
    if doc.task:
        try:
            task = frappe.get_doc("Task", doc.task)
            
            if task:
                frappe.db.set_value(task.doctype, task.name, "feedback", doc.name)

                frappe.log_error(f"Linked feedback {doc.name} to task {task.name}", "Feedback Link Success")

        except Exception as e:
            frappe.log_error(f"Failed to link feedback {doc.name} to Task {doc.task}: {str(e)}", "Feedback Link Error")