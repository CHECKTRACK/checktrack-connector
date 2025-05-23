import jwt
import frappe
from frappe import _
from frappe.sessions import Session

# def validate_jwt_token():
#     """Middleware to validate JWT token before processing requests."""
#     try:
#         # Extract the Authorization header
#         auth_header = frappe.get_request_header("Authorization", "").strip()

#         if not auth_header or not auth_header.startswith("Bearer "):
#             frappe.throw(_("Missing or invalid Authorization header"), frappe.AuthenticationError)

#         # Extract the token
#         token = auth_header.split(" ")[1]

#         # Decode the JWT token
#         secret_key = "your_jwt_secret"
#         decoded = jwt.decode(token, secret_key, algorithms=["HS256"])

#         # Validate the user exists in the system
#         email = decoded.get("email")
#         if not email or not frappe.db.exists("User", email):
#             frappe.throw(_("Invalid token or user does not exist"), frappe.AuthenticationError)

#         # Optionally, attach user info to the request context
#         frappe.local.user_email = email

#     except jwt.ExpiredSignatureError:
#         frappe.throw(_("Token has expired"), frappe.AuthenticationError)
#     except jwt.InvalidTokenError:
#         frappe.throw(_("Invalid token"), frappe.AuthenticationError)
#     except Exception as e:
#         frappe.throw(str(e), frappe.AuthenticationError)

def validate_jwt_middleware():
    """Middleware to validate JWT token for all requests"""
    token = frappe.get_request_header("Authorization")
    if not token or not token.startswith("Bearer "):
        frappe.throw(_("Authorization header missing or invalid"))

    try:
        token = token.split("Bearer ")[1]
        SECRET_KEY = "your_jwt_secret"
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], audience="app.checktrack.dev")
        frappe.set_user(decoded.get("email"))
    except jwt.ExpiredSignatureError:
        frappe.throw(_("Token has expired"))
    except jwt.InvalidTokenError:
        frappe.throw(_("Invalid token"))

def patch_session_from_authorization():
    sid = frappe.get_request_header("Authorization") or frappe.get_request_header("X-Frappe-SID")
    if sid and sid.startswith("sid="):
        sid = sid[4:]

    if sid:
        try:
            session = Session(None)
            session.sid = sid
            session.resume()

            # Assign to local context
            frappe.local.session = session
            frappe.local.session_obj = session
            frappe.local.session.sid = sid
            frappe.local.session.user = session.user

        except Exception as e:
            frappe.log_error(f"Failed to resume session from sid: {sid}\nError: {str(e)}")