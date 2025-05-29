import requests
from checktrack_connector.api import DATA_API_URL, USER_API_URL
import frappe
from frappe import _


def get_last_value(url):
    parts = url.rstrip('/').split('/')
    return parts[-1]

@frappe.whitelist()
def send_feedback_request(task_id):
    try:
        task = frappe.get_doc('Task', task_id)

        # if not task.customer:
        #     frappe.throw(_("No customer linked to this task."))

        # customer = frappe.get_doc("Customer", task.customer)
        # email = customer.email_id or customer.primary_contact_email
        # if not email:
        #     frappe.throw(_("Customer email not found."))

        # Test email for now

        feedback_url = f"http://erpnext.local:8001/feedback-web-form/new?task={task_id}"

        subject_of_mail = f"Feedback Request for Task {task.task_name}"
        message_of_mail = f"""
            Dear Customer,<br><br>
            We would love to hear your thoughts on the task <b>{task.task_name}</b>.<br>
            Please provide your feedback using the link below:<br><br>
            <a href="{feedback_url}">Give Feedback</a><br><br>
            Regards,<br>
            Your Team
        """

        frappe.sendmail(
            recipients=["mihir.patel@team.satat.tech"],
            subject=subject_of_mail,
            message=message_of_mail
        )

    except Exception as e:
        frappe.msgprint(_("Failed to send feedback request: ") + str(e), alert=True)

def send_notification(doc, docname, prefix, tenantId):
    try:
        # Check if assign_to has changed or it's a new assignment
        previous_doc = doc.get_doc_before_save()
        current_assign_to = doc.assign_to

        # Determine if we should send the notification
        send_notification = False
        if previous_doc is None:
            # New document: send notification if assign_to is set
            if current_assign_to:
                send_notification = True
        else:
            # Existing document: send notification if assign_to changed
            previous_assign_to = previous_doc.assign_to
            if previous_assign_to != current_assign_to:
                send_notification = True

        if not send_notification:
            frappe.logger().info(f"No change in assign_to for {docname}, skipping notification.")
            return

        # Get the current user (assigner) details
        current_user = frappe.get_doc("User", frappe.session.user)
        assigner_name = current_user.full_name or current_user.name

        # Extract employee IDs from child table 'assign_to'
        list_of_employee_ids = [{"$oid": doc.assign_to}]

        if not list_of_employee_ids:
            frappe.logger().warn(f"No employees assigned to task {docname}, skipping notification.")
            return

        # Get API URLs
        USER_API_URL = frappe.get_hooks().get("user_api_url")
        DATA_API_URL = frappe.get_hooks().get("data_api_url")

        USER_API_URL = USER_API_URL[0] if isinstance(USER_API_URL, list) and USER_API_URL else USER_API_URL
        DATA_API_URL = DATA_API_URL[0] if isinstance(DATA_API_URL, list) and DATA_API_URL else DATA_API_URL

        # Prepare notification payload
        notification_data = {
            "prefix": prefix,
            "listOfEmployeeIds": list_of_employee_ids,
            "notificationPayload": {
                "title": "Task",
                "body": f"{assigner_name} has assigned the task \"{doc.task_name}\" to you",
                "data": {
                    "route": "/tasks/view",
                    "arguments": {
                        "doctype": "Task",
                        "docname": docname,
                        "isEdit": False,
                        "readOnly": True,
                        "selectedMenu": "summary"
                    }
                }
            },
            "tenantId": tenantId
        }

        # Send notification via API
        url = f"{USER_API_URL}/notification/send"
        access_token = get_app_admin_bearer_auth()
        notification_headers = {
            "Authorization": access_token,
            'Content-Type': 'application/json; charset=UTF-8',
            'No-Auth-Challenge': 'true'
        }

        response = requests.post(url, json=notification_data, headers=notification_headers)
        response.raise_for_status()

        frappe.logger().info(f"Notification sent for task {docname}")

        return response

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Notification sending failed")

