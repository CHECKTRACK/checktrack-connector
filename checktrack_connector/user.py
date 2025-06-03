import frappe
from frappe.utils import random_string
from frappe.utils.password import set_encrypted_password

def generate_api_credentials(doc, method):
    # Only generate if not already present
    if not doc.api_key:
        doc.api_key = random_string(15)
        doc.save(ignore_permissions=True)

    if not frappe.db.get_value("User", doc.name, "api_secret"):
        api_secret = random_string(30)
        set_encrypted_password("User", doc.name, api_secret, fieldname="api_secret")