frappe.ui.form.on('Task Type', {
    refresh(frm) {
        // Hide default child tables
        frm.toggle_display('status_flow', false);
        frm.toggle_display('field_mapping', false);

        // If first load, create UI containers only once
        if (!frm.custom_ui_added) {
            frm.custom_ui_added = true;
            // Add containers to the page
            $('<div id="status-flow-ui"></div>').insertAfter(frm.fields_dict.status_flow.$wrapper);
            $('<div id="field-mapping-ui"></div>').insertAfter(frm.fields_dict.field_mapping.$wrapper);
        }

        // Render custom UIs
        render_status_flow(frm);
        render_field_mapping(frm);
    }
});

function render_status_flow(frm) {
    const wrapper = $('#status-flow-ui');
    wrapper.empty();

    wrapper.append('<h4>Status Flow</h4>');

    // Container to hold chips and button horizontally aligned
    const container = $('<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px;"></div>');

    frm.doc.status_flow.forEach((row, idx) => {
        const color = row.color || '#ccc';
        const chip = $(`
            <div class="badge status-flow-chip" style="
                background-color: #f8f9fa;
                color: #6c757d;
                padding: 8px 16px;
                cursor: pointer;
                border: 1px solid #dee2e6;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: all 0.2s ease;
            " data-index="${idx}">
                <b style="color: #495057;">${row.workflow_status}</b>
                <small style="color: #6c757d;">
                    ${row.start_state ? 'Start' : row.working_state ? 'Working' : row.end_state ? 'End' : ''}
                </small>
                <button class="btn btn-link btn-xs remove-btn" style="padding: 0; font-size: 12px; color: #6c757d;">✖</button>
            </div>
        `);
        
        // Add hover effect
        chip.hover(
            function() {
                $(this).css('background-color', '#e9ecef');
            },
            function() {
                $(this).css('background-color', '#f8f9fa');
            }
        );

        // Edit on chip click (but not on remove button)
        chip.click(function(e) {
            if (!$(e.target).hasClass('remove-btn')) {
                edit_status_flow_row(frm, idx);
            }
        });

        // Remove on button click
        chip.find('.remove-btn').click(function(e) {
            e.stopPropagation();
            remove_status_flow_row(frm, idx);
        });

        container.append(chip);
    });

    // Create the Add Status button aligned with chips
    const addButton = $('<button class="btn btn-sm btn-primary" id="add-status-flow-btn" style="height: 36px;">Add Status</button>');
    addButton.click(() => add_status_flow_dialog(frm));

    container.append(addButton);
    wrapper.append(container);
}

