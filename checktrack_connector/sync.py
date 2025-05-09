import requests
from checktrack_connector.api import DATA_API_URL, USER_API_URL
import frappe

def get_last_value(url):
    parts = url.rstrip('/').split('/')
    return parts[-1]

def sync_or_update_task_in_mongo(doc, method):
    if doc.mongo_task_id:
        update_task_in_mongo(doc, method)
    else:
        sync_task_to_mongo(doc, method)
        
def sync_or_update_project_in_mongo(doc, method):
    if doc.mongo_project_id:
        update_project_in_mongo(doc, method)
    else:
        sync_project_to_mongo(doc, method)

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

    if doc.status:
        payload["status"] = doc.status
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
            doc.mongo_task_id = mongo_id
            doc.save(ignore_permissions=True)
            frappe.logger().info(f"[SYNC SUCCESS] Task '{doc.name}' synced to MongoDB with ID: {mongo_id}")
        else:
            frappe.logger().error(f"[SYNC FAILED] Task '{doc.name}' created in MongoDB but no ID returned.")

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

    if doc.status:
        payload["status"] = doc.status
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

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Mongo Update Failed")