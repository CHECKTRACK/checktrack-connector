import frappe
import jwt
import requests
import urllib.parse
import json
from frappe.model.meta import get_meta
from frappe.auth import LoginManager
from frappe import _
from frappe.utils.password import get_decrypted_password
from checktrack_connector.onboard_api import automated_import_users
from frappe.utils import get_url

@frappe.whitelist(allow_guest=True)
def sso_login(token):
    """Custom login using JWT token"""
    try:


        print("LOGINNNNNNNNNNNN--------------");

        # Decode JWT token
        secret_key = "e6H9QQMGBx33KaOd"
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"], audience="app.checktrack.dev")

        # Extract user information
        email = decoded.get("email")

        if not email:
            frappe.throw(_("Invalid JWT token"))

        # Check if the user exists in ERPNext
        try:
            user = frappe.get_doc("User", email)
        except frappe.DoesNotExistError:
            error_message = f"User {email} not found"
            frappe.log_error(error_message, "SSO Login Error")  # Log the error
            frappe.throw(error_message)

        # Authenticate the user
        login_manager = LoginManager()
        login_manager.user = user.name
        login_manager.post_login()

        frappe.response.update({
            "sid": frappe.session.sid,
            # "csrf-token": frappe.local.session.data
        })

    except jwt.ExpiredSignatureError:
        frappe.throw(_("JWT token has expired"))
        frappe.log_error(error_message, "SSO Login Error")
        frappe.throw(_(error_message))
    except Exception as e:
        frappe.log_error(str(e), "SSO Login Error")
        frappe.throw(str(e))

# Get API URLs from hooks with better error handling
try:
    USER_API_URL = frappe.get_hooks().get("user_api_url")
    DATA_API_URL = frappe.get_hooks().get("data_api_url")

    if isinstance(USER_API_URL, list) and USER_API_URL:
        USER_API_URL = USER_API_URL[0]
    if isinstance(DATA_API_URL, list) and DATA_API_URL:
        DATA_API_URL = DATA_API_URL[0]

except Exception as e:
    frappe.log_error(f"Error getting API URLs from hooks: {str(e)}", "API Configuration Error")

@frappe.whitelist(allow_guest=True)
def checktrack_integration(email, password=""):

    # Authenticate and get access token
    auth_url = f"{USER_API_URL}/login"
    auth_payload = {"email": email.strip().lower(), "password": password}
    HEADERS = {"Content-Type": "application/json"}

    try:
        auth_response = requests.post(auth_url, headers=HEADERS, json=auth_payload)

        if auth_response.status_code != 200:
            frappe.throw("CheckTrack intergation failed. Invalid email or password.")

        auth_data = auth_response.json()
        frappe.log_error(message=f"Auth response keys: {list(auth_data.keys())}", title="Auth Debug")

        access_token = auth_data.get("accessToken")
        tenant_id = auth_data.get("user", {}).get("works", [{}])[0].get("tenant", {}).get("_id", {}).get("$oid")

    except Exception as e:
        frappe.log_error(message=f"Error checking CheckTrack integration: {str(e)}", title="CheckTrack Integration Error")
        return {"exists": False, "message": f"Error: {str(e)}"}

    try:
        tenant_url = f"{DATA_API_URL}/tenants/{tenant_id}"
        tenant_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        tenant_response = requests.get(tenant_url, headers=tenant_headers)
        tenant_data = tenant_response.json()

    except Exception as e:
        frappe.log_error(message=f"Error checking CheckTrack integration: {str(e)}", title="CheckTrack Integration Error")
        return {"exists": False, "message": f"Error: {str(e)}"}

    try:
        mapped_data = map_tenant_data(tenant_data)

        tenant_id = mapped_data.get("data", {}).get("tenant_id")
        tenant_prefix = mapped_data.get("data", {}).get("prefix")
        company_name = mapped_data.get("data", {}).get("company_name")

        company_result = {}

        new_company = frappe.get_doc({
                "doctype": "Company",
                **mapped_data["data"]
            })
        new_company.insert(ignore_permissions=True)
        company_result = {"status": "created", "tenant_id": tenant_id, "message": "Company created successfully"}

        team_members_result = fetch_and_create_team_members(tenant_id, tenant_prefix, access_token, company_name)

        if team_members_result.get("status") == "error" or team_members_result.get("rollback_status") == True:
            try:
                if frappe.db.exists("Company", company_name):
                    company_doc = frappe.get_doc("Company", company_name)
                    company_doc.delete(ignore_permissions=True)
                    frappe.db.commit()
                    company_result = {"status": "error", "tenant_id": tenant_id, "message": "Company removed due to employee creation failure"}

                    frappe.throw(_("Something went wrong!"), indicator="red")
                    return {
                        "tenant": company_result,
                        "team_members": team_members_result,
                        "is_fully_integration": False
                    }
            except Exception as e:
                frappe.throw(_("Something went wrong!"), indicator="red")

        is_fully_integration = team_members_result.get("status") == "success"

        return {
            "tenant": company_result,
            "team_members": team_members_result,
            "is_fully_integration": is_fully_integration
        }

    except Exception as e:
        frappe.log_error(message=f"Error checking CheckTrack integration: {str(e)}", title="CheckTrack Integration Error")
        return {"exists": False, "message": f"Error: {str(e)}"}

