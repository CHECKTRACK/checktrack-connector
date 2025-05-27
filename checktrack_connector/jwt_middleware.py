import frappe
import jwt
from frappe.exceptions import AuthenticationError

# Configuration (from site_config.json)
JWT_SECRET = "e6H9QQMGBx33KaOd"
JWT_ALGORITHM = "HS256"
EXPECTED_AUDIENCE = "app.checktrack.dev"

# Define the paths for which JWT authentication is MANDATORY
# You can use full paths or partial paths (e.g., if you want all methods in a module)
# Examples:
# - "/api/resource/Sales Order": Only for Sales Order resource
# - "/api/method/my_custom_app.my_module": For all methods in my_module
# - "/api/method/checktrack_connector.api.authenticate_with_jwt_and_get_frappe_token": Your initial endpoint
# - "/api/method/frappe.client.get_logged_user": If you want this to be JWT protected
# - "/api/method/your_custom_secure_method": Specific custom method
# - "/api/resource/My Secure DocType": Specific custom DocType
SECURE_API_PATHS = [
    "/api/method/frappe.desk.form.load.getdoctype"
]

def authenticate_jwt_token():
    # --- TEMPORARY DEBUG LOG ---
    frappe.logger("jwt_auth").info(f"--- JWT Middleware START ---")
    frappe.logger("jwt_auth").info(f"Request Path: {frappe.request.path}")
    frappe.logger("jwt_auth").info(f"Request Method: {frappe.request.method}")
    frappe.logger("jwt_auth").info(f"Request Headers: {dict(frappe.request.headers)}")
    frappe.logger("jwt_auth").info(f"Current Frappe User (before middleware): {frappe.session.user}")
    frappe.logger("jwt_auth").info(f"--- JWT Middleware END DEBUG START ---")
    # --- END TEMPORARY DEBUG LOG ---

    is_secure_path = False
    for path_prefix in SECURE_API_PATHS:
        # Check for prefix match or exact match
        if frappe.request.path.startswith(path_prefix):
            is_secure_path = True
            break

    if not is_secure_path:
        frappe.logger("jwt_auth").info(f"Path {frappe.request.path} not in SECURE_API_PATHS. Skipping JWT auth.")
        return

    if frappe.session.user and frappe.session.user != "Guest":
        frappe.logger("jwt_auth").info(f"User {frappe.session.user} already authenticated. Skipping JWT auth.")
        return

    auth_header = frappe.request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        frappe.logger("jwt_auth").error(f"Secure path {frappe.request.path} requested, but no valid Bearer token provided.")
        raise AuthenticationError("Authentication required: Bearer token missing or invalid for this secure endpoint.")

    jwt_token = auth_header.split("Bearer ")[1]

    try:
        # ... (rest of your JWT validation and frappe.set_user logic) ...
        frappe.logger("jwt_auth").info(f"User {user_name} successfully authenticated via JWT for {frappe.request.path}")

    except jwt.ExpiredSignatureError:
        frappe.logger("jwt_auth").error(f"JWT expired for {frappe.request.path}")
        raise AuthenticationError("JWT has expired.")
    except jwt.InvalidAudienceError:
        frappe.logger("jwt_auth").error(f"Invalid JWT audience for {frappe.request.path}")
        raise AuthenticationError("Invalid JWT: Invalid audience.")
    except jwt.InvalidTokenError as e:
        frappe.logger("jwt_auth").error(f"General JWT invalidity for {frappe.request.path}: {e}")
        raise AuthenticationError(f"Invalid JWT: {e}")
    except AuthenticationError as e:
        frappe.logger("jwt_auth").error(f"JWT auth failed for {frappe.request.path}: {e}")
        raise
    except Exception as e:
        frappe.logger("jwt_auth").error(frappe.get_traceback(), f"Unexpected error in JWT middleware for {frappe.request.path}")
        raise AuthenticationError(f"An unexpected error occurred during JWT authentication: {e}")