// Function to show add/edit dialog
async function show_status_flow_dialog(frm, editIndex = null) {
    if (!frm.doc.task_type) {
        frappe.msgprint('Please select a Task Type first.');
        return;
    }

    let doctype_fields = await frappe.db.get_doc("DocType", frm.doc.task_type);
    let excluded_fieldtypes = [
        "Section Break",
        "Column Break", 
        "HTML",
        "Line Break",
        "Table",
        "Button",
        "Fold"
    ];

    let visible_fields = (doctype_fields.fields || [])
        .filter(f => !f.hidden && !excluded_fieldtypes.includes(f.fieldtype))
        .map(f => f.fieldname);

    let existing_statuses = frm.doc.status_flow.map(row => row.workflow_status);

    // Get existing data if editing
    let existing_data = {};
    if (editIndex !== null) {
        existing_data = frm.doc.status_flow[editIndex];
    }

    let d = new frappe.ui.Dialog({
        title: editIndex !== null ? 'Edit Status' : 'Add Status',
        fields: [
            {fieldtype: 'Data', fieldname: 'workflow_status', label: 'Status', reqd: 1, default: existing_data.workflow_status || ''},
            {fieldtype: 'Color', fieldname: 'color', label: 'Color', default: existing_data.color || ''},
            {fieldtype: 'Section Break'},
            {fieldtype: 'HTML', fieldname: 'visible_fields_html', label: 'Visible Fields'},
            {fieldtype: 'Section Break'},
            {fieldtype: 'HTML', fieldname: 'required_fields_html', label: 'Required Fields'},
            {fieldtype: 'Section Break'},
            {fieldtype: 'HTML', fieldname: 'read_only_fields_html', label: 'Read Only Fields'},
            {fieldtype: 'Section Break'},
            {fieldtype: 'HTML', fieldname: 'workflow_status_change_to_html', label: 'Workflow Status Change To'},
            {fieldtype: 'Section Break'},
            {fieldtype: 'Check', fieldname: 'start_state', label: 'Start', default: existing_data.start_state || 0},
            {fieldtype: 'Check', fieldname: 'working_state', label: 'Working', default: existing_data.working_state || 0},
            {fieldtype: 'Check', fieldname: 'end_state', label: 'End', default: existing_data.end_state || 0},
        ]
    });

    d.show();

    // Create table-based multiselect fields
    const create_table_multiselect = (fieldname, label, options, container_selector, default_values = []) => {
        let selected_values = default_values;
        
        const render_table = () => {
            let html = `
                <div style="margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <label style="font-weight: bold; margin: 0;">${label}</label>
                        <button type="button" class="btn btn-xs btn-default toggle-all-btn" style="font-size: 11px; padding: 2px 8px;">
                            ${selected_values.length === options.length ? 'Remove All' : 'Check All'}
                        </button>
                    </div>
                    <div style="border: 1px solid #d1d8dd; border-radius: 4px; max-height: 200px; overflow-y: auto;">
                        <table class="table table-condensed" style="margin: 0;">
                            <tbody>
            `;
            
            options.forEach(option => {
                const isSelected = selected_values.includes(option);
                html += `
                    <tr style="cursor: pointer; ${isSelected ? 'background-color: #e8f4fd;' : ''}" 
                        data-value="${option}" class="multiselect-row">
                        <td style="padding: 8px 12px; border: none; font-size: 13px;">
                            <input type="checkbox" ${isSelected ? 'checked' : ''} 
                                   style="margin-right: 8px;" class="multiselect-checkbox">
                            ${option}
                        </td>
                    </tr>
                `;
            });
            
            html += `
                            </tbody>
                        </table>
                    </div>
                    <div style="margin-top: 5px; font-size: 12px; color: #6c7680;">
                        Selected: <span class="selected-count">${selected_values.length}</span> items
                    </div>
                </div>
            `;
            
            $(container_selector).html(html);
            
            // Add event handlers for individual rows
            $(container_selector).find('.multiselect-row').click(function(e) {
                e.preventDefault();
                const value = $(this).data('value');
                const checkbox = $(this).find('.multiselect-checkbox');
                
                if (selected_values.includes(value)) {
                    selected_values = selected_values.filter(v => v !== value);
                    checkbox.prop('checked', false);
                    $(this).css('background-color', '');
                } else {
                    selected_values.push(value);
                    checkbox.prop('checked', true);
                    $(this).css('background-color', '#e8f4fd');
                }
                
                $(container_selector).find('.selected-count').text(selected_values.length);
            });
            
            // Handle checkbox clicks
            $(container_selector).find('.multiselect-checkbox').click(function(e) {
                e.stopPropagation();
                $(this).closest('.multiselect-row').click();
            });

            // Toggle All button (smart check/uncheck all)
            $(container_selector).find('.toggle-all-btn').click(function(e) {
                e.preventDefault();
                if (selected_values.length === options.length) {
                    // If all are selected, remove all
                    selected_values = [];
                } else {
                    // If not all are selected, select all
                    selected_values = [...options];
                }
                render_table(); // Re-render to update UI and button text
            });
        };
        
        render_table();
        
        return {
            get_values: () => selected_values,
            set_values: (values) => {
                selected_values = values || [];
                render_table();
            }
        };
    };

    // Parse existing values for editing
    const parseExistingValues = (str) => {
        if (!str) return [];
        return str.split(',').map(s => s.trim().replace(/^'|'$/g, ''));
    };

    // Create the multiselect controls after dialog is rendered
    setTimeout(() => {
        const visible_fields_ctrl = create_table_multiselect(
            'visible_fields', 
            'Visible Fields', 
            visible_fields, 
            d.$wrapper.find('[data-fieldname="visible_fields_html"]'),
            parseExistingValues(existing_data.visible_fields)
        );
        
        const required_fields_ctrl = create_table_multiselect(
            'required_fields', 
            'Required Fields', 
            visible_fields, 
            d.$wrapper.find('[data-fieldname="required_fields_html"]'),
            parseExistingValues(existing_data.required_fields)
        );
        
        const read_only_fields_ctrl = create_table_multiselect(
            'read_only_fields', 
            'Read Only Fields', 
            visible_fields, 
            d.$wrapper.find('[data-fieldname="read_only_fields_html"]'),
            parseExistingValues(existing_data.read_only_fields)
        );
        
        const workflow_status_change_to_ctrl = create_table_multiselect(
            'workflow_status_change_to', 
            'Workflow Status Change To', 
            existing_statuses, 
            d.$wrapper.find('[data-fieldname="workflow_status_change_to_html"]'),
            parseExistingValues(existing_data.workflow_status_change_to)
        );

        // Store controls for later access
        d.multiselect_controls = {
            visible_fields_ctrl,
            required_fields_ctrl,
            read_only_fields_ctrl,
            workflow_status_change_to_ctrl
        };
    }, 100);

    d.set_primary_action(editIndex !== null ? 'Update' : 'Add', () => {
        let data = d.get_values();

        if (!data.workflow_status) {
            frappe.msgprint('Status is required!');
            return;
        }

        // Get values from multiselect controls
        const controls = d.multiselect_controls;
        if (controls) {
            const visible_vals = controls.visible_fields_ctrl.get_values();
            const required_vals = controls.required_fields_ctrl.get_values();
            const readonly_vals = controls.read_only_fields_ctrl.get_values();
            const workflow_vals = controls.workflow_status_change_to_ctrl.get_values();

            data.visible_fields = visible_vals.length ? visible_vals.map(v => `'${v}'`).join(", ") : "";
            data.required_fields = required_vals.length ? required_vals.map(v => `'${v}'`).join(", ") : "";
            data.read_only_fields = readonly_vals.length ? readonly_vals.map(v => `'${v}'`).join(", ") : "";
            data.workflow_status_change_to = workflow_vals.length ? workflow_vals.map(v => `'${v}'`).join(", ") : "";
        }

        if (editIndex !== null) {
            // Update existing row
            Object.assign(frm.doc.status_flow[editIndex], data);
        } else {
            // Add new row
            frm.add_child('status_flow', data);
        }
        
        frm.refresh_field('status_flow');
        render_status_flow(frm);
        d.hide();
    });
}

