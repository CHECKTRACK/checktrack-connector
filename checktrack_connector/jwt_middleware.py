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
    "/api/resource"
]

def authenticate_jwt_token():
    # 1. Basic checks: Is it an API request? Is user already authenticated?
    # Ensure it's an API request AND that the request path is in our secure list
    # Use .startswith() for general paths (like modules or resources) or exact match for specific methods
    is_secure_path = False
    for path_prefix in SECURE_API_PATHS:
        if frappe.request.path.startswith(path_prefix): # Checks for prefix or exact match
            is_secure_path = True
            break

    if not is_secure_path:
        # This path is not in our list of secure paths, so let Frappe's default authentication handle it.
        return

    
    # If the path is secure and the user is already authenticated by Frappe's native session/API Key, skip.
    # This prevents double authentication and ensures existing Frappe auth works.
    if frappe.session.user and frappe.session.user != "Guest":
        return

    # 2. Extract JWT from Authorization header
    auth_header = frappe.request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        # If the path requires JWT, but no valid Bearer token is provided, raise an error.
        raise AuthenticationError("Authentication required: Bearer token missing or invalid for this secure endpoint.")

    jwt_token = auth_header.split("Bearer ")[1]

    print(jwt_token)

    # 3. Validate JWT and set user
    try:
        decoded_jwt = jwt.decode(
            jwt_token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=EXPECTED_AUDIENCE,
            options={"verify_aud": True}
        )

        user_email = decoded_jwt.get("email")
        if not user_email:
            raise AuthenticationError("JWT does not contain a valid user identifier (e.g., 'email').")

        user_name = frappe.db.get_value("User", {"email": user_email}, "name")

        if not user_name:
            raise AuthenticationError(f"Frappe user for email '{user_email}' not found.")

        # Set the Frappe session user based on the validated JWT
        frappe.set_user(user_name)
        frappe.logger("jwt_auth").info(f"User {user_name} authenticated via JWT middleware for {frappe.request.path}")

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("JWT has expired.")
    except jwt.InvalidAudienceError:
        raise AuthenticationError("Invalid JWT: Invalid audience.")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid JWT: {e}")
    except Exception as e:
        frappe.logger("jwt_auth").error(frappe.get_traceback(), "JWT Middleware Error")
        raise AuthenticationError(f"An unexpected error occurred during JWT authentication: {e}")