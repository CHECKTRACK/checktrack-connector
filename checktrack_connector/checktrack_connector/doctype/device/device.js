// Copyright (c) 2025, satat tech llp and contributors
// For license information, please see license.txt

frappe.ui.form.on('Device', {
    validate: function(frm) {
        const today = frappe.datetime.get_today();
        // Check if AMC Expiry Date is past and clear AMC field
        if (frm.doc.amc_expiry_date && today > frm.doc.amc_expiry_date) {
            frm.doc.amc = null; // Clear AMC field
            frappe.msgprint(`AMC expired for Device with Serial No: ${frm.doc.serial_no}. Clearing AMC.`);
        }
    }
});
