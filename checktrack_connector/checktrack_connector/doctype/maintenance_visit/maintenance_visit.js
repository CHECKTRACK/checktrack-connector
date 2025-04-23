// Copyright (c) 2025, Satat Tech LLP and contributors
// For license information, please see license.txt

frappe.provide("checktrack_connector.maintenance");

frappe.ui.form.on("Maintenance Visit", {
	setup: function (frm) {
		frm.set_query("contact_person", erpnext.queries.contact_query);
		frm.set_query("customer_address", erpnext.queries.address_query);
		frm.set_query("customer", erpnext.queries.customer);
	},

	customer: function (frm) {
		erpnext.utils.get_party_details(frm);
	},

	customer_address: function (frm) {
		erpnext.utils.get_address_display(frm, "customer_address", "address_display");
	},

	contact_person: function (frm) {
		erpnext.utils.get_contact_details(frm);
	},
});

checktrack_connector.maintenance.MaintenanceVisit = class MaintenanceVisit extends frappe.ui.form.Controller {
	refresh() {
		frappe.dynamic_link = { doc: this.frm.doc, fieldname: "customer", doctype: "Customer" };
		let me = this;

		if (this.frm.doc.docstatus === 0) {
			this.frm.add_custom_button(__("Maintenance Schedule"), function () {
				if (!me.frm.doc.customer) {
					frappe.msgprint(__("Please select Customer first"));
					return;
				}
				erpnext.utils.map_current_doc({
					method: "checktrack_connector.checktrack_connector.doctype.maintenance_schedule.maintenance_schedule.make_maintenance_visit",
					source_doctype: "Maintenance Schedule",
					target: me.frm,
					setters: {
						customer: me.frm.doc.customer,
					},
					get_query_filters: {
						docstatus: 1,
						company: me.frm.doc.company,
					},
				});
			}, __("Get Items From"));

			this.frm.add_custom_button(__("Warranty Claim"), function () {
				erpnext.utils.map_current_doc({
					method: "checktrack_connector.support.doctype.warranty_claim.warranty_claim.make_maintenance_visit",
					source_doctype: "Warranty Claim",
					target: me.frm,
					date_field: "complaint_date",
					setters: {
						customer: me.frm.doc.customer || undefined,
					},
					get_query_filters: {
						status: ["in", "Open, Work in Progress"],
						company: me.frm.doc.company,
					},
				});
			}, __("Get Items From"));

			this.frm.add_custom_button(__("Sales Order"), function () {
				if (!me.frm.doc.customer) {
					frappe.msgprint(__("Please select Customer first"));
					return;
				}
				erpnext.utils.map_current_doc({
					method: "checktrack_connector.selling.doctype.sales_order.sales_order.make_maintenance_visit",
					source_doctype: "Sales Order",
					target: me.frm,
					setters: {
						customer: me.frm.doc.customer,
					},
					get_query_filters: {
						docstatus: 1,
						company: me.frm.doc.company,
						order_type: me.frm.doc.order_type,
					},
				});
			}, __("Get Items From"));
		}
	}
};

extend_cscript(cur_frm.cscript, new checktrack_connector.maintenance.MaintenanceVisit({ frm: cur_frm }));
