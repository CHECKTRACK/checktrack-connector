frappe.ui.form.on('Task Type', {
    refresh(frm) {
        // Hide default child tables
        frm.toggle_display('status_flow', false);
        frm.toggle_display('task_card', false);

        // If first load, create UI containers only once
        if (!frm.custom_ui_added) {
            frm.custom_ui_added = true;
            // Add containers to the page
            $('<div id="status-flow-ui"></div>').insertAfter(frm.fields_dict.status_flow.$wrapper);
            $('<div id="task-card-ui"></div>').insertAfter(frm.fields_dict.task_card.$wrapper);
        }

        // Debug: Check if task_card data exists
        console.log('Task Card Data:', frm.doc.task_card);
        console.log('Task Card Field:', frm.fields_dict.task_card);

        // Render custom UIs
        render_status_flow(frm);
        render_task_card(frm);
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
                padding: 10px 18px;
                cursor: pointer;
                border: 1px solid #dee2e6;
                display: flex;
                align-items: center;
                gap: 10px;
                transition: all 0.2s ease;
                min-height: 20px;
            " data-index="${idx}">
                <span style="color: #495057; font-size: 14px; font-weight: 700;">${row.workflow_status}</span>
                <span style="color: #6c757d; font-size: 13px; font-weight: 500;">
                    ${row.start_state ? 'Start' : row.working_state ? 'Working' : row.end_state ? 'End' : ''}
                </span>
                <button class="btn btn-link btn-xs remove-btn" style="padding: 0; font-size: 14px; color: #6c757d;">✖</button>
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
        
        // FIXED: Mark form as dirty and refresh
        frm.dirty();
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
    frm.dirty();
    frm.refresh_field('status_flow');
    render_status_flow(frm);
}

function render_task_card(frm) {
    const wrapper = $('#task-card-ui');
    wrapper.empty();
    // Add spacing above the heading
    wrapper.append('<h4 style="margin-top: 16px; margin-bottom: 12px;">Task Card</h4>');

    // Check if task_card field exists and has data
    if (!frm.doc.task_card || !Array.isArray(frm.doc.task_card)) {
        wrapper.append('<p style="color: #6c757d; font-style: italic;">No task card data found. Make sure the "task_card" field is properly linked to "CT Task Card Table".</p>');
        
        // Still show the Add button
        const buttonHtml = '<button class="btn btn-sm btn-primary" id="add-value-btn" style="margin-bottom: 16px;">Add Value</button>';
        wrapper.append(buttonHtml);
        $('#add-value-btn').click(() => add_task_card_dialog(frm));
        return;
    }

    frm.doc.task_card.forEach((row, idx) => {
        const displayTargetField = convertToDisplayValue(row.target_field);
        
        const mappingItem = $(`
            <div class="task-card-item" style="
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
                    <b>${displayTargetField}</b> → <i>${row.value || 'No value'}</i> : ${row.label_text || 'No label'}
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
                edit_task_card_row(frm, idx);
            }
        });

        // Remove on button click
        mappingItem.find('.remove-mapping-btn').click(function(e) {
            e.stopPropagation();
            remove_task_card_row(frm, idx);
        });

        wrapper.append(mappingItem);
    });

    // Check if all 4 values are created
    const isMaxReached = frm.doc.task_card.length >= 4;
    
    // Add spacing above the button
    const buttonHtml = isMaxReached ? 
        '<button class="btn btn-sm btn-secondary" id="add-value-btn" style="margin-bottom: 16px;" disabled>Add Value (Max 4 reached)</button>' :
        '<button class="btn btn-sm btn-primary" id="add-value-btn" style="margin-bottom: 16px;">Add Value</button>';
    
    wrapper.append(buttonHtml);

    if (!isMaxReached) {
        $('#add-value-btn').click(() => add_task_card_dialog(frm));
    }
}

// Function to show add/edit task card dialog with enhanced source path UI
async function show_task_card_dialog(frm, editIndex = null) {
    // Get existing data if editing
    let existing_data = {};
    if (editIndex !== null) {
        existing_data = frm.doc.task_card[editIndex];
    }

    let d = new frappe.ui.Dialog({
        title: editIndex !== null ? 'Edit Value' : 'Add Value',
        fields: [
            {
                fieldname:'target_field', 
                label:'Target Field', 
                fieldtype:'Select', 
                options:'Assign To Row\nFirst Row\nSecond Row\nThird Row', 
                reqd:1, 
                default: existing_data.target_field ? convertToDisplayValue(existing_data.target_field) : ''
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldname:'label_text', 
                label:'Label Text', 
                fieldtype:'Data',
                reqd:1, 
                default: existing_data.label_text || ''
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'HTML',
                fieldname: 'value_builder',
                label: 'Value Builder'
            }
        ]
    });

    // Store frm reference in dialog for access in path builder
    d.frm = frm;

    d.show();

    // Initialize the value builder after dialog is rendered
    setTimeout(async () => {
        await initValueBuilder(d, frm.doc.task_type, existing_data.value || '');
    }, 100);

    d.set_primary_action(editIndex !== null ? 'Update' : 'Add', () => {
        let data = d.get_values();
        
        if (!data.target_field) {
            frappe.msgprint('Target Field is required!');
            return;
        }

        // Get the value from the builder
        const value = getValueFromBuilder(d);

        if (!value) {
            frappe.msgprint('Value is required!');
            return;
        }

        if (!data.label_text) {
            frappe.msgprint('Label Text is required!');
            return;
        }

        // Convert display values back to storage format and auto-determine label field
        const storageData = {
            target_field: convertToStorageValue(data.target_field),
            label_field: autoConvertToLabelField(data.target_field),
            value: value,
            label_text: data.label_text
        };

        if (editIndex !== null) {
            // Update existing row
            Object.assign(frm.doc.task_card[editIndex], storageData);
        } else {
            // Add new row
            frm.add_child('task_card', storageData);
        }
        
        // FIXED: Mark form as dirty and refresh
        frm.dirty();
        frm.refresh_field('task_card');
        render_task_card(frm);
        d.hide();
    });
}

// Initialize the value builder UI
async function initValueBuilder(dialog, taskType, existingValue = '') {
    const wrapper = dialog.$wrapper.find('[data-fieldname="value_builder"]');
    
    // Create container for the path builder
    const container = $(`
        <div class="value-builder">
            <label style="margin-bottom: 8px; display: block;">Value</label>
            <div class="path-display" style="
                background: #f8f9fa; 
                border: 1px solid #d1d8dd; 
                border-radius: 4px; 
                padding: 8px 12px; 
                margin-bottom: 12px; 
                min-height: 20px;
                font-family: monospace;
                font-size: 13px;
                color: #495057;
            "></div>
            <div class="field-selectors" style="display: flex; flex-direction: column; gap: 8px;"></div>
        </div>
    `);
    
    wrapper.html(container);

    // Initialize path builder state
    const pathBuilder = {
        dialog: dialog,
        container: container,
        path: [],
        selectors: []
    };

    // Store reference for later access
    dialog.pathBuilder = pathBuilder;

    // Load initial fields and parse existing path if provided
    if (existingValue) {
        await parseAndBuildExistingPath(pathBuilder, 'Task', existingValue, taskType);
    } else {
        await addFieldSelector(pathBuilder, 'Task', 'Task',taskType);
    }
}

// Parse existing path and rebuild the UI - FIXED for dynamic doctypes
async function parseAndBuildExistingPath(pathBuilder, baseTaskDoctype, existingValue, taskType) {
    console.log('Parsing existing path:', existingValue);
    
    const pathParts = existingValue.split('.');
    
    // Check if the path starts with task_type_doc - this means it's a dynamic link to the current task type
    if (pathParts[0] === 'task_type_doc') {
        // Start with Task doctype for task_type_doc field
        let currentDoctype = 'Task';
        let currentDoctypeLabel = 'Task';
        
        pathBuilder.path = [];
        
        // Always add the first selector for Task doctype
        const firstSelector = await addFieldSelector(pathBuilder, currentDoctype, currentDoctypeLabel,taskType);
        
        // Set task_type_doc in the first selector
        $(firstSelector).val('task_type_doc').trigger('change');
        await new Promise(resolve => setTimeout(resolve, 200));
        
        // Update path for task_type_doc
        const taskFields = await getDocTypeFields(currentDoctype, pathBuilder,taskType);
        const taskTypeDocField = taskFields.find(f => f.fieldname === 'task_type_doc');
        if (taskTypeDocField) {
            pathBuilder.path[0] = {
                field: 'task_type_doc',
                doctype: currentDoctype,
                fieldData: taskTypeDocField
            };
        }
        
        // Now switch to the actual task type doctype for remaining fields
        const currentTaskType = pathBuilder.dialog.frm?.doc?.task_type;
        if (currentTaskType) {
            currentDoctype = currentTaskType;
            currentDoctypeLabel = currentTaskType;
            
            // Process remaining path parts (skip task_type_doc which is index 0)
            for (let i = 1; i < pathParts.length; i++) {
                const fieldName = pathParts[i];
                console.log(`Processing field: ${fieldName} at level ${i} in doctype: ${currentDoctype}`);
                
                // Get fields for current doctype
                const fields = await getDocTypeFields(currentDoctype, pathBuilder,taskType);
                const field = fields.find(f => f.fieldname === fieldName);
                
                if (field) {
                    console.log(`Found field:`, field);
                    
                    // Set the value in the current selector (which should exist from previous iteration or trigger)
                    const currentSelector = pathBuilder.selectors[i];
                    if (currentSelector) {
                        $(currentSelector).val(fieldName).trigger('change');
                        await new Promise(resolve => setTimeout(resolve, 200));
                    }
                    
                    // Update path
                    pathBuilder.path[i] = {
                        field: fieldName,
                        doctype: currentDoctype,
                        fieldData: field
                    };
                    
                    // If this is a link field and not the last part, prepare for next level
                    if (field.fieldname === 'type') {
                        console.log('Field is "type", ending path here');
                        break;
                    } else if ((field.fieldtype === 'Link') && i < pathParts.length - 1) {
                        currentDoctype = field.options;
                        currentDoctypeLabel = field.options;
                        console.log(`Next doctype (Link): ${currentDoctype}`);
                    }
                } else {
                    console.warn(`Field ${fieldName} not found in ${currentDoctype}`);
                    break;
                }
            }
        }
    } else {
        // Handle regular paths (not starting with task_type_doc)
        let currentDoctype = baseTaskDoctype;
        let currentDoctypeLabel = baseTaskDoctype;
        
        pathBuilder.path = [];
        
        // Always add the first selector
        const firstSelector = await addFieldSelector(pathBuilder, currentDoctype, currentDoctypeLabel,taskType);
        
        for (let i = 0; i < pathParts.length; i++) {
            const fieldName = pathParts[i];
            console.log(`Processing field: ${fieldName} at level ${i}`);
            
            // Get fields for current doctype
            const fields = await getDocTypeFields(currentDoctype, pathBuilder,taskType);
            const field = fields.find(f => f.fieldname === fieldName);
            
            if (field) {
                console.log(`Found field:`, field);
                
                // Set the value in the current selector
                const currentSelector = pathBuilder.selectors[i];
                if (currentSelector) {
                    $(currentSelector).val(fieldName).trigger('change');
                    await new Promise(resolve => setTimeout(resolve, 200));
                }
                
                // Update path
                pathBuilder.path[i] = {
                    field: fieldName,
                    doctype: currentDoctype,
                    fieldData: field
                };
                
                // Handle next level
                if (field.fieldname === 'type') {
                    console.log('Field is "type", ending path here');
                    break;
                } else if ((field.fieldtype === 'Link') && i < pathParts.length - 1) {
                    currentDoctype = field.options;
                    currentDoctypeLabel = field.options;
                    console.log(`Next doctype (Link): ${currentDoctype}`);
                }
            } else {
                console.warn(`Field ${fieldName} not found in ${currentDoctype}`);
                break;
            }
        }
    }
    
    updatePathDisplay(pathBuilder);
    console.log('Final path:', pathBuilder.path);
}

// Add a field selector at the current level
async function addFieldSelector(pathBuilder, doctype, doctypeLabel, taskType, selectedField = '') {
    const fields = await getDocTypeFields(doctype, pathBuilder,taskType);
    
    // Create selector container
    const selectorContainer = $(`
        <div class="field-selector-container" style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            <span class="doctype-label" style="
                background: #e3f2fd; 
                color: #1976d2; 
                padding: 4px 8px; 
                border-radius: 12px; 
                font-size: 11px; 
                font-weight: 500;
                min-width: 60px;
                text-align: center;
            ">${doctypeLabel}</span>
            <select class="form-control field-selector" style="flex: 1;">
                <option value="">Select Field...</option>
            </select>
            <button class="btn btn-xs btn-default remove-selector" style="padding: 2px 6px;" title="Remove this level">×</button>
        </div>
    `);

    // Populate field options
    const select = selectorContainer.find('.field-selector');
    fields.forEach(field => {
        const option = $(`<option value="${field.fieldname}">${field.label || field.fieldname} (${field.fieldtype})</option>`);
        select.append(option);
    });

    // Set selected field if provided
    if (selectedField) {
        select.val(selectedField);
    }

    // Add event handler for field selection
    select.change(async function() {
        const fieldName = $(this).val();
        const selectorIndex = pathBuilder.selectors.indexOf(this);
        
        // Remove all selectors after this one
        pathBuilder.selectors.slice(selectorIndex + 1).forEach(selector => {
            $(selector).closest('.field-selector-container').remove();
        });
        pathBuilder.selectors = pathBuilder.selectors.slice(0, selectorIndex + 1);
        pathBuilder.path = pathBuilder.path.slice(0, selectorIndex + 1);

        if (fieldName) {
            const field = fields.find(f => f.fieldname === fieldName);
            
            // Update path
            if (pathBuilder.path[selectorIndex]) {
                pathBuilder.path[selectorIndex] = {
                    field: fieldName,
                    doctype: doctype,
                    fieldData: field
                };
            } else {
                pathBuilder.path.push({
                    field: fieldName,
                    doctype: doctype,
                    fieldData: field
                });
            }

            // Handle different field types for next level
            // Special case: If field is "type", don't show next level selector
            if (field.fieldname === 'type') {
                // Do nothing - end the path here
            } else if (field.fieldtype === 'Link' && field.options) {
                await addFieldSelector(pathBuilder, field.options, field.options,taskType);
            } else if (field.fieldtype === 'Dynamic Link') {
                // Special handling for task_type_doc field
                if (field.fieldname === 'task_type_doc') {
                    // Get the current task_type from the form document
                    const currentTaskType = pathBuilder.dialog.frm?.doc?.task_type;
                    if (currentTaskType) {
                        await addFieldSelector(pathBuilder, currentTaskType, currentTaskType,taskType);
                    } else {
                        frappe.msgprint({
                            title: 'Task Type Required',
                            message: 'Please select a Task Type first before configuring this dynamic field.',
                            indicator: 'orange'
                        });
                    }
                } else {
                    // For other dynamic link fields, find the reference doctype field
                    const referenceDoctypeField = fields.find(f => 
                        f.fieldname === field.options && f.fieldtype === 'Link'
                    );
                    if (referenceDoctypeField) {
                        // For dynamic link, you might need to show a doctype selector
                        // For now, we'll just show a placeholder
                        await addFieldSelector(pathBuilder, 'DocType', 'Dynamic',taskType);
                    }
                }
            }
        } else {
            // Clear path if no field selected
            if (pathBuilder.path[selectorIndex]) {
                pathBuilder.path = pathBuilder.path.slice(0, selectorIndex);
            }
        }

        updatePathDisplay(pathBuilder);
    });

    // Add remove button handler
    selectorContainer.find('.remove-selector').click(function() {
        const selectorIndex = pathBuilder.selectors.indexOf(select[0]);
        if (selectorIndex > 0) { // Don't allow removing the first selector
            // Remove this and all subsequent selectors
            pathBuilder.selectors.slice(selectorIndex).forEach(selector => {
                $(selector).closest('.field-selector-container').remove();
            });
            pathBuilder.selectors = pathBuilder.selectors.slice(0, selectorIndex);
            pathBuilder.path = pathBuilder.path.slice(0, selectorIndex);
            updatePathDisplay(pathBuilder);
        }
    });

    // Add to container and track
    pathBuilder.container.find('.field-selectors').append(selectorContainer);
    pathBuilder.selectors.push(select[0]);

    return select[0];
}

// Get fields for a doctype - INCLUDE task_type_doc for Task doctype
async function getDocTypeFields(doctype, pathBuilder,taskType) {
    try {
        const doc = await frappe.db.get_doc("DocType", doctype);
        const excludedFieldtypes = [
            "Section Break", "Column Break", "HTML", "Line Break", 
            "Table", "Button", "Fold", "Heading","Table MultiSelect"
        ];
        
        let fields = (doc.fields || [])
            .filter(f => !f.hidden && !excludedFieldtypes.includes(f.fieldtype));

        // Remove task_type_doc field if taskType is "Task"
        if (taskType === "Task") {
            fields = fields.filter(f => f.fieldname !== "task_type_doc");
        }
        
        return fields.sort((a, b) => (a.label || a.fieldname).localeCompare(b.label || b.fieldname));
    } catch (error) {
        console.error(`Error fetching fields for ${doctype}:`, error);
        return [];
    }
}

// Update the path display
function updatePathDisplay(pathBuilder) {
    const pathDisplay = pathBuilder.container.find('.path-display');
    const pathString = pathBuilder.path.map(p => p.field).join('.');
    
    if (pathString) {
        pathDisplay.text(pathString);
        pathDisplay.css('color', '#495057');
    } else {
        pathDisplay.text('No field selected');
        pathDisplay.css('color', '#6c757d');
    }
}

// Get the final value from the builder
function getValueFromBuilder(dialog) {
    if (dialog.pathBuilder) {
        return dialog.pathBuilder.path.map(p => p.field).join('.');
    }
    return '';
}

function convertToDisplayValue(storageValue) {
    const mapping = {
        'assign_to_value': 'Assign To Row',
        'first_value': 'First Row',
        'second_value': 'Second Row',
        'third_value': 'Third Row'
    };
    return mapping[storageValue] || storageValue;
}

function convertToStorageValue(displayValue) {
    const mapping = {
        'Assign To Row': 'assign_to_value',
        'First Row': 'first_value',
        'Second Row': 'second_value',
        'Third Row': 'third_value'
    };
    return mapping[displayValue] || displayValue;
}

// Auto-convert target field to corresponding label field
function autoConvertToLabelField(displayTargetField) {
    const mapping = {
        'Assign To Row': 'assign_to_label',
        'First Row': 'first_label',
        'Second Row': 'second_label',
        'Third Row': 'third_label'
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

// Add task card dialog (wrapper for add functionality)
function add_task_card_dialog(frm) {
    show_task_card_dialog(frm);
}

// Edit task card row
function edit_task_card_row(frm, idx) {
    show_task_card_dialog(frm, idx);
}

// Remove task card row
window.remove_task_card_row = function(frm, idx) {
    frm.doc.task_card.splice(idx, 1);
    frm.dirty();
    frm.refresh_field('task_card');
    render_task_card(frm);
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