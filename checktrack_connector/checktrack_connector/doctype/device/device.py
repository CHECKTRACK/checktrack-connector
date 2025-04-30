# Copyright (c) 2025, satat tech llp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class Device(Document):
    def clear_expired_amc_in_devices():
    # Fetch all Device records where AMC Expiry Date <= today and AMC is not empty
        devices = frappe.get_all(
            "Device",
            filters={
                "amc_expiry_date": ("<=", nowdate()),
                "amc": ("!=", "")  # Skip already cleared AMC fields
            },
            fields=["name"]
        )

        # Clear the AMC field for expired records
        for device in devices:
            doc = frappe.get_doc("Device", device.name)
            doc.amc = None  # or doc.set("amc", "")
            doc.save(ignore_permissions=True)

        frappe.db.commit()