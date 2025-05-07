# Copyright (c) 2025, satat tech llp and contributors
# For license information, please see license.txt


import frappe
from frappe import _, throw
from frappe.utils import add_days, cint, cstr, date_diff, formatdate, getdate

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.utilities.transaction_base import TransactionBase, delete_events


class MaintenanceSchedule(TransactionBase):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.maintenance.doctype.maintenance_schedule_detail.maintenance_schedule_detail import (
			MaintenanceScheduleDetail,
		)
		from erpnext.maintenance.doctype.maintenance_schedule_item.maintenance_schedule_item import (
			MaintenanceScheduleItem,
		)

		address_display: DF.TextEditor | None
		amended_from: DF.Link | None
		company: DF.Link
		items: DF.Table[MaintenanceScheduleItem]
		naming_series: DF.Literal["MAT-MSH-.YYYY.-"]
		schedules: DF.Table[MaintenanceScheduleDetail]
		status: DF.Literal["", "Draft", "Submitted", "Cancelled"]
		territory: DF.Link | None
		transaction_date: DF.Date
	# end: auto-generated types

	@frappe.whitelist()
	def generate_schedule(self):
		if self.docstatus != 0:
			return
		self.set("schedules", [])
		count = 1
		for d in self.get("items"):
			self.validate_maintenance_detail()
			s_list = []
			s_list = self.create_schedule_list(d.start_date, d.end_date, d.no_of_visits, d.sales_person)
			for i in range(d.no_of_visits):
				child = self.append("schedules")
				child.serial_no = d.serial_no
				child.item_code = d.item_code
				child.item_name = d.item_name
				child.scheduled_date = s_list[i].strftime("%Y-%m-%d")
				child.idx = count
				count = count + 1
				child.sales_person = d.sales_person
				child.employee_id = d.employee_id
				child.employee_name = d.employee_name
				child.customer_name = d.customer_name
				child.customer_email_id = d.customer_email_id
				child.completion_status = "Pending"
				child.item_reference = d.name

	@frappe.whitelist()
	def validate_end_date_visits(self):
		days_in_period = {"Weekly": 7, "Monthly": 30, "Quarterly": 91, "Half Yearly": 182, "Yearly": 365}
		for item in self.items:
			if item.periodicity and item.periodicity != "Random" and item.start_date:
				if not item.end_date:
					if item.no_of_visits:
						item.end_date = add_days(
							item.start_date, item.no_of_visits * days_in_period[item.periodicity]
						)
					else:
						item.end_date = add_days(item.start_date, days_in_period[item.periodicity])

				diff = date_diff(item.end_date, item.start_date) + 1
				no_of_visits = cint(diff / days_in_period[item.periodicity])

				if not item.no_of_visits or item.no_of_visits == 0:
					item.end_date = add_days(item.start_date, days_in_period[item.periodicity])
					diff = date_diff(item.end_date, item.start_date) + 1
					item.no_of_visits = cint(diff / days_in_period[item.periodicity])

				elif item.no_of_visits > no_of_visits:
					item.end_date = add_days(
						item.start_date, item.no_of_visits * days_in_period[item.periodicity]
					)

				elif item.no_of_visits < no_of_visits:
					item.end_date = add_days(
						item.start_date, item.no_of_visits * days_in_period[item.periodicity]
					)

	def on_submit(self):
		if not self.get("schedules"):
			throw(_("Please click on 'Generate Schedule' to get schedule"))
		self.validate_schedule()

		for d in self.get("items"):
			scheduled_date = frappe.db.get_all(
				"Maintenance Schedule Detail",
				{"parent": self.name, "item_code": d.item_code},
				["scheduled_date"],
				as_list=False,
			)

		for item in self.items:
			if item.customer and item.serial_no:
				customer_doc = frappe.get_doc("Customer", item.customer)
				for customer_item in customer_doc.customer_items:
					if customer_item.serial_no == item.serial_no:
						customer_item.amc = self.name
						customer_item.amc_expiry_date = item.end_date
						break
				customer_doc.save()
				frappe.msgprint(f"Updated Customer AMC for {item.customer}")

		for item in self.items:
			if item.serial_no:
				# Find Device by serial_no
				devices = frappe.get_all("Device", filters={"serial_no": item.serial_no}, fields=["name"])
				if not devices:
					frappe.msgprint(f"No Device found with Serial No: {item.device}", raise_exception=True)
					continue
				# Get the first matching Device
				device_name = devices[0]["name"]
				device = frappe.get_doc("Device", device_name)
				device.amc = self.name
				device.amc_expiry_date = item.end_date
				device.save()
				frappe.msgprint(f"Updated AMC and AMC expiry for {device.serial_no}")

		self.db_set("status", "Submitted")

	def create_schedule_list(self, start_date, end_date, no_of_visit, sales_person):
		schedule_list = []
		start_date_copy = start_date
		date_diff = (getdate(end_date) - getdate(start_date)).days
		add_by = date_diff / no_of_visit

		for _visit in range(cint(no_of_visit)):
			if getdate(start_date_copy) < getdate(end_date):
				start_date_copy = add_days(start_date_copy, add_by)
				if len(schedule_list) < no_of_visit:
					schedule_date = self.validate_schedule_date_for_holiday_list(
						getdate(start_date_copy), sales_person
					)
					if schedule_date > getdate(end_date):
						schedule_date = getdate(end_date)
					schedule_list.append(schedule_date)

		return schedule_list

	def validate_schedule_date_for_holiday_list(self, schedule_date, sales_person):
		validated = False

		employee = frappe.db.get_value("Sales Person", sales_person, "employee")
		if employee:
			holiday_list = get_holiday_list_for_employee(employee)
		else:
			holiday_list = frappe.get_cached_value("Company", self.company, "default_holiday_list")

		holidays = frappe.db.sql_list(
			"""select holiday_date from `tabHoliday` where parent=%s""", holiday_list
		)

		if not validated and holidays:
			# max iterations = len(holidays)
			for _i in range(len(holidays)):
				if schedule_date in holidays:
					schedule_date = add_days(schedule_date, -1)
				else:
					validated = True
					break

		return schedule_date

	def validate_dates_with_periodicity(self):
		for d in self.get("items"):
			if d.start_date and d.end_date and d.periodicity and d.periodicity != "Random":
				date_diff = (getdate(d.end_date) - getdate(d.start_date)).days + 1
				days_in_period = {
					"Weekly": 7,
					"Monthly": 30,
					"Quarterly": 90,
					"Half Yearly": 180,
					"Yearly": 365,
				}

				if date_diff < days_in_period[d.periodicity]:
					throw(
						_(
							"Row {0}: To set {1} periodicity, difference between from and to date must be greater than or equal to {2}"
						).format(d.idx, d.periodicity, days_in_period[d.periodicity])
					)

	def validate_maintenance_detail(self):
		if not self.get("items"):
			throw(_("Please enter Maintenance Details first"))

		for d in self.get("items"):
			if not d.item_code:
				throw(_("Please select item code"))
			elif not d.start_date or not d.end_date:
				throw(_("Please select Start Date and End Date for Item {0}").format(d.item_code))
			elif not d.no_of_visits:
				throw(_("Please mention no of visits required"))

			if getdate(d.start_date) >= getdate(d.end_date):
				throw(_("Start date should be less than end date for Item {0}").format(d.item_code))

	def validate_items_table_change(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return
		for prev_item, item in zip(doc_before_save.items, self.items, strict=False):
			fields = [
				"item_code",
				"start_date",
				"end_date",
				"periodicity",
				"sales_person",
				"no_of_visits",
			]
			for field in fields:
				b_doc = prev_item.as_dict()
				doc = item.as_dict()
				if cstr(b_doc[field]) != cstr(doc[field]):
					return True

	def validate_no_of_visits(self):
		return len(self.schedules) != sum(d.no_of_visits for d in self.items)

	def validate(self):
		self.sync_customer_to_items()

		self.validate_end_date_visits()
		self.validate_maintenance_detail()
		self.validate_dates_with_periodicity()
		if not self.schedules or self.validate_items_table_change() or self.validate_no_of_visits():
			self.generate_schedule()

	def on_update(self):
		self.sync_customer_to_items()
		self.db_set("status", "Draft")

	def sync_customer_to_items(self):
		if self.customer and self.customer_name and self.customer_email_id:
			for item in self.get("items", []):
				if self.customer and (not item.customer or item.customer != self.customer):
					item.customer = self.customer
				if self.customer_name and (not item.customer_name or item.customer_name != self.customer_name):
					item.customer_name = self.customer_name
				if self.customer_email_id and (not item.customer_email_id or item.customer_email_id != self.customer_email_id):
					item.customer_email_id = self.customer_email_id

			for schedule in self.get("schedules", []):
				if self.customer and (not schedule.customer or schedule.customer != self.customer):
					schedule.customer = self.customer
				if self.customer_name and (not schedule.customer_name or schedule.customer_name != self.customer_name):
					schedule.customer_name = self.customer_name
				if self.customer_email_id and (not schedule.customer_email_id or schedule.customer_email_id != self.customer_email_id):
					schedule.customer_email_id = self.customer_email_id
					
	def validate_schedule(self):
		item_lst1 = []
		item_lst2 = []
		for d in self.get("items"):
			if d.item_code not in item_lst1:
				item_lst1.append(d.item_code)

		for m in self.get("schedules"):
			if m.item_code not in item_lst2:
				item_lst2.append(m.item_code)

		if len(item_lst1) != len(item_lst2):
			throw(
				_(
					"Maintenance Schedule is not generated for all the items. Please click on 'Generate Schedule'"
				)
			)
		else:
			for x in item_lst1:
				if x not in item_lst2:
					throw(_("Please click on 'Generate Schedule'"))

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		delete_events(self.doctype, self.name)

	def on_trash(self):
		delete_events(self.doctype, self.name)

	@frappe.whitelist()
	def get_pending_data(self, data_type, s_date=None, item_name=None):
		if data_type == "date":
			dates = ""
			for schedule in self.schedules:
				if schedule.item_name == item_name and schedule.completion_status == "Pending":
					dates = dates + "\n" + formatdate(schedule.scheduled_date, "dd-MM-yyyy")
			return dates
		elif data_type == "items":
			items = ""
			for item in self.items:
				for schedule in self.schedules:
					if item.item_name == schedule.item_name and schedule.completion_status == "Pending":
						items = items + "\n" + item.item_name
						break
			return items
		elif data_type == "id":
			for schedule in self.schedules:
				if schedule.item_name == item_name and s_date == formatdate(
					schedule.scheduled_date, "dd-mm-yyyy"
				):
					return schedule.name


def create_schedule_logs(doc, method):
		for row in doc.schedules:
			frappe.msgprint(f"Creating log for Item Code: {row.item_code}")
			
			log = frappe.new_doc("Schedule Log")
			log.serial_no = row.serial_no
			log.item_code = row.item_code
			log.item_name = row.item_name
			log.scheduled_date = row.scheduled_date
			log.actual_date = row.actual_date
			log.assign_to_id = row.employee_id
			log.assign_to = row.employee_name
			log.completion_status = row.completion_status
			log.customer = row.customer
			log.customer_name = row.customer_name
			log.customer_email_id = row.customer_email_id
			log.maintenance_schedule = doc.name
			log.insert()

			if row.employee_id:
				employee = row.employee_id.strip()
				employee = frappe.get_list(
					"Employee",
					filters={"teammember_id": employee},
					fields=["name"],
					limit=1
				)

				if employee:
					emp_doc = frappe.get_doc("Employee", employee[0].name)

					task_row = emp_doc.append("tasks", {})
					task_row.serial_no = row.serial_no
					task_row.item_code = row.item_code
					task_row.item_name = row.item_name
					task_row.scheduled_date = row.scheduled_date
					task_row.actual_date = row.actual_date
					task_row.completion_status = row.completion_status
					task_row.maintenance_schedule = doc.name

					emp_doc.save()
					frappe.msgprint(f"Task added for Employee (id): {employee}")
				else:
					frappe.log_error(f"Employee with id '{employee}' not found.", "Task Creation Failed")