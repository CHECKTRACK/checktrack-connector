frappe.ui.form.on("Task", {
    onload: async function(frm) {
        // Initialize pending status changes storage if it doesn't exist
        if (!frappe._task_pending_status_changes) {
            frappe._task_pending_status_changes = {};
        }
        
        // Get all task type names (these are the doctype names stored in Task Type)
        const task_types = await frappe.db.get_list('Task Type', {
            fields: ['name'],
            pluck: 'name'
        });
        
        // Remove 'Task' from the list if it exists
        const filtered_task_types = (task_types || []).filter(type => type !== 'Task');
        
        // Set query filter for type field to show only doctypes present in Task Type (excluding 'Task')
        frm.set_query('type', function() {
            return {
                filters: [
                    ['DocType', 'name', 'in', filtered_task_types]
                ]
            };
        });

        // Set query for task_type dynamic link to show no existing options (only "Create new" will appear)
        frm.set_query('task_type_doc', function() {
            if (frm.doc.type) {
                return {
                    filters: [
                        [frm.doc.type, 'name', '=', 'null*'] // This ensures no records match
                    ]
                };
            }
            return {};
        });
    },

    refresh(frm) {
        render_status_ui(frm);
        // Set field properties based on type field
        set_task_type_doc_requirements(frm);
    },

    workflow_status(frm) {
        render_status_ui(frm);
    },

    type(frm) {
        render_status_ui(frm); // re-render when type changes
        
        // Set field requirements when type changes
        set_task_type_doc_requirements(frm);
        
        // Clear task_type_doc if type is cleared
        if (!frm.doc.type) {
            frm.set_value('task_type_doc', '');
        }
        
        // Re-apply the query filter when type changes
        frm.set_query('task_type_doc', function() {
            if (frm.doc.type) {
                return {
                    filters: [
                        [frm.doc.type, 'name', '=', 'null*'] // This ensures no records match
                    ]
                };
            }
            return {};
        });
    },

    validate: function(frm) {
        // Validation: if type is selected, task_type_doc must also be selected
        if (frm.doc.type && !frm.doc.task_type_doc) {
            frappe.msgprint(__('Please select Task Type Doc when Type is selected'));
            frappe.validated = false;
        }
    }
});

function set_task_type_doc_requirements(frm) {
    // Set task_type_doc as required if type is selected
    if (frm.doc.type) {
        frm.set_df_property('task_type_doc', 'reqd', 1);
        frm.set_df_property('task_type_doc', 'bold', 1);
    } else {
        frm.set_df_property('task_type_doc', 'reqd', 0);
        frm.set_df_property('task_type_doc', 'bold', 0);
    }
}

function get_task_key(frm) {
    // Create a unique key for this task record
    return frm.doc.name || `new_${frm.doc.doctype}_${Date.now()}`;
}

function get_pending_status_change(frm) {
    // Initialize storage if it doesn't exist
    if (!frappe._task_pending_status_changes) {
        frappe._task_pending_status_changes = {};
    }
    
    const task_key = get_task_key(frm);
    return frappe._task_pending_status_changes[task_key] || null;
}

function set_pending_status_change(frm, status) {
    // Initialize storage if it doesn't exist
    if (!frappe._task_pending_status_changes) {
        frappe._task_pending_status_changes = {};
    }
    
    const task_key = get_task_key(frm);
    if (status) {
        frappe._task_pending_status_changes[task_key] = status;
    } else {
        delete frappe._task_pending_status_changes[task_key];
    }
}

