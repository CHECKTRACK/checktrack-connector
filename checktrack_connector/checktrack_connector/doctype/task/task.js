// Copyright (c) 2025, satat tech llp and contributors
// For license information, please see license.txt

frappe.ui.form.on("Task", {
    refresh(frm) {
        // Remove any existing status circle
        frm.dashboard.clear_headline();
        
        // Create and display status circle
        if (frm.doc.status) {
            create_status_circle(frm);
        }
    },
    
    // Update circle when status field changes
    status(frm) {
        if (frm.doc.status) {
            create_status_circle(frm);
        }
    }
});

function create_status_circle(frm) {
    const status = frm.doc.status;
    
    // Define status colors
    const status_colors = {
        'Open': '#ff6b6b',
        'Working': '#4ecdc4',
        'Pending Review': '#45b7d1',
        'Overdue': '#f39c12',
        'Template': '#9b59b6',
        'Completed': '#2ecc71',
        'Cancelled': '#e74c3c'
    };
    
    // Get color for current status (default to gray if not found)
    const color = status_colors[status] || '#95a5a6';
    
    // Create HTML for status circle
    const circle_html = `
        <div class="status-circle-container" style="
            display: flex;
            align-items: center;
            margin: 10px 0;
            padding: 15px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        ">
            <div class="status-circle" style="
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: ${color};
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 12px;
                text-align: center;
                margin-right: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                animation: pulse 2s infinite;
            ">
                ${status.charAt(0).toUpperCase()}
            </div>
            <div class="status-info">
                <div style="
                    font-weight: 600;
                    font-size: 16px;
                    color: #2c3e50;
                    margin-bottom: 4px;
                ">
                    Status: ${status}
                </div>
                <div style="
                    font-size: 12px;
                    color: #7f8c8d;
                ">
                    Last Updated: ${frappe.datetime.get_datetime_as_string(frm.doc.modified)}
                </div>
            </div>
        </div>
        <style>
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            .status-circle-container:hover {
                transform: translateY(-2px);
                transition: all 0.3s ease;
            }
        </style>
    `;
    
    // Add the circle to form dashboard
    frm.dashboard.add_section(circle_html, __("Task Status"));
}

// Alternative approach: Add to specific section
function add_status_circle_to_section(frm) {
    const status = frm.doc.status;
    if (!status) return;
    
    // Find a section to add the circle (you can customize this)
    const section = frm.fields_dict.section_break_1 || frm.fields_dict.details_section;
    
    if (section && section.wrapper) {
        // Remove existing circle if any
        $(section.wrapper).find('.custom-status-circle').remove();
        
        const circle_element = $(`
            <div class="custom-status-circle" style="
                text-align: center;
                margin: 20px 0;
                padding: 15px;
            ">
                <div style="
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    background: ${get_status_color(status)};
                    margin: 0 auto 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                ">
                    ${status}
                </div>
                <div style="
                    font-size: 12px;
                    color: #666;
                    margin-top: 8px;
                ">
                    Current Status
                </div>
            </div>
        `);
        
        $(section.wrapper).prepend(circle_element);
    }
}

function get_status_color(status) {
    const colors = {
        'Open': '#ff6b6b',
        'Working': '#4ecdc4',
        'Pending Review': '#45b7d1',
        'Overdue': '#f39c12',
        'Template': '#9b59b6',
        'Completed': '#2ecc71',
        'Cancelled': '#e74c3c'
    };
    return colors[status] || '#95a5a6';
}