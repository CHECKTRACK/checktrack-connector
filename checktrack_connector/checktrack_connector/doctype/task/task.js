frappe.ui.form.on("Task", {
    refresh(frm) {
        render_status_ui(frm);
    },

    status(frm) {
        render_status_ui(frm);
    },

    type(frm) {
        render_status_ui(frm); // re-render when type changes
    }
});

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

    // Show "Pending" only if no type selected
    if (!frm.doc.type) {
        render_status_dropdown(wrapper, frm, ['Pending']);
        return;
    }

    // Call server to get status list based on selected type
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "CT Task Flow",
            filters: {
                name: frm.doc.type
            },
            fields: ["name"],
            limit: 1
        },
        callback: function (res) {
            const doc = res.message?.[0];
            if (!doc) {
                render_status_dropdown(wrapper, frm, ['Pending']);
                return;
            }

            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "CT Task Flow",
                    name: doc.name
                },
                callback: function (r) {
                    const status_list = (r.message.status_flow || []).map(row => row.status);
                    if (!status_list.length) status_list.push('Pending');
                    render_status_dropdown(wrapper, frm, status_list);
                }
            });
        }
    });
}

function render_status_dropdown(wrapper, frm, status_list) {
    const is_submitted = frm.doc.docstatus === 1;


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
                ${frm.doc.status ? frm.doc.status.charAt(0).toUpperCase() : '-'}
            </div>
            <div>
                <div style="font-weight: 600; font-size: 14px;">
                    Current Status: ${frm.doc.status || 'Not Set'}
                </div>
                <div style="font-size: 12px; color: #888;">
                    Last Updated: ${frappe.datetime.get_datetime_as_string(frm.doc.modified)}
                </div>
                ${!is_submitted ? `
                <div style="margin-top: 8px;">
                    <select id="status-dropdown" style="padding: 6px 10px; border-radius: 4px; border: 1px solid #ccc;">
                        ${status_list.map(s => `
                            <option value="${s}" ${s === frm.doc.status ? "selected" : ""}>${s}</option>
                        `).join('')}
                    </select>
                </div>` : ''}
            </div>
        </div>
    `;

    wrapper.html(status_display);

    if (!is_submitted) {
        setTimeout(() => {
            $('#status-dropdown').on('change', function () {
                const new_status = $(this).val();
                if (new_status !== frm.doc.status) {
                    frm.set_value('status', new_status);
                    frappe.show_alert(`Status set to ${new_status}. Don't forget to Save.`);
                }
            });
        }, 100);
    }
}