def send_status_change_notification(doc, docname, prefix, tenantId):
    try:
        # Check if status has changed
        previous_doc = doc.get_doc_before_save()
        
        # Determine if notification should be sent
        send_notification = False
        
        if previous_doc is None:
            # New document: no status change to notify
            frappe.logger().info(f"New task {docname}, no status change notification.")
            return
        else:
            # Existing document: check if status changed
            previous_status = previous_doc.workflow_status
            current_status = doc.workflow_status
            if previous_status != current_status:
                send_notification = True

        if not send_notification:
            frappe.logger().info(f"Status unchanged for task {docname}, skipping notification.")
            return

        # Get current user (who changed the status)
        current_user = frappe.get_doc("User", frappe.session.user)
        changer_name = current_user.full_name or current_user.name

        # Get watchers from child table
        list_of_employee_ids = [{"$oid": row.employee} for row in doc.watchers]  # Adjust field name if different

        if not list_of_employee_ids:
            frappe.logger().warn(f"No watchers found for task {docname}, skipping notification.")
            return

        # Get API URLs (same as original function)
        USER_API_URL = frappe.get_hooks().get("user_api_url")
        if isinstance(USER_API_URL, list) and USER_API_URL:
            USER_API_URL = USER_API_URL[0]

        # Prepare notification payload
        notification_data = {
            "prefix": prefix,
            "listOfEmployeeIds": list_of_employee_ids,
            "notificationPayload": {
                "title": "Task Status Updated",
                "body": f"The status of task \"{doc.task_name}\" has changed from \"{previous_status}\" to \"{current_status}\" by \"{changer_name}\"",  # Include previous status for clarity
                "data": {
                    "route": "/tasks/view",
                    "arguments": {
                        "doctype": "Task",
                        "docname": docname,
                        "isEdit": False,
                        "readOnly": True,
                        "selectedMenu": "summary"
                    }
                }
            },
            "tenantId": tenantId
        }

        # Send notification
        url = f"{USER_API_URL}/notification/send"
        access_token = get_app_admin_bearer_auth()
        notification_headers = {
            "Authorization": access_token,
            'Content-Type': 'application/json; charset=UTF-8',
            'No-Auth-Challenge': 'true'
        }

        response = requests.post(url, json=notification_data, headers=notification_headers)
        response.raise_for_status()

        frappe.logger().info(f"Status change notification sent for task {docname}")
        return response

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Status change notification failed")

def sync_or_update_task_in_mongo(doc, method):
    if doc.mongo_task_id:
        response = update_task_in_mongo(doc, method)
    else:
        response = sync_task_to_mongo(doc, method)
      
def sync_or_update_project_in_mongo(doc, method):
    if doc.mongo_project_id:
        response = update_project_in_mongo(doc, method)
    else:
        response = sync_project_to_mongo(doc, method)

def get_app_admin_bearer_auth():

    try:
        USER_API_URL = frappe.get_hooks().get("user_api_url")
        DATA_API_URL = frappe.get_hooks().get("data_api_url")

        if isinstance(USER_API_URL, list) and USER_API_URL:
            USER_API_URL = USER_API_URL[0]
        if isinstance(DATA_API_URL, list) and DATA_API_URL:
            DATA_API_URL = DATA_API_URL[0]

        url = f"{USER_API_URL}/login"
        auth_payload = {"email": "jaympatel9294@gmail.com", "password": "0hr3VuNoyqcgy1Su"}
        HEADERS = {"Content-Type": "application/json"}
        auth_response = requests.post(url, headers=HEADERS, json=auth_payload)

        if auth_response.status_code != 200:
            frappe.throw("CheckTrack intergation failed. Invalid email or password.")

        auth_data = auth_response.json()
        frappe.log_error(message=f"Auth response keys: {list(auth_data.keys())}", title="Auth Debug")

        access_token = auth_data.get("accessToken")
        return f"Bearer {access_token}"

    except Exception:
        frappe.log_error(frappe.get_traceback(), "get_app_admin_bearer_auth failed")
        frappe.throw("Failed to generate admin token.") 