@frappe.whitelist()
def fetch_and_create_team_members(tenant_id, tenant_prefix, access_token, company_name):
    try:
        fetch_result = get_all_team_members(tenant_id, tenant_prefix, access_token)
        team_members_data = fetch_result.get("data")

        if not team_members_data:
            return {
                "status": "warning",
                "message": "No team members found for this company"
            }

        create_result = create_all_team_members(team_members_data, company_name)
        update_all_team_members(team_members_data, company_name)


        if create_result.get("status") != "success":
            return create_result

        user_import_result = automated_import_users(tenant_id=company_name)
        if user_import_result.get("status") == "success":
            update_mongodb_tenant_flag(tenant_id,access_token)
            return create_result

        if user_import_result.get("status") != "success":
            rollback_team_members(create_result.get("new_member_ids", []))  # Rollback team members
            frappe.msgprint(_("User import failed. Rolling back created team members."), indicator="red")

            return {
                "status": "error",
                "rollback_status": True,
                "message": "User import failed after team member creation",
                "import_error": user_import_result
            }

        return create_result

    except Exception as e:
        return {
            "status": "error",
            "rollback_status": True,
            "message": f"Exception: {str(e)}"
        }

@frappe.whitelist()
def get_all_team_members(tenant_id, tenant_prefix, access_token):
    try:
        limit = 1000
        filter_query = {"tenant._id": {"$oid": tenant_id}}
        url = f"{DATA_API_URL}/{tenant_prefix}_team_members?filter={urllib.parse.quote(json.dumps(filter_query))}&pagesize={limit}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "No-Auth-Challenge": "true",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            team_members_data = response.json()
            if isinstance(team_members_data, list):
                return {
                    "status": "success",
                    "message": f"Successfully fetched {len(team_members_data)} team members",
                    "data": team_members_data
                }
            else:
                return {
                    "status": "error",
                    "rollback_status": True,
                    "message": "Something went wrong!"
                }
        else:
            return {
                "status": "error",
                "rollback_status": True,
                "message": "Something went wrong!"
            }

    except Exception as e:
        return {
            "status": "error",
            "rollback_status": True,
            "message": "Something went wrong!"
        }

