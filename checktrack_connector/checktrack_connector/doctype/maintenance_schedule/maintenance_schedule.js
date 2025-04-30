// Copyright (c) 2025, Satat Tech LLP and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("checktrack_connector.maintenance");

frappe.ui.form.on("Maintenance Schedule", {

	onload: function (frm) {
		if (!frm.doc.status) {
			frm.set_value({ status: "Draft" });
		}
		if (frm.doc.__islocal) {
			frm.set_value({ transaction_date: frappe.datetime.get_today() });
		}
	},
	refresh: function (frm) {
		setTimeout(() => {
			frm.toggle_display("generate_schedule", !(frm.is_new() || frm.doc.docstatus));
			frm.toggle_display("schedule", !frm.is_new());
		}, 10);
	},

    customer: function(frm) {
        // Set filter for the items table's serial_no field
        frm.fields_dict.items.grid.get_field('serial_no').get_query = function(doc, cdt, cdn) {
            var child = locals[cdt][cdn];
            return {
                filters: {
                    'customer': frm.doc.customer
                }
            };
        };
        
        // Refresh the items table to apply the filter
        if(frm.doc.items && frm.doc.items.length > 0) {
            frm.refresh_field('items');
        }
    }
});

