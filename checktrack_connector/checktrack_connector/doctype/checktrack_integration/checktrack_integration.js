// Copyright (c) 2025, satat tech llp and contributors
// For license information, please see license.txt

frappe.ui.form.on('CheckTrack Integration', {
    refresh: function (frm) {
        if (!frm.is_new()) {
            
            frm.remove_custom_button('Connect');
            
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
                    frm.add_custom_button(__('Connect'), function () {
                        
                        if (!frm.doc.email || !frm.doc.password) {
                            frappe.msgprint(__('Please fill in all required fields before CheckTrack intergration.'), __('Validation Error'));
                            return;
                        }
                        
                        var $btn = $(this);
                        var original_text = $btn.text();
                        $btn.prop('disabled', true);
                        $btn.html(`<i class="fa fa-spinner fa-spin"></i> ${__("Connecting...")}`);
                        
                        frm.fields.forEach(field => {
                            frm.set_df_property(field.df.fieldname, 'read_only', true);
                        });
                        
                        // Define how to reenable everything
                        const enable_form = function() {
                            $btn.prop('disabled', false);
                            $btn.html(original_text);
                            frm.enable_save();
                            
                            frm.fields.forEach(field => {
                                frm.set_df_property(field.df.fieldname, 'read_only', false);
                            });
                        };
                        
                        new Promise((resolve, reject) => {
                            if (frm.is_dirty()) {
                                frm.save()
                                    .then(() => {
                                        resolve();
                                    })
                                    .catch(reject);
                            } else {
                                resolve();
                            }
                        })
                        .then(() => {
                            return new Promise((resolve, reject) => {
                                frappe.call({
                                    method: 'checktrack_connector.api.check_tenant_exists',
                                    args: {
                                        email: frm.doc.email,
                                        password: frm.raw_password || frm.doc.password
                                    },
                                    callback: function(response) {
                                        resolve(response.message && response.message.exists);
                                    },
                                    error: function(err) {
                                        reject(err);
                                    }
                                });
                            });
                        })
                        .then((exists) => {
                            return new Promise((resolve, reject) => {
                                frappe.call({
                                    method: 'checktrack_connector.api.checktrack_integration',
                                    args: {
                                        email: frm.doc.email,
                                        password: frm.raw_password || frm.doc.password
                                    },
                                    callback: function(response) {
                                        resolve(response);
                                    },
                                    error: function(err) {
                                        reject(err);
                                    }
                                });
                            });
                        })
                        .then((response) => {
                            enable_form();
                            
                            if (response.message) {
                                if (response.message.is_fully_integration) {
                                    frappe.msgprint(__('Cecktrack successfully integration.'));
                                    frm.reload_doc();
                                }
                            } else {
                                frappe.msgprint(__('Failed to integrat!'));
                            }
                        })
                        .catch((error) => {
                            // Error case
                            console.error(error);
                            enable_form();
                            frappe.msgprint(__('Connection failed: ') + (error.message || ''));
                        });
                        
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
        frm.raw_password = frm.fields_dict.password.input.value;
        
        if (frm.doc.email && frm.doc.password) {
            frm.trigger('refresh');
        }
    },
});

function check_tenant_exists(frm, callback) {
    if (!frm.doc.email || !frm.doc.password) {
        callback(false);
        return;
    }
    
    frappe.call({
        method: 'checktrack_connector.api.check_tenant_exists',
        args: {
            email: frm.doc.email,
            password: frm.raw_password || frm.doc.password
        },
        callback: function (response) {
            var exists = response.message && response.message.exists;
            
            if (callback) callback(exists);
        }
    });
}



