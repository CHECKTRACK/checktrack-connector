import frappe
import jwt
from frappe.auth import LoginManager
from frappe import _

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