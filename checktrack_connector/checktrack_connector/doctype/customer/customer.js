// Copyright (c) 2025, satat tech llp and contributors
// For license information, please see license.txt

frappe.ui.form.on('Customer', {
    onload: function(frm) {
        frm.fields_dict.customer_items.grid.get_field('serial_no').get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    customer: ''
                }
            };
        };
    },
    validate: function(frm) {
        const today = frappe.datetime.get_today();
        if (frm.doc.customer_items) {
            frm.doc.customer_items.forEach(function(item) {
                if (item.amc_expiry_date && today > item.amc_expiry_date) {
                    item.amc = null;
                    frappe.msgprint(`AMC expired for Serial No: ${item.serial_no}. Clearing AMC.`);
                }
            });
        }
    }
});
