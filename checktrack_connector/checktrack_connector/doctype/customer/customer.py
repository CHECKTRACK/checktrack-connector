# Copyright (c) 2025, satat tech llp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import set_name_by_naming_series
from frappe.utils import nowdate


class Customer(Document):
	def autoname(self):
		set_name_by_naming_series(self)
		self.customer_id = self.name

	def validate(self):
		today = nowdate()
		for item in self.customer_items:

			if not frappe.db.exists("Device", {"serial_no": item.serial_no}):
				device = frappe.new_doc("Device")
				device.serial_no = item.serial_no
				device.item_code = item.item_code
				device.item_name = item.item_name
				device.amc = item.amc
				device.customer = self.name
				device.insert(ignore_permissions=True)
				frappe.logger().info(f"Device created for Serial No: {item.serial_no}, Customer: {self.name}")
			else:
				frappe.logger().info(f"Device already exists for Serial No: {item.serial_no}, skipping creation.")
