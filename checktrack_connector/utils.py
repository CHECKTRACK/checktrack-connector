import frappe

def validate_cors():
    """Set CORS headers for all requests and allow all origins."""
    print("CORS middleware executed")
    
    # Allow all origins
    frappe.local.response["headers"].update({
        "Access-Control-Allow-Origin": "*",   # Allow all origins
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Requested-With, Accept",
        "Access-Control-Allow-Credentials": "true",
    })

@frappe.whitelist(allow_guest=True)
def handle_preflight():
    """Handle preflight requests for CORS with all origins allowed."""
    if frappe.request.method == "OPTIONS":
        frappe.local.response["headers"].update({
            "Access-Control-Allow-Origin": "*",   # Allow all origins
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Requested-With, Accept",
            "Access-Control-Allow-Credentials": "true",
        })
        frappe.local.response["type"] = "binary"
        frappe.local.response["status_code"] = 200
        return ""

def add_cors_headers(response):
    """Add CORS headers to the response with all origins allowed."""
    print("CORS middleware executed")

    # Allow all origins
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Requested-With, Accept"
    response.headers["Access-Control-Allow-Credentials"] = "true"

    return response