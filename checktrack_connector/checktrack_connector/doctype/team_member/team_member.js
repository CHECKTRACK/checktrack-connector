// Copyright (c) 2025, satat tech llp and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Team Member", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Team Member", {
    first_name: function(frm) {
        set_full_name(frm);
    },
    last_name: function(frm) {
        set_full_name(frm);
    },
    refresh: function(frm) {
        if (!frm.doc.full_name) {
            set_full_name(frm);
        }
    }
});

function set_full_name(frm) {
    const firstName = frm.doc.first_name || '';
    const lastName = frm.doc.last_name || '';
    const fullName = `${firstName} ${lastName}`.trim();
    frm.set_value('full_name', fullName);
}
