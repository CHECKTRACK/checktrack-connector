# Copyright (c) 2025, satat tech llp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AMCRenewalSetting(Document):
	def on_update(self):
		notifications = {
            "AMC Renewal Customer": self.customer_days,
            "AMC Renewal Owner": self.owner_days
        }

		for notification_name, days in notifications.items():
			if frappe.db.exists("Notification", notification_name):
				notification = frappe.get_doc("Notification", notification_name)
				notification.days_in_advance = days
				notification.save()
			else:
				frappe.msgprint(f"Notification document '{notification_name}' not found.", alert=True)

		frappe.db.commit()