@frappe.whitelist()
def create_all_team_members(team_members_data, company_name):
    if not isinstance(team_members_data, list):
        team_members_data = frappe.parse_json(team_members_data)

    successfully_processed_ids = []
    already_existing_ids = []
    total_members = len(team_members_data)
    processing_count = 0
    should_rollback = False
    rollback_reason = ""
    rollback_results = []

    try:
        for member_data in team_members_data:
            try:
                processing_count += 1

                if "_id" in member_data and not "teammember_id" in member_data:
                    member_data = map_team_member_data(member_data, company_name,False)

                result = create_team_member(member_data)

                if result.get("already_exists"):
                    already_existing_ids.append(result["data"]["name"])
                else:
                    successfully_processed_ids.append(result["data"]["name"])

            except Exception as e:
                error_msg = str(e)
                teammember_id = member_data.get('teammember_id', 'unknown')
                should_rollback = True
                rollback_reason = f"Error processing employee: {teammember_id} - {error_msg}"
                break

        if should_rollback and successfully_processed_ids:
            rollback_results = rollback_team_members(successfully_processed_ids)
            frappe.msgprint(_("Something went wrong!"), indicator="red")

            return {
                "status": "error",
                "rollback_status": True,
                "message": rollback_reason,
                "rollback_results": rollback_results,
                "processed_before_error": len(successfully_processed_ids),
            }

        return {
            "status": "success",
            "rollback_status": False,
            "message": f"Successfully created {len(successfully_processed_ids)} employee, {len(already_existing_ids)} already existed",
            "team_members": successfully_processed_ids + already_existing_ids,
            "new_members": len(successfully_processed_ids),
            "new_member_ids": successfully_processed_ids  # Add this line
        }

    except Exception as e:
        rollback_reason = f"Unexpected error in create all employee: {str(e)}"
        frappe.msgprint(_("Something went wrong!"), indicator="red")

        if successfully_processed_ids:
            rollback_results = rollback_team_members(successfully_processed_ids)

        return {
            "status": "error",
            "rollback_status": True,
            "message": rollback_reason,
            "rollback_results": rollback_results,
            "processed_before_error": len(successfully_processed_ids),
        }
    finally:
        if should_rollback and successfully_processed_ids and not rollback_results:
            rollback_results = rollback_team_members(successfully_processed_ids)

@frappe.whitelist()
def update_all_team_members(team_members_data, company_name):
    if not isinstance(team_members_data, list):
        team_members_data = frappe.parse_json(team_members_data)

    try:
        for member_data in team_members_data:
            try:
                if "_id" in member_data and not "teammember_id" in member_data:
                    member_data = map_team_member_data(member_data, company_name, True)

                result = update_team_member(member_data)

            except Exception as e:
                break

        return {
            "status": "success",
            "message": f"Successfully update employee",
            "result": result
        }

    except Exception as e:
        reason = f"Unexpected error in update employee: {str(e)}"
        frappe.msgprint(_("Something went wrong!"), indicator="red")

        return {
            "status": "error",
            "message": reason,
        }

@frappe.whitelist()
def create_team_member(data):
    try:
        if not isinstance(data, dict):
            data = frappe.parse_json(data)

        teammember_id = data.get('teammember_id')

        new_member = frappe.get_doc({
            "doctype": "Employee",
            **data
        })
        new_member.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "data": {
                "name": new_member.name,
                "teammember_id": teammember_id
            }
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.throw(f"Something went wrong!")

@frappe.whitelist()
def update_team_member(data):
    try:
        teammember_id = data.get('teammember_id')
        if not teammember_id:
            frappe.throw("teammember_id is required.")

        existing_member = frappe.db.get_value("Employee", {"teammember_id": teammember_id}, "name")

        if not existing_member:
            frappe.throw(f"No Employee found with teammember_id {teammember_id}")

        employee = frappe.get_doc("Employee", existing_member)

        if "reports_to" in data and data["reports_to"] == employee.name:
            return

        for field, value in data.items():
            if employee.meta.has_field(field):
                employee.set(field, value)

        employee.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "data": {
                "name": employee.name,
                "teammember_id": teammember_id,
                "update": True
            }
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.throw(f"Something went wrong!")



def rollback_team_members(processed_ids):
    rollback_results = []
    for member_id in processed_ids:
        try:
            if frappe.db.exists("Employee", member_id):
                doc = frappe.get_doc("Employee", member_id)
                doc.delete(ignore_permissions=True)
                frappe.db.commit()
                rollback_results.append({
                    "id": member_id,
                    "status": "success",
                    "rollback_status": True,
                    "message": f"Rollback successful: Deleted Team Member ID {member_id}"
                })
            else:
                rollback_results.append({
                    "id": member_id,
                    "status": "warning",
                    "rollback_status": True,
                    "message": f"Team Member ID {member_id} not found for rollback"
                })
        except Exception as e:
            rollback_results.append({
                "id": member_id,
                "status": "error",
                "rollback_status": True,
                "message": f"Rollback error for Team Member ID {member_id}: {str(e)}"
            })

    return rollback_results