// Add status flow dialog (wrapper for add functionality)
function add_status_flow_dialog(frm) {
    show_status_flow_dialog(frm);
}

// Edit status flow row
function edit_status_flow_row(frm, idx) {
    show_status_flow_dialog(frm, idx);
}

// Remove chip implementation
window.remove_status_flow_row = function(frm, idx) {
    frm.doc.status_flow.splice(idx, 1);
    frm.refresh_field('status_flow');
    render_status_flow(frm);
}

function render_field_mapping(frm) {
    const wrapper = $('#field-mapping-ui');
    wrapper.empty();
    // Add spacing above the heading
    wrapper.append('<h4 style="margin-top: 16px; margin-bottom: 12px;">Field Mapping</h4>');

    frm.doc.field_mapping.forEach((row, idx) => {
        const displayTargetField = convertToDisplayValue(row.target_field);
        const displayLabelField = convertToDisplayLabel(row.label_field);
        
        const mappingItem = $(`
            <div class="field-mapping-item" style="
                margin-bottom:6px; 
                padding:8px; 
                border-bottom:1px solid #eee; 
                display: flex; 
                align-items: center; 
                justify-content: space-between;
                cursor: pointer;
                border-radius: 4px;
                transition: all 0.2s ease;
            " data-index="${idx}">
                <div>
                    <b>${displayTargetField}</b> → <b>${displayLabelField}</b> (<i>${row.source_path || 'No path'}</i>) : ${row.label_text || 'No label'}
                </div>
                <button class="btn btn-link btn-xs remove-mapping-btn" style="font-size: 12px; padding: 0; color: #6c757d;">✖</button>
            </div>
        `);

        // Add hover effect
        mappingItem.hover(
            function() {
                $(this).css('background-color', '#f8f9fa');
            },
            function() {
                $(this).css('background-color', 'transparent');
            }
        );

        // Edit on item click (but not on remove button)
        mappingItem.click(function(e) {
            if (!$(e.target).hasClass('remove-mapping-btn')) {
                edit_field_mapping_row(frm, idx);
            }
        });

        // Remove on button click
        mappingItem.find('.remove-mapping-btn').click(function(e) {
            e.stopPropagation();
            remove_field_mapping_row(frm, idx);
        });

        wrapper.append(mappingItem);
    });

    // Add spacing above the button
    wrapper.append('<button class="btn btn-sm btn-primary" id="add-field-mapping-btn" style="margin-bottom: 16px;">Add Field Mapping</button>');

    $('#add-field-mapping-btn').click(() => add_field_mapping_dialog(frm));
}

