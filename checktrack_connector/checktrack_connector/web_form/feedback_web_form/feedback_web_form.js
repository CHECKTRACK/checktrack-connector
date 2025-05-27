frappe.ready(async function () {

   function getUrlParameter(name) {
        name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
        var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
        var results = regex.exec(location.search);
        return results === null ? null : decodeURIComponent(results[1].replace(/\+/g, ' '));
    }

    const taskId = getUrlParameter('task_type_id');
    frappe.msgprint(taskId);

    const result = await frappe.call({
        method: "checktrack_connector.api.get_task_and_service_report",
        type: "GET",
        args: {
            task_id: taskId,
        }
    });

    const feedback = result.message.task.feedback;
    if (feedback) {
        window.location.href = '/thank-you-form';
        return;
    }

	const navBar = document.querySelector('nav.navbar.navbar-light.navbar-expand-lg');
    if (navBar) {
        navBar.style.display = 'none';
    }
	const footer = document.querySelector('footer.web-footer');
    if (footer) {
        footer.style.display = 'none';
    }
    
});