def map_tenant_data(input_data):

    if isinstance(input_data, list) and input_data:
        input_data = input_data[0]

    tenant_id = input_data.get('_id', {}).get('$oid') if isinstance(input_data.get('_id'), dict) else str(input_data.get('_id'))

    phone_data = input_data.get('phone', {})
    dial_code = phone_data.get('dialCode', '')
    phone_number = phone_data.get('phoneNumber', '')
    if phone_number and dial_code and phone_number.startswith(dial_code):
        phone_number = phone_number[len(dial_code):]
    formatted_phone = f"{dial_code}-{phone_number}" if dial_code and phone_number else phone_number

    return {
        "data": {
            "tenant_id": tenant_id,
            "prefix": input_data.get('prefix', ''),
            "phone": formatted_phone,
            "timezone": input_data.get('timezone', ''),
            "features": [{"features": feature} for feature in input_data.get('featuresList', [])],
            "company_name": input_data.get('name', ''),
            "date_format": input_data.get('dateFormat', ''),
            "no_of_employee": str(input_data.get('noOfEmployee', 0)),
            "work_location": [
                {
                    "address": location.get('address', ''),
                    "country": location.get('country', ''),
                    "state": location.get('state', ''),
                    "city": location.get('city', ''),
                    "pincode": str(location.get('pincode', ''))
                }
                for location in input_data.get('workLocation', [])
            ]
        }
    }

def map_team_member_data(input_data, company_name, updateEmployee):

    phone_data = input_data.get('phone', {})
    dial_code = phone_data.get('dialCode', '')
    phone_number = phone_data.get('phoneNumber', '')
    if phone_number and dial_code and phone_number.startswith(dial_code):
        phone_number = phone_number[len(dial_code):]
    formatted_phone = f"{dial_code}-{phone_number}" if dial_code and phone_number else phone_number

    start_date = ""
    if input_data.get('startDate', {}).get('$date'):
        try:
            from datetime import datetime
            timestamp = input_data['startDate']['$date']
            if isinstance(timestamp, int):
                start_date = datetime.fromtimestamp(timestamp/1000 if timestamp > 9999999999 else timestamp).isoformat()
        except Exception as e:
            frappe.log_error(f"Error formatting start date: {str(e)}", "Date Conversion Error")

    termination_date = None
    if input_data.get('terminationDate', {}).get('$date'):
        try:
            from datetime import datetime
            timestamp = input_data['terminationDate']['$date']
            if isinstance(timestamp, int):
                termination_date = datetime.fromtimestamp(timestamp/1000 if timestamp > 9999999999 else timestamp).isoformat()
        except Exception as e:
            frappe.log_error(f"Error formatting termination date: {str(e)}", "Date Conversion Error")

    if updateEmployee:
        return {
            'teammember_id': input_data.get('_id', {}).get('$oid') if isinstance(input_data.get('_id'), dict) else str(input_data.get('_id', '')),
            'reports_to': input_data.get('reportsTo', {}).get('_id', {}).get('$oid') if isinstance(input_data.get('reportsTo', {}).get('_id'), dict) else str(input_data.get('reportsTo', {}).get('_id', '')),
        }

    return {
        'teammember_id': input_data.get('_id', {}).get('$oid') if isinstance(input_data.get('_id'), dict) else str(input_data.get('_id', '')),
        'company': company_name,
        'first_name': input_data.get('firstName', ''),
        'last_name': input_data.get('lastName', ''),
        'work_email': input_data.get('workEmail', ''),
        'phone': formatted_phone,
        'employment_type': input_data.get('employmentType', ''),
        'job_title': input_data.get('jobTitle', ''),
        'start_date': start_date,
        'status': input_data.get('status', ''),
        'timezone': input_data.get('timezone', ''),
        'address': [
            {
                'address': input_data.get('addressDetails', {}).get('address', ''),
                'country': input_data.get('addressDetails', {}).get('country', ''),
                'state': input_data.get('addressDetails', {}).get('state', ''),
                'city': input_data.get('addressDetails', {}).get('city', ''),
                'pincode': str(input_data.get('addressDetails', {}).get('pincode', '')),
            }
        ],
        'termination_date': termination_date,
    }

# SECRET_KEY = "e6H9QQMGBx33KaOd"

# @frappe.whitelist(allow_guest=True)
# def sso_login():
#     """SSO login using token in Authorization header"""
#     print("SSO LOGINNNNNNNNNNNN--------------")
#     try:
#         # Extract token from Authorization header
#         auth_header = frappe.get_request_header("Authorization")

#         print("Authorization header :", auth_header)
#         if not auth_header:
#             frappe.throw(_("Authorization header is missing"))