def sync_task_to_mongo(doc, method):

    USER_API_URL = frappe.get_hooks().get("user_api_url")
    DATA_API_URL = frappe.get_hooks().get("data_api_url")

    if isinstance(USER_API_URL, list) and USER_API_URL:
        USER_API_URL = USER_API_URL[0]
    if isinstance(DATA_API_URL, list) and DATA_API_URL:
        DATA_API_URL = DATA_API_URL[0]
    frappe.log_error("Triggered sync_task_to_mongo", f"TASK NAME: {doc.name}")
    company_doc = frappe.get_doc("Company", doc.company)
    payload = {
        "name": doc.task_name,
        "assignedTo": [],
        "description": doc.description,
        "frappe": {
            "_id": doc.name,
            "_ref": doc.doctype,
            "_title": doc.task_name
        },
        "tenant": {
            "_id": {
                "$oid" : company_doc.tenant_id
            },
            "_ref": "tenants",
            "_title": f"{company_doc.prefix}"
        }
    }
    if doc.project:
        try:
            project_doc = frappe.get_doc("Project", doc.project)
            
            payload["project"] = {
                "_id": {
                    "$oid": project_doc.mongo_project_id
                },
                "_ref": f"{company_doc.prefix}_projects",
                "_title": project_doc.project_name
            }
        except frappe.DoesNotExistError:
            frappe.log_error(f"Project '{doc.project}' not found", "Sync Task Error")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Failed to sync project '{doc.project}'")

    if doc.workflow_status:
        payload["status"] = doc.workflow_status
    else:
        payload["status"] = ""

    try:
        prefix = company_doc.prefix
        url = f"{DATA_API_URL}/{prefix}_tasks"
        access_token = get_app_admin_bearer_auth()
        task_headers = {
            "Authorization": access_token,
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=payload, headers=task_headers)
        response.raise_for_status()

        mongo_id = get_last_value(response.headers['Location'])
        if mongo_id:
            frappe.db.set_value(doc.doctype, doc.name, "mongo_task_id", mongo_id)
            frappe.logger().info(f"[SYNC SUCCESS] Task '{doc.name}' synced to MongoDB with ID: {mongo_id}")
        else:
            frappe.logger().error(f"[SYNC FAILED] Task '{doc.name}' created in MongoDB but no ID returned.")

        notification_res = send_notification(doc,doc.name,prefix,company_doc.tenant_id)
        return response

    except Exception as e:
        frappe.logger().error(f"[SYNC ERROR] Task '{doc.name}' failed to sync to MongoDB.")
        frappe.throw(e)

def update_task_in_mongo(doc, method):
    
    USER_API_URL = frappe.get_hooks().get("user_api_url")
    DATA_API_URL = frappe.get_hooks().get("data_api_url")

    if isinstance(USER_API_URL, list) and USER_API_URL:
        USER_API_URL = USER_API_URL[0]
    if isinstance(DATA_API_URL, list) and DATA_API_URL:
        DATA_API_URL = DATA_API_URL[0]

    company_doc = frappe.get_doc("Company", doc.company)

    payload = {
        "name": doc.task_name,
        "assignedTo": [],
        "description": doc.description,
        "frappe": {
            "_id": doc.name,
            "_ref": doc.doctype,
            "_title": doc.task_name
        },
        "tenant": {
            "_id": {
                "$oid" : company_doc.tenant_id
            },
            "_ref": "tenants",
            "_title": f"{company_doc.prefix}"
        }
    }
    if doc.project:
        try:
            project_doc = frappe.get_doc("Project", doc.project)
            
            payload["project"] = {
                "_id": {
                    "$oid": project_doc.mongo_project_id
                },
                "_ref": f"{company_doc.prefix}_projects",
                "_title": project_doc.project_name
            }
        except frappe.DoesNotExistError:
            frappe.log_error(f"Project '{doc.project}' not found", "Sync Task Error")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Failed to sync project '{doc.project}'")

    if doc.workflow_status:
        payload["status"] = doc.workflow_status
    else:
        payload["status"] = ""

    try:
        prefix = company_doc.prefix
        url = f"{DATA_API_URL}/{prefix}_tasks/{doc.mongo_task_id}"
        access_token = get_app_admin_bearer_auth()
        task_headers = {
            "Authorization": access_token,
            "Content-Type": "application/json"
        }
        response = requests.patch(url, json=payload, headers=task_headers)
        response.raise_for_status()

        notification_res = send_notification(doc,doc.name,prefix,company_doc.tenant_id)
        send_status_change_notification(doc,doc.name,prefix,company_doc.tenant_id)

        if doc.workflow_status.strip().lower() == 'complete':
            send_feedback_request(doc.name)

        return response

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Mongo Update Failed")

