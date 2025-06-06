import io
import csv
import frappe
from frappe.utils.file_manager import save_file
from frappe.core.doctype.data_import.data_import import start_import, get_import_status


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