import io
import csv
import frappe
import urllib.parse
import json
import requests
from frappe.utils.file_manager import save_file
from frappe.core.doctype.data_import.data_import import start_import, get_import_status

USER_API_URL = frappe.get_hooks().get("user_api_url")
DATA_API_URL = frappe.get_hooks().get("data_api_url")
if isinstance(USER_API_URL, list) and USER_API_URL:
    USER_API_URL = USER_API_URL[0]
if isinstance(DATA_API_URL, list) and DATA_API_URL:
    DATA_API_URL = DATA_API_URL[0]


@frappe.whitelist()
def automated_import_users(tenant_id=None):
    try:
        if not tenant_id:
            return {"status": "error", "message": "tenant_id is required"}

        # Step 1: Fetch team members based on tenant_id
        team_members = frappe.get_all("Employee", filters={"company": tenant_id}, fields=["work_email", "first_name", "last_name"])

        if not team_members:
            return {"status": "error", "message": "No team members found for the provided tenant_id"}

        # Step 2: Prepare CSV data
        data = [
            ["email", "first_name", "last_name", "user_type", "roles.role", "enabled", "send_welcome_email"]
        ]
        
        for tm in team_members:
            data.append([
                tm.work_email,
                tm.first_name,
                tm.last_name,
                "System User",
                "System Manager",
                1,
                0
            ])

        # Step 3: Convert to CSV in-memory
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        for row in data:
            writer.writerow(row)
        csv_buffer.seek(0)

        # Step 4: Save file in Frappe's file system
        file_doc = save_file(
            fname="user_import.csv",
            content=csv_buffer.getvalue(),
            dt=None,
            dn=None,
            folder="Home",
            decode=False,
            is_private=0
        )
        frappe.db.commit()

        # Step 5: Create Data Import record
        import_doc = frappe.get_doc({
            "doctype": "Data Import",
            "reference_doctype": "User",
            "import_type": "Insert New Records",
            "import_file": file_doc.file_url,
            "submit_after_import": 0,
            "overwrite": 0,
            "ignore_encoding_errors": 1
        })
        import_doc.save()
        frappe.db.commit()

        # Step 6: Start import
        start_import(import_doc.name)

        # Step 7: Check import status
        status_info = get_import_status(import_doc.name)

        if status_info.get("status") == "Success":

            new_user_emails = [tm["work_email"] for tm in team_members]
            created_permission_ids = []
            failed_permissions = []

            for email in new_user_emails:
                if frappe.db.exists("User", email):
                    try:
                        if not frappe.db.exists("User Permission", {
                            "user": email,
                            "allow": "Company",
                            "for_value": tenant_id
                        }):
                            doc = frappe.get_doc({
                                "doctype": "User Permission",
                                "user": email,
                                "allow": "Company",
                                "for_value": tenant_id,
                                "apply_to_all_doctypes": 1
                })
                            doc.insert(ignore_permissions=True)
                            created_permission_ids.append(doc.name)
                    except Exception:
                        frappe.log_error(frappe.get_traceback(), f"User Permission Error for {email}")
                        failed_permissions.append(email)
                        break


            if failed_permissions:
                for perm_id in created_permission_ids:
                    try:
                        frappe.delete_doc("User Permission", perm_id, ignore_permissions=True)
                    except Exception as del_err:
                        frappe.log_error(frappe.get_traceback(), f"Rollback failed for User Permission: {perm_id}")
    
                frappe.db.commit()
                return {
                    "status": "error",
                    "message": "User permission creation failed. Rolled back all permissions.",
                    "failed_user_permissions": failed_permissions
                }
            
            frappe.db.commit()

            return {
                "status": "success",
                "message": f"Imported data into User from file {file_doc.file_url}"
            }
        else:
            return {
                "status": "error",
                "message": "Import failed",
                "details": status_info.get("messages")
            }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "automated_import_users failed")
        return {
            "status": "error",
            "message": "An error occurred during user import",
            "error": str(e)
        }
    
