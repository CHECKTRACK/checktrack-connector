// Copyright (c) 2025, satat tech llp and contributors
// For license information, please see license.txt

frappe.ui.form.on('Onboard Tenant Authentication', {
    refresh: function (frm) {
        if (!frm.is_new()) {
            
            frm.remove_custom_button('Onboard Tenant');
            
            check_tenant_exists(frm, function(exists) {
                if (exists) {
                    
                    frm.fields.forEach(field => {
                        frm.set_df_property(field.df.fieldname, 'hidden', true);
                    });
                    frm.dashboard.clear_headline();
                    frm.dashboard.set_headline(
                        `<div class="alert alert-success" style="margin-bottom: 0px;">
                            <strong>${__("This tenant is already connected to Checktrack")}</strong>
                        </div>`
                    );
                    frm.set_indicator(__('Connected to Frappe'), 'green');
                    
                } else {
                    
                    frm.fields.forEach(field => {
                        frm.set_df_property(field.df.fieldname, 'hidden', false);
                    });
                    frm.dashboard.clear_headline();
                    frm.add_custom_button(__('Onboard Tenant'), function () {
                        
                        if (!frm.doc.email || !frm.doc.password) {
                            frappe.msgprint(__('Please fill in all required fields before onboarding.'), __('Validation Error'));
                            return;
                        }
                        
                        if (!frm.is_dirty()) {
                            proceed_with_onboarding(frm);
                        } else {
                            frm.save()
                                .then(() => {
                                    proceed_with_onboarding(frm);
                                })
                                .catch(error => {
                                    frappe.msgprint(__('Something went wrong'));
                                });
                        }
                    }).addClass('btn-primary');
                }
            });
        }
    },
    
    email: function(frm) {
        if (frm.doc.email && frm.doc.password) {
            frm.trigger('refresh');
        }
    },
    
    password: function(frm) {
        if (frm.doc.email && frm.doc.password) {
            frm.trigger('refresh');
        }
    }
});

function proceed_with_onboarding(frm) {
    check_tenant_exists(frm, function(exists) {    
        frappe.call({
            method: 'checktrack_connector.api.on_board_tenant_authentication',
            args: {
                email: frm.doc.email,
                password: frm.doc.password
            },
            callback: function (response) {
                if (response.message) {
                    if (response.message.is_fully_onboarded) {
                        frappe.msgprint(__('Tenant is successfully onboarded with team members.'));
                        frm.reload_doc();
                    } else {
                        frappe.msgprint(__('Tenant onboarded successfully!'));
                        frm.reload_doc();
                    }
                } else {
                    frappe.msgprint(__('Failed to onboard tenant!'));
                }
            }
        });
    });
}

function check_tenant_exists(frm, callback) {
    if (!frm.doc.email || !frm.doc.password) {
        callback(false);
        return;
    }
    
    frappe.call({
        method: 'checktrack_connector.api.check_tenant_exists',
        args: {
            email: frm.doc.email,
            password: frm.doc.password
        },
        callback: function (response) {
            var exists = response.message && response.message.exists;
            
            if (callback) callback(exists);
        }
    });
}