// Function to show add/edit field mapping dialog
function show_field_mapping_dialog(frm, editIndex = null) {
    // Get existing data if editing
    let existing_data = {};
    if (editIndex !== null) {
        existing_data = frm.doc.field_mapping[editIndex];
    }

    frappe.prompt([
        {
            fieldname:'target_field', 
            label:'Target Field', 
            fieldtype:'Select', 
            options:'Assign To\nFirst\nSecond\nThird', 
            reqd:1, 
            default: existing_data.target_field ? convertToDisplayValue(existing_data.target_field) : ''
        },
        {fieldname:'source_path', label:'Source Path', fieldtype:'Data', default: existing_data.source_path || ''},
        {fieldname:'label_text', label:'Label Text', fieldtype:'Data', default: existing_data.label_text || ''},
    ], (values) => {
        // Convert display values back to storage format and auto-determine label field
        const storageData = {
            target_field: convertToStorageValue(values.target_field),
            label_field: autoConvertToLabelField(values.target_field),
            source_path: values.source_path,
            label_text: values.label_text
        };

        if (editIndex !== null) {
            // Update existing row
            Object.assign(frm.doc.field_mapping[editIndex], storageData);
        } else {
            // Add new row
            frm.add_child('field_mapping', storageData);
        }
        frm.refresh_field('field_mapping');
        render_field_mapping(frm);
    }, editIndex !== null ? 'Edit Field Mapping' : 'Add Field Mapping');
}

function convertToDisplayValue(storageValue) {
    const mapping = {
        'assign_to_value': 'Assign To',
        'first_value': 'First',
        'second_value': 'Second',
        'third_value': 'Third'
    };
    return mapping[storageValue] || storageValue;
}

function convertToStorageValue(displayValue) {
    const mapping = {
        'Assign To': 'assign_to_value',
        'First': 'first_value',
        'Second': 'second_value',
        'Third': 'third_value'
    };
    return mapping[displayValue] || displayValue;
}

// Auto-convert target field to corresponding label field
function autoConvertToLabelField(displayTargetField) {
    const mapping = {
        'Assign To': 'assign_to_label',
        'First': 'first_label',
        'Second': 'second_label',
        'Third': 'third_label'
    };
    return mapping[displayTargetField] || 'assign_to_label';
}

function convertToDisplayLabel(storageLabel) {
    const mapping = {
        'assign_to_label': 'Assign To Label',
        'first_label': 'First Label',
        'second_label': 'Second Label',
        'third_label': 'Third Label'
    };
    return mapping[storageLabel] || storageLabel;
}

// Add field mapping dialog (wrapper for add functionality)
function add_field_mapping_dialog(frm) {
    show_field_mapping_dialog(frm);
}

// Edit field mapping row
function edit_field_mapping_row(frm, idx) {
    show_field_mapping_dialog(frm, idx);
}

// Remove field mapping row
window.remove_field_mapping_row = function(frm, idx) {
    frm.doc.field_mapping.splice(idx, 1);
    frm.refresh_field('field_mapping');
    render_field_mapping(frm);
}

function getFrappeBadgeClass(color) {
    const map = {
        "#007bff": "badge-primary",
        "#28a745": "badge-success", 
        "#dc3545": "badge-danger",
        "#17a2b8": "badge-info",
        "#ffc107": "badge-warning",
        "#6c757d": "badge-secondary",
        "#343a40": "badge-dark",
    };
    // Basic mapping based on common colors or fallback
    return Object.entries(map).find(([k,v]) => k.toLowerCase() === color.toLowerCase())?.[1] || "badge-secondary";
}