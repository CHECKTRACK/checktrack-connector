import frappe
import jwt
import requests
import urllib.parse
import json
from frappe.auth import LoginManager
from frappe import _
from frappe.utils.password import get_decrypted_password
from checktrack_connector.onboard_api import automated_import_users  

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
def checktrack_integration(email, password):
        
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

        # Save tenant data in Frappe
        tenant_id = mapped_data.get("data", {}).get("tenant_id")
        tenant_prefix = mapped_data.get("data", {}).get("prefix")

        tenant_result = {}

        new_tenant = frappe.get_doc({
                "doctype": "Tenant",
                **mapped_data["data"]
            })
        new_tenant.insert(ignore_permissions=True)
        tenant_result = {"status": "created", "tenant_id": tenant_id, "message": "Tenant created successfully"}
                
        team_members_result = fetch_and_create_team_members(tenant_id, tenant_prefix, access_token)
        
        if team_members_result.get("status") == "error" or team_members_result.get("rollback_status") == True:
            try:
                if frappe.db.exists("Tenant", tenant_id):
                    tenant_doc = frappe.get_doc("Tenant", tenant_id)
                    tenant_doc.delete(ignore_permissions=True)
                    frappe.db.commit()
                    tenant_result = {"status": "error", "tenant_id": tenant_id, "message": "Tenant removed due to team member creation failure"}
                    
                    frappe.throw(_("Something went wrong!"), indicator="red")
                    return {
                        "tenant": tenant_result,
                        "team_members": team_members_result,
                        "is_fully_integration": False
                    }
            except Exception as e:
                frappe.throw(_("Something went wrong!"), indicator="red")
        
        # if team_members_result.get("status") == "success":
        #     new_members = team_members_result.get("new_members", len(team_members_result.get("team_members", [])))
        #     tenant_action = "updated" if tenant_result.get("status") == "updated" else "created"
        #     message = _(f"Successfully {tenant_action} tenant with {new_members} team members")
        #     frappe.msgprint(message, indicator="green")
            
        is_fully_integration = team_members_result.get("status") == "success"
        
        return {
            "tenant": tenant_result,
            "team_members": team_members_result,
            "is_fully_integration": is_fully_integration
        }
        
    except Exception as e:
        frappe.log_error(message=f"Error checking CheckTrack integration: {str(e)}", title="CheckTrack Integration Error")
        return {"exists": False, "message": f"Error: {str(e)}"}

@frappe.whitelist()
def fetch_and_create_team_members(tenant_id, tenant_prefix, access_token):
    try:
        fetch_result = get_all_team_members(tenant_id, tenant_prefix, access_token)
        team_members_data = fetch_result.get("data")
        
        if not team_members_data:
            return {
                "status": "warning",
                "message": "No team members found for this tenant"
            }

        create_result = create_all_team_members(team_members_data)

        if create_result.get("status") != "success":
            return create_result

        # ✅ Call automated_import_users with tenant_id