#         # Expecting the header to have the format: Bearer <token>
#         if not auth_header.startswith("Bearer "):
#             frappe.throw(_("Invalid Authorization header format"))

#         token = auth_header.split(" ")[1]  # Extract the token part

#         # Decode and verify the JWT token
#         print("Token :", token)
#         decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], audience="app.checktrack.dev")
#         email = decoded_token.get("email")

#         if not email:
#             frappe.throw(_("Invalid token: email is missing"))

#         # Check if the user exists in ERPNext

#         user = frappe.get_doc("User", email)
#         print("User :", user)
#         print("decoded token :", decoded_token)
#         if not user:
#             frappe.throw(_("User not found or is disabled"))

#         # Log in the user
#         login_manager = LoginManager()
#         login_manager.user = user.name
#         login_manager.post_login()

#         # Return success response
#         return {"message": "Login successful", "user": user.name}

#     except jwt.ExpiredSignatureError:
#         frappe.throw(_("Token has expired"))
#     except jwt.InvalidTokenError:
#         frappe.throw(_("Invalid token"))
#     except Exception as e:
#         frappe.throw(str(e))



# @frappe.whitelist(allow_guest=True)
# def sync_user(email, first_name, last_name):
#     """Sync users from CheckTrack to Frappe"""
#     if frappe.db.exists("User", email):
#         return {"message": "User already exists"}

#     user = frappe.get_doc({
#         "doctype": "User",
#         "email": email,
#         "first_name": first_name,
#         "last_name": last_name,
#         "enabled": 1
#     })
#     user.insert(ignore_permissions=True)
#     return {"message": "User synced successfully"}

@frappe.whitelist(allow_guest=True)
def check_tenant_exists(email, password=""):
    """
    Check if a tenant already exists for the given credentials.
    This function authenticates with the credentials but does not create any records.
    Returns: True if tenant exists and is fully intgration, False otherwise
    """
    if not email or not password:
        return {"exists": False}
    auth_url = f"{USER_API_URL}/login"
    auth_payload = {"email": email.strip().lower(), "password": password}
    HEADERS = {"Content-Type": "application/json"}

    try:
        auth_response = requests.post(auth_url, headers=HEADERS, json=auth_payload)

        if auth_response.status_code != 200:
            return {"exists": False, "message": "CheckTrack intergation failed. Invalid email or password."}

        auth_data = auth_response.json()

        access_token = auth_data.get("accessToken")
        company_name = auth_data.get("tenant", {}).get("name")

        if not access_token or not company_name:
            return {"exists": False, "message": "Failed to get company information."}

        if frappe.db.exists("Company", company_name):
            team_members_count = frappe.db.count("Employee", {"company": company_name})

            if team_members_count > 0:
                return {
                    "exists": True,
                    "tenant_id": company_name,
                    "team_members_count": team_members_count,
                    "message": f"Company exists with {team_members_count} employee"
                }
            else:
                return {
                    "exists": True,
                    "tenant_id": company_name,
                    "team_members_count": 0,
                    "message": "Company exists but has no employee"
                }
        else:
            return {"exists": False, "message": "Company does not exist in the system"}

    except Exception as e:
        frappe.log_error(message=f"Error checking company exists: {str(e)}", title="Employee Check Error")
        return {"exists": False, "message": f"Error: {str(e)}"}

@frappe.whitelist(allow_guest=True)
def get_decrypted_password_for_doc(docname):
    try:
        raw_password = frappe.db.get_value("CheckTrack Integration", docname, "password")

        if not raw_password:
            return None

        password = get_decrypted_password("CheckTrack Integration", docname, "password")

        if not password:
            return None

        return password
    except Exception as e:
        frappe.log_error(f"Error decrypting password for {docname}: {str(e)}", "CheckTrack Error")
        return {"error": "Could not decrypt password due to an internal error."}


