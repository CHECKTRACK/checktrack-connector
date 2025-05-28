(function () {
    function getUrlParameter(name) {
        name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
        var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
        var results = regex.exec(location.search);
        return results === null ? null : decodeURIComponent(results[1].replace(/\+/g, ' '));
    }

    const taskId = getUrlParameter('task_type_id');

    if (!taskId) return;

    document.documentElement.style.display = 'none';

    fetch('/api/method/checktrack_connector.api.get_task_and_service_report?' + new URLSearchParams({
        task_id: taskId
    }), {
        method: 'GET',
        headers: {
            'Accept': 'application/json'
        }
    }).then(res => res.json())
      .then(result => {
          const feedback = result.message?.task?.feedback;
          if (feedback) {
              window.location.href = '/thank-you-form';
          } else {
              document.documentElement.style.display = '';
              frappe.ready(async function() {
                  const navBar = document.querySelector('nav.navbar.navbar-light.navbar-expand-lg');
                    if (navBar) {
                        navBar.style.display = 'none';
                    }
                    const footer = document.querySelector('footer.web-footer');
                    if (footer) {
                        footer.style.display = 'none';
                    }
              });
          }
      })
      .catch(err => {
          console.error("API failed:", err);
          document.documentElement.style.display = '';
          frappe.ready(async function() {
                const navBar = document.querySelector('nav.navbar.navbar-light.navbar-expand-lg');
                if (navBar) {
                    navBar.style.display = 'none';
                }
                const footer = document.querySelector('footer.web-footer');
                if (footer) {
                    footer.style.display = 'none';
                }
          });
      });
})();