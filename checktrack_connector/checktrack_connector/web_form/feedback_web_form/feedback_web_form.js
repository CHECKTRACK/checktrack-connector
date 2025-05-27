// frappe.ready(async function () {
// 	const navBar = document.querySelector('nav.navbar.navbar-light.navbar-expand-lg');
//     if (navBar) {
//         navBar.style.display = 'none';
//     }
// 	const footer = document.querySelector('footer.web-footer');
//     if (footer) {
//         footer.style.display = 'none';
//     }
//     function getUrlParameter(name) {
//         name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
//         var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
//         var results = regex.exec(location.search);
//         return results === null ? null : decodeURIComponent(results[1].replace(/\+/g, ' '));
//     }

    

//     const result = await frappe.call({
//         method: "checktrack_connector.api.get_task_and_service_report",
//         type: "GET",
//         args: {
//             task_id: taskId,
//         }
//     });

//     const remark = result.message.service_report?.remarks??'';
//     frappe.msgprint(`remarks ${remark}`);

//     frappe.web_form.on('after_load',() => {
//         const taskId = getUrlParameter('task');
//         const task = getUrlParameter('tasks');
//         frappe.msgprint(taskId);
//         frappe.msgprint(task);
        
//         if (taskId) {
//              frappe.web_form.set_value('tasks', remark);
//              frappe.web_form.set_value('task', taskId);
//         }
//     });
// });