function render_status_ui(frm) {
    const wrapper_id = 'custom-status-overview-wrapper';
    let wrapper = $(`#${wrapper_id}`);
    if (!wrapper.length) {
        frm.dashboard.add_section(`
            <div id="${wrapper_id}" style="padding-top: 12px;"></div>
        `, __("Status Overview"));
        wrapper = $(`#${wrapper_id}`);
    }
    wrapper.empty();

    // If no type selected, use "Task" as default type
    const task_type = frm.doc.type || "Task";

    // Call server to get status list based on selected type (or "Task" if no type selected)
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Task Type",
            filters: {
                name: task_type
            },
            fields: ["name"],
            limit: 1
        },
        callback: function (res) {
            const doc = res.message?.[0];
            if (!doc) {
                render_status_dropdown(wrapper, frm, ['Pending'], []);
                return;
            }
            
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Task Type",
                    name: doc.name
                },
                callback: function (r) {
                    const status_flow = r.message.status_flow || [];
                    const all_statuses = status_flow.map(row => row.workflow_status);
                    
                    if (!all_statuses.length) {
                        render_status_dropdown(wrapper, frm, ['Pending'], []);
                        return;
                    }

                    // Get valid next statuses based on current status
                    const current_status = frm.doc.workflow_status;
                    let valid_next_statuses = [];

                    if (current_status) {
                        // Find all rows where workflow_status matches current status
                        const matching_rows = status_flow.filter(row => row.workflow_status === current_status);
                        
                        // Get all possible next statuses and split comma-separated values
                        valid_next_statuses = matching_rows
                            .map(row => row.workflow_status_change_to)
                            .filter(status => status) // Remove empty values
                            .flatMap(status => status.split(',')) // Split comma-separated values
                            .map(status => status.trim()) // Remove whitespace
                            .map(status => status.replace(/['"]/g, '')) // Remove quotes
                            .filter(status => status); // Remove empty strings
                        
                        // Remove duplicates
                        valid_next_statuses = [...new Set(valid_next_statuses)];
                        
                        // Always include current status as an option
                        if (!valid_next_statuses.includes(current_status)) {
                            valid_next_statuses.unshift(current_status);
                        }
                    } else {
                        // If no current status, show all available statuses
                        // Or you can set a default starting status here
                        valid_next_statuses = all_statuses;
                        
                        // Alternative: Set first status as default
                        // valid_next_statuses = [all_statuses[0]];
                    }

                    render_status_dropdown(wrapper, frm, all_statuses, valid_next_statuses);
                }
            });
        }
    });
}

function render_status_dropdown(wrapper, frm, all_statuses, valid_next_statuses) {
    const is_submitted = frm.doc.docstatus === 1;
    
    // Use valid_next_statuses for dropdown options, fallback to all_statuses if empty
    const dropdown_options = valid_next_statuses.length > 0 ? valid_next_statuses : all_statuses;
    
    // Get the pending status change for this specific task
    const pending_status_change = get_pending_status_change(frm);
    
    const status_display = `
        <div style="display: flex; align-items: center; gap: 16px;">
            <div style="
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background-color: #d1d1d1;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                color: #fff;
                font-size: 14px;
            ">
                ${frm.doc.workflow_status ? frm.doc.workflow_status.charAt(0).toUpperCase() : '-'}
            </div>
            <div>
                <div style="font-weight: 600; font-size: 14px;">
                    Current Status: ${frm.doc.workflow_status || 'Not Set'}
                </div>
                <div style="font-size: 12px; color: #888;">
                    Last Updated: ${frappe.datetime.get_datetime_as_string(frm.doc.modified)}
                </div>

                ${!is_submitted ? `
                <div style="margin-top: 8px;">
                    <select id="workflow_status-dropdown" style="padding: 6px 10px; border-radius: 4px; border: 1px solid #ccc;">
                        ${dropdown_options.map(s => `
                            <option value="${s}" ${s === (pending_status_change || frm.doc.workflow_status) ? "selected" : ""}>${s}</option>
                        `).join('')}
                    </select>
                    <button id="apply-status-btn" style="
                        margin-left: 8px;
                        padding: 6px 12px;
                        background-color: #007bff;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        ${!pending_status_change ? 'display: none;' : ''}
                    ">Save</button>
                </div>` : ''}
            </div>
        </div>
    `;
    wrapper.html(status_display);

    if (!is_submitted) {
        setTimeout(() => {
            $('#workflow_status-dropdown').on('change', function () {
                const selected_status = $(this).val();
                const current_status = frm.doc.workflow_status;
                
                if (selected_status !== current_status) {
                    // Store the pending change for this specific task
                    set_pending_status_change(frm, selected_status);
                    
                    // Show apply button
                    $('#apply-status-btn').show();
                    
                    
                } else {
                    // Reset if user selects the current status
                    set_pending_status_change(frm, null);
                    $('#apply-status-btn').hide();
                }
            });
            
            $('#apply-status-btn').on('click', function() {
                const pending_change = get_pending_status_change(frm);
                if (pending_change) {
                    // Apply the pending status change
                    frm.set_value('workflow_status', pending_change);
                    
                    // Save the form
                    frm.save().then(() => {
                        frappe.show_alert(`Status successfully changed to "${pending_change}"`);
                        set_pending_status_change(frm, null);
                        
                        // Re-render the UI after save
                        setTimeout(() => {
                            render_status_ui(frm);
                        }, 500);
                    });
                }
            });
        }, 100);
    }
}