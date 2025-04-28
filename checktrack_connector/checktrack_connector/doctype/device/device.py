# Copyright (c) 2025, satat tech llp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class Device(Document):
    def validate(self):
        today = nowdate()
        # Check if AMC Expiry Date is past and clear AMC field
        if self.amc_expiry_date and self.amc_expiry_date < today:
            self.amc = None  # or '' if AMC is a Data field
            frappe.msgprint(f"AMC expired for Device with Serial No: {self.serial_no}. Clearing AMC.")