@frappe.whitelist(allow_guest=True)
def get_doc_data_list(doctype, filters=None):
    filters = json.loads(filters) if filters else {}
    docs = frappe.get_all(doctype, filters=filters, fields=["*"])

    def expand_links(doc_dict, doctype_name):
        meta = frappe.get_meta(doctype_name)
        for field in meta.fields:
            value = doc_dict.get(field.fieldname)

            if field.fieldtype == "Link" and value:
                try:
                    linked_doc = frappe.get_doc(field.options, value)
                    doc_dict[field.fieldname] = linked_doc.as_dict()
                except:
                    pass

            elif field.fieldtype == "Dynamic Link" and value:
                dynamic_doctype = doc_dict.get(field.options)
                if dynamic_doctype:
                    try:
                        linked_doc = frappe.get_doc(dynamic_doctype, value)
                        doc_dict[field.fieldname] = expand_links(linked_doc.as_dict(), dynamic_doctype)
                    except:
                        pass

            elif field.fieldtype in ["Table", "Table MultiSelect"] and isinstance(value, list):
                child_doctype = field.options
                try:
                    child_docs = frappe.get_all(child_doctype, filters={
                        "parent": doc_dict.get("name"),
                        "parenttype": doctype_name,
                        "parentfield": field.fieldname
                    }, fields=["*"])
                    expanded_children = []
                    for child_doc in child_docs:
                        child_doc_expanded = expand_links(child_doc, child_doctype)
                        expanded_children.append(child_doc_expanded)
                    doc_dict[field.fieldname] = expanded_children
                except:
                    pass
        return doc_dict

    result = []
    for doc in docs:
        full_doc = frappe.get_doc(doctype, doc.name).as_dict()
        result.append(expand_links(full_doc, doctype))

    return {"data": result}

@frappe.whitelist()
def get_expanded_doc(doctype, name):
    doc = frappe.get_doc(doctype, name).as_dict()
    meta = get_meta(doctype)

    def expand_field(field, value):
        
        if field.fieldtype == "Link" and value:
            return value

        if field.fieldtype == "Dynamic Link" and value:
            doctype_field = field.options
            link_doctype = doc.get(doctype_field)
            if link_doctype and value:
                try:
                    return frappe.get_doc(link_doctype, value).as_dict()
                except:
                    return value

        if field.fieldtype in ("Table", "Table MultiSelect") and isinstance(value, list):
            child_table = []
            for row in value:
                row_meta = get_meta(field.options)
                expanded_row = row.copy()
                for child_field in row_meta.fields:
                    val = row.get(child_field.fieldname)
                    if child_field.fieldtype in ("Link", "Dynamic Link"):
                        expanded_row[child_field.fieldname] = expand_field(child_field, val)
                child_table.append(expanded_row)
            return child_table

        return value

    expanded_doc = {}
    for field in meta.fields:
        val = doc.get(field.fieldname)
        expanded_doc[field.fieldname] = expand_field(field, val)

    return {"data": expanded_doc}

@frappe.whitelist(allow_guest=True)
def get_specific_doc_data(doctype, name=None, filters=None):
    if name:
        try:
            doc = frappe.get_doc(doctype, name)
            full_doc = doc.as_dict()
            expanded_doc = expand_links(full_doc, doctype)
            return {"data": expanded_doc}
        except Exception as e:
            frappe.log_error(f"Error fetching specific document: {str(e)}")
            return {"message": f"Error fetching specific document: {str(e)}"}
    else:
        filters = json.loads(filters) if filters else {}
        docs = frappe.get_all(doctype, filters=filters, fields=["*"])

        result = []
        for doc in docs:
            full_doc = frappe.get_doc(doctype, doc.name).as_dict()
            result.append(expand_links(full_doc, doctype))

        return {"data": result}

def expand_links(doc_dict, doctype_name):
    """Recursively expands all Link fields in a document"""
    meta = frappe.get_meta(doctype_name)
    for field in meta.fields:
        value = doc_dict.get(field.fieldname)

        if field.fieldtype == "Link" and value:
            try:
                linked_doc = frappe.get_doc(field.options, value)
                doc_dict[field.fieldname] = linked_doc.as_dict()
            except:
                pass

        elif field.fieldtype == "Dynamic Link" and value:
            dynamic_doctype = doc_dict.get(field.options)
            if dynamic_doctype:
                try:
                    linked_doc = frappe.get_doc(dynamic_doctype, value)
                    doc_dict[field.fieldname] = expand_links(linked_doc.as_dict(), dynamic_doctype)
                except:
                    pass

        elif field.fieldtype in ["Table", "Table MultiSelect"] and isinstance(value, list):
            child_doctype = field.options
            try:
                expanded_children = []
                for row in value:
                    expanded_row = expand_links(row, child_doctype)
                    expanded_children.append(expanded_row)
                doc_dict[field.fieldname] = expanded_children
            except:
                pass
    return doc_dict

