// Copyright (c) 2025, satat tech llp and contributors
// For license information, please see license.txt

frappe.ui.form.on('Task Type', {
    refresh: function(frm) {
        frappe.call({
            method: "checktrack_connector.checktrack_connector.doctype.linked_doctype.linked_doctype.get_filtered_doctypes",
            callback: function(response) {
                if (response.message) {
                    const filtered_doctypes = response.message.map(dt => dt.name);

                    frm.set_query('link_doctype', () => {
                        return {
                            filters: [['name', 'in', filtered_doctypes]]
                        };
                    });
                }
            }
        });
    }
});

