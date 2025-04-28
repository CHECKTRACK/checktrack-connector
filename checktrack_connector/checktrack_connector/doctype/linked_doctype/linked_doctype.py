# Copyright (c) 2025, satat tech llp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class LinkedDocType(Document):
    pass

@frappe.whitelist()
def get_filtered_doctypes():
    """Fetch DocTypes only from the CheckTrack Frappe app"""
    doctypes = frappe.get_all(
        "DocType",
        filters={"module": "checktrack_connector"},
        fields=["name"]
    )
    return doctypes
