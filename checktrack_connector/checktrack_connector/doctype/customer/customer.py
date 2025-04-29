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

			if item.amc_expiry_date and item.amc_expiry_date < today:
				item.amc = None
				frappe.msgprint(f"AMC expired for Serial No: {item.serial_no}. Clearing AMC.")

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

	def clear_expired_amc():
		# Fetch all Customer records where AMC Expiry Date <= today and AMC is not empty
		customers = frappe.get_all(
			"Customer",
			filters={
				"amc_expiry_date": ("<=", nowdate()),
				"amc": ("!=", "")  # Skip already cleared AMC fields
			},
			fields=["name"]
		)

		# Clear the AMC field for expired records
		for customer in customers:
			doc = frappe.get_doc("Customer", customer.name)
			doc.amc = None  # or doc.set("amc", "")
			doc.save(ignore_permissions=True)

		frappe.db.commit()	