def sync_project_to_mongo(doc, method):

    USER_API_URL = frappe.get_hooks().get("user_api_url")
    DATA_API_URL = frappe.get_hooks().get("data_api_url")

    if isinstance(USER_API_URL, list) and USER_API_URL:
        USER_API_URL = USER_API_URL[0]
    if isinstance(DATA_API_URL, list) and DATA_API_URL:
        DATA_API_URL = DATA_API_URL[0]
    frappe.log_error("Triggered sync_project_to_mongo", f"PROJECT NAME: {doc.name}")
    company_doc = frappe.get_doc("Company", doc.company)
    payload = {
        "name": doc.project_name,
        "assignedTo": [],
        "description": doc.description,
        "status": doc.status,
        "frappe": {
            "_id": doc.name,
            "_ref": doc.doctype,
            "_title": doc.project_name
        },
        "tenant": {
            "_id": {
                "$oid" : company_doc.tenant_id
            },
            "_ref": "tenants",
            "_title": f"{company_doc.prefix}"
        }
    }

    try:
        prefix = company_doc.prefix
        url = f"{DATA_API_URL}/{prefix}_projects"
        access_token = get_app_admin_bearer_auth()
        project_headers = {
            "Authorization": access_token,
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=payload, headers=project_headers)
        response.raise_for_status()

        mongo_id = get_last_value(response.headers['Location'])
        if mongo_id:
            doc.mongo_project_id = mongo_id
            doc.save(ignore_permissions=True)
            frappe.logger().info(f"[SYNC SUCCESS] Project '{doc.name}' synced to MongoDB with ID: {mongo_id}")
        else:
            frappe.logger().error(f"[SYNC FAILED] Project '{doc.name}' created in MongoDB but no ID returned.")

        return response

    except Exception as e:
        frappe.logger().error(f"[SYNC ERROR] Project '{doc.name}' failed to sync to MongoDB.")
        frappe.throw(e)

def update_project_in_mongo(doc, method):
    
    USER_API_URL = frappe.get_hooks().get("user_api_url")
    DATA_API_URL = frappe.get_hooks().get("data_api_url")

    if isinstance(USER_API_URL, list) and USER_API_URL:
        USER_API_URL = USER_API_URL[0]
    if isinstance(DATA_API_URL, list) and DATA_API_URL:
        DATA_API_URL = DATA_API_URL[0]

    company_doc = frappe.get_doc("Company", doc.company)

    payload = {
        "name": doc.project_name,
        "assignedTo": [],
        "description": doc.description,
        "status": doc.status,
        "frappe": {
            "_id": doc.name,
            "_ref": doc.doctype,
            "_title": doc.project_name
        },
        "tenant": {
            "_id": {
                "$oid" : company_doc.tenant_id
            },
            "_ref": "tenants",
            "_title": f"{company_doc.prefix}"
        }
    }

    try:
        prefix = company_doc.prefix
        url = f"{DATA_API_URL}/{prefix}_projects/{doc.mongo_project_id}"
        access_token = get_app_admin_bearer_auth()
        project_headers = {
            "Authorization": access_token,
            "Content-Type": "application/json"
        }
        response = requests.patch(url, json=payload, headers=project_headers)
        response.raise_for_status()
        return response

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Mongo Update Failed")