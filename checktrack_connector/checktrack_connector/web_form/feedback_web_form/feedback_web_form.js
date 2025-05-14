frappe.ready(function () {
	const navBar = document.querySelector('nav.navbar.navbar-light.navbar-expand-lg');
    if (navBar) {
        navBar.style.display = 'none';
    }
	const footer = document.querySelector('footer.web-footer');
    if (footer) {
        footer.style.display = 'none';
    }
    function getUrlParameter(name) {
        name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
        var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
        var results = regex.exec(location.search);
        return results === null ? null : decodeURIComponent(results[1].replace(/\+/g, ' '));
    }

    const taskId = getUrlParameter('task');

    frappe.web_form.on('after_load', () => {
        
        if (taskId) {
            frappe.web_form.set_value('task', taskId);
            // frappe.web_form.set_df_property('task', 'reqd', 1);
			// frappe.web_form.set_df_property('task', 'hidden', 1);
        }
		// const taskFieldWrapper = document.querySelector('form.frappe-control.input-max-eidth');
        // if (taskFieldWrapper) {
        //     taskFieldWrapper.style.display = 'none';
        // }
    });
});