@frappe.whitelist()
def import_project(tenant_id, tenant_prefix, access_token,company_name):
    try:
        filter_query = {"tenant._id": {"$oid": tenant_id}}
        url = f"{DATA_API_URL}/{tenant_prefix}_projects?filter={urllib.parse.quote(json.dumps(filter_query))}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "No-Auth-Challenge": "true",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            projects = response.json()
            if not isinstance(projects, list):
                return {"status": "error", "message": "No project found for the provided tenant_id"}
            data = [
                ["project_name", "description","status","company","mongo_project_id"]
            ]
            for project in projects:
                data.append([
                    project.get("name"),
                    project.get("description"),
                    project.get("status").capitalize(),
                    company_name,
                    project.get("_id", {}).get("$oid")
                ])
            
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            for row in data:
                writer.writerow(row)
            csv_buffer.seek(0)

            file_doc = save_file(
                fname="project_import.csv",
                content=csv_buffer.getvalue(),
                dt=None,
                dn=None,
                folder="Home",
                decode=False,
                is_private=0
            )
            frappe.db.commit()

            # Step 5: Create Data Import record
            import_doc = frappe.get_doc({
                "doctype": "Data Import",
                "reference_doctype": "Project",
                "import_type": "Insert New Records",
                "import_file": file_doc.file_url,
                "submit_after_import": 0,
                "overwrite": 0,
                "ignore_encoding_errors": 1
            })
            import_doc.save()
            frappe.db.commit()

            start_import(import_doc.name)

            status_info = get_import_status(import_doc.name)

            if status_info.get("status") == "Success":

                created_projects = frappe.get_all("Project",fields=["name", "mongo_project_id"])
                project_id_map = {
                    proj["mongo_project_id"]: proj["name"]
                    for proj in created_projects if proj.get("mongo_project_id")
                }
                task_list  = get_task(tenant_id=tenant_id, tenant_prefix=tenant_prefix, access_token=access_token)

                task_data = [
                    ["task_name", "description","assign_to","project","workflow_status","company","mongo_task_id"]
                ]

                for task in task_list:
                    mongo_proj_id = task.get("project", {}).get("_id", {}).get("$oid")

                    if not mongo_proj_id or mongo_proj_id not in project_id_map:
                        continue

                    frappe_project_name = project_id_map[mongo_proj_id]

                    assigned_to = (
                        task.get("assignedTo") and task.get("assignedTo", [{}])[0].get("_id", {}).get("$oid")
                    ) or None

                    task_data.append([
                        task.get("name"),
                        task.get("description", ""),
                        assigned_to,
                        frappe_project_name,
                        "Pending",
                        company_name,
                        task.get("_id", {}).get("$oid")
                    ])

                csv_buffer_task = io.StringIO()
                writer_task = csv.writer(csv_buffer_task)
                for row in task_data:
                    writer_task.writerow(row)
                csv_buffer_task.seek(0)

                file_doc_task = save_file(
                    fname="task_import.csv",
                    content=csv_buffer_task.getvalue(),
                    dt=None,
                    dn=None,
                    folder="Home",
                    decode=False,
                    is_private=0
                )
                frappe.db.commit()

                # Step 5: Create Data Import record
                import_doc_task = frappe.get_doc({
                    "doctype": "Data Import",
                    "reference_doctype": "Task",
                    "import_type": "Insert New Records",
                    "import_file": file_doc_task.file_url,
                    "submit_after_import": 0,
                    "overwrite": 0,
                    "ignore_encoding_errors": 1
                })
                import_doc_task.save()
                frappe.db.commit()

                start_import(import_doc_task.name)

                status_info_task = get_import_status(import_doc_task.name)

                if status_info_task.get("status") == "Success":
                    return {
                        "status": "success",
                        "message": f"Imported data of task and project done"
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Task Import failed project",
                        "details": status_info_task.get("messages")
                    }
            else:
                return {
                    "status": "error",
                    "message": "Project and Task Import failed project",
                    "details": status_info.get("messages")
                }


        else:
            return {
                "status": "error",
                "message": "Something went wrong!"
            }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "automated_import_project failed")
        return {
            "status": "error",
            "message": "An error occurred during project import",
            "error": str(e)
        }
    

def get_task(tenant_id, tenant_prefix, access_token):
    try:
        filter_query = {"tenant._id": {"$oid": tenant_id}}
        url = f"{DATA_API_URL}/{tenant_prefix}_tasks?filter={urllib.parse.quote(json.dumps(filter_query))}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "No-Auth-Challenge": "true",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            tasks = response.json()
            return tasks
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "tasks get failed")
        return {
            "status": "error",
            "message": "An error occurred during tasks get",
            "error": str(e)
        }
    