# Copyright (c) 2025, satat tech llp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AMCRenewal(Document):
    def on_update(self):
        """
        Update the 'days_in_advance' field in the Notification document
        when the 'days' field in AMC Renewal is changed.
        """
        notification_name = "AMC Renewal"  # Name of the Notification document
        
        if frappe.db.exists("Notification", notification_name):
            notification = frappe.get_doc("Notification", notification_name)
            notification.days_in_advance = self.days
            notification.save()
            frappe.db.commit()
        else:
            frappe.msgprint(f"Notification document '{notification_name}' not found.", alert=True)