def update_mongodb_tenant_flag(tenant_id, access_token):
    try:
        tenant_url = f"{DATA_API_URL}/tenants/{tenant_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "isFrappeIntegrated": True
        }

        response = requests.patch(tenant_url, headers=headers, json=payload)

        if response.status_code in [200, 204]:
            frappe.logger().info(f"CheckTrack: Tenant {tenant_id} updated with isFrappeIntegrated = true")
        else:
            frappe.logger().warn(f"CheckTrack: Failed to update tenant {tenant_id}. Status: {response.status_code}, Response: {response.text}")

    except Exception as e:
        frappe.log_error(str(e), "CheckTrack Tenant Update Error")


@frappe.whitelist(allow_guest=True)
def login_with_checktrack_jwt(token: str):
    try:
        secret_key = "e6H9QQMGBx33KaOd"  # Use your secret
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"], audience="app.checktrack.dev")

        email = decoded.get("email")
        if not email:
            frappe.throw(_("Invalid JWT token"))

        if not frappe.db.exists("User", email):
            frappe.throw(_("User {0} not found").format(email))

        # Authenticate user
        login_manager = LoginManager()
        login_manager.user = email
        login_manager.post_login()

        frappe.response.update({
            "sid": frappe.session.sid,
            "message": "Login successful",
            "redirect_to": f"https://checktrack-dev.frappe.cloud/app?sid={frappe.session.sid}"
        })

    except jwt.ExpiredSignatureError:
        frappe.throw(_("JWT token has expired"))
    except Exception as e:
        frappe.log_error(str(e), "SSO Login Error")
        frappe.throw(str(e))



@frappe.whitelist(allow_guest=True)
def get_frappe_sid_if_integrated(access_token: str, tenant_id: str):
    try:
        # 1. Get tenant info from CheckTrack via DATA_API
        tenant_url = f"{DATA_API_URL}/tenants/{tenant_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(tenant_url, headers=headers)
        if response.status_code != 200:
            frappe.throw(_("Failed to fetch tenant information from CheckTrack."))

        tenant_data = response.json()

        if not tenant_data.get("isFrappeIntegrated"):
            frappe.throw(_("Tenant is not yet integrated with Frappe."))

        # 2. Get first team member’s email (or handle this logic based on your needs)
        team_member = frappe.get_all(
            "Team Member",
            filters={"tenant": tenant_id},
            fields=["work_email"],
            limit=1
        )

        if not team_member:
            frappe.throw(_("No associated team members found in Frappe."))

        user_email = team_member[0].get("work_email")

        if not frappe.db.exists("User", user_email):
            frappe.throw(_("Frappe user not found for {0}").format(user_email))

        # 3. Log in as this user and return SID
        login_manager = LoginManager()
        login_manager.user = user_email
        login_manager.post_login()

        return frappe.session.sid  # Return string as required for Flutter

    except Exception as e:
        frappe.log_error(str(e), "get_frappe_sid_if_integrated Error")
        frappe.throw(str(e))


def update_related_tasks(doc, method):
    """
    This function is triggered when a Demo PM Task document is updated.
    It looks up all Task documents that reference this Demo PM Task (via the dynamic Link field) 
    and updates their status to match the updated document.
    """
    # Check if the status field has changed. Optionally, you can compare with the previous value.
    # For example, if you want to restrict updates only when status truly changes,
    # you can use doc.get_doc_before_save() if available.

    # Fetch all Task documents where:
    # - the 'type' field equals the name of the Task_Type_Doc (e.g., "Demo PM Task")
    # - the 'task_type_doc' field equals the name of this document (doc.name)
    tasks = frappe.get_all("Task",
        filters={
            "type": doc.doctype,
            "task_type_doc": doc.name
        },
        fields=["name"]
    )

    # Iterate through each task and update its status field
    for task in tasks:
        frappe.db.set_value("Task", task.name, "status", doc.status)
        # Alternatively, if you want the document to be reloaded and triggers to fire, use:
        task_doc = frappe.get_doc("Task", task.name)
        task_doc.status = doc.status
        task_doc.save()