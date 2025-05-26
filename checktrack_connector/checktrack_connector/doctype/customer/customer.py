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

			if not frappe.db.exists("Customer Items", {"serial_no": item.serial_no}):
				customer_items = frappe.new_doc("Customer Items")
				customer_items.serial_no = item.serial_no
				customer_items.item_code = item.item_code
				customer_items.item_name = item.item_name
				customer_items.amc = item.amc
				customer_items.customer = self.name
				customer_items.insert(ignore_permissions=True)
				frappe.logger().info(f"Customer Items created for Serial No: {item.serial_no}, Customer: {self.name}")
			else:
				frappe.logger().info(f"Customer Items already exists for Serial No: {item.serial_no}, skipping creation.")
