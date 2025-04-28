# Copyright (c) 2025, satat tech llp and contributors
# For license information, please see license.txt

# import frappe
from frappe.utils.nestedset import NestedSet
from frappe.model.document import Document

class Employee(NestedSet):
    def validate(self):
        first_name = self.first_name or ''
        last_name = self.last_name or ''
        self.employee_name = f"{first_name} {last_name}".strip()