# Import correctly

        user_import_result = automated_import_users(tenant_id=tenant_id)
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
def create_all_team_members(team_members_data):
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
                # Removing the progress popup message
                # frappe.publish_progress(
                #     percent=int((processing_count / total_members) * 100),
                #     title=f"Processing team members ({processing_count}/{total_members})"
                # )
                
                if "_id" in member_data and not "teammember_id" in member_data:
                    member_data = map_team_member_data(member_data)
                
                result = create_team_member(member_data)
                
                if result.get("already_exists"):
                    already_existing_ids.append(result["data"]["name"])
                else:
                    successfully_processed_ids.append(result["data"]["name"])
                
            except Exception as e:
                error_msg = str(e)
                teammember_id = member_data.get('teammember_id', 'unknown')
                should_rollback = True
                rollback_reason = f"Error processing team member: {teammember_id} - {error_msg}"
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
            "message": f"Successfully created {len(successfully_processed_ids)} team members, {len(already_existing_ids)} already existed",
            "team_members": successfully_processed_ids + already_existing_ids,
            "new_members": len(successfully_processed_ids),
            "new_member_ids": successfully_processed_ids  # Add this line
        }
        
    except Exception as e:
        rollback_reason = f"Unexpected error in create_all_team_members: {str(e)}"
        frappe.msgprint(_("Something went wrong!"), indicator="red")
        
        # Always rollback if there are any successfully processed members
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
def create_team_member(data):
    try:
        if not isinstance(data, dict):
            data = frappe.parse_json(data)
        
        teammember_id = data.get('teammember_id')
        
        new_member = frappe.get_doc({
            "doctype": "Team Member",
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

def rollback_team_members(processed_ids):
    rollback_results = []
    for member_id in processed_ids:
        try:
            if frappe.db.exists("Team Member", member_id):
                doc = frappe.get_doc("Team Member", member_id)
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

def map_team_member_data(input_data):
    
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

    return {
        'teammember_id': input_data.get('_id', {}).get('$oid') if isinstance(input_data.get('_id'), dict) else str(input_data.get('_id', '')),
        'tenant': input_data.get('tenant', {}).get('_id', {}).get('$oid') if isinstance(input_data.get('tenant', {}).get('_id'), dict) else str(input_data.get('tenant', {}).get('_id', '')),
        'first_name': input_data.get('firstName', ''),
        'last_name': input_data.get('lastName', ''),
        'work_email': input_data.get('workEmail', ''),
        'phone': formatted_phone,
        'employment_type': input_data.get('employmentType', ''),
        'job_title': input_data.get('jobTitle', ''),
        'start_date': start_date,
        'status': input_data.get('status', ''),
        'timezone': input_data.get('timezone', ''),
        'report_to': input_data.get('reportsTo', {}).get('_id', {}).get('$oid') if isinstance(input_data.get('reportsTo', {}).get('_id'), dict) else str(input_data.get('reportsTo', {}).get('_id', '')),
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
def check_tenant_exists(email, password):
    """
    Check if a tenant already exists for the given credentials.
    This function authenticates with the credentials but does not create any records.
    Returns: True if tenant exists and is fully intgration, False otherwise
    """
    # Authenticate and get access token
    auth_url = f"{USER_API_URL}/login"
    auth_payload = {"email": email.strip().lower(), "password": password}
    HEADERS = {"Content-Type": "application/json"}

    try:
        auth_response = requests.post(auth_url, headers=HEADERS, json=auth_payload)

        if auth_response.status_code != 200:
            return {"exists": False, "message": "CheckTrack intergation failed. Invalid email or password."}

        auth_data = auth_response.json()
        
        access_token = auth_data.get("accessToken")
        tenant_id = auth_data.get("user", {}).get("works", [{}])[0].get("tenant", {}).get("_id", {}).get("$oid")

        if not access_token or not tenant_id:
            return {"exists": False, "message": "Failed to get tenant information."}

        # Check if tenant exists in Frappe
        if frappe.db.exists("Tenant", tenant_id):
            team_members_count = frappe.db.count("Team Member", {"tenant": tenant_id})
            
            if team_members_count > 0:
                return {
                    "exists": True, 
                    "tenant_id": tenant_id,
                    "team_members_count": team_members_count,
                    "message": f"Tenant exists with {team_members_count} team members"
                }
            else:
                return {
                    "exists": False,
                    "tenant_id": tenant_id,
                    "team_members_count": 0,
                    "message": "Tenant exists but has no team members"
                }
        else:
            return {"exists": False, "message": "Tenant does not exist in the system"}

    except Exception as e:
        frappe.log_error(message=f"Error checking tenant exists: {str(e)}", title="Tenant Check Error")
        return {"exists": False, "message": f"Error: {str(e)}"}

@frappe.whitelist(allow_guest=True)
def get_decrypted_password_for_doc(docname):
    try:
        password = get_decrypted_password("CheckTrack Integration", docname, "password")
        return password
    except Exception as e:
        frappe.log_error(f"Error decrypting password for {docname}: {str(e)}", "CheckTrack Error")
        return {"error": "Could not decrypt password"}

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
            "redirect_to": f"http://checktrack.test:8000?sid={frappe.session.sid}"
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