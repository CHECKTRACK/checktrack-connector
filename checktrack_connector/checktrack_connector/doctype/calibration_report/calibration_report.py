import frappe
from frappe.model.document import Document
from frappe.utils.pdf import get_pdf

class CalibrationReport(Document):
    def before_save(self):
        all_within_range = True

        for row in self.parameters or []:
            try:
                span = float(row.span or 0)
                offline = float(row.offline or 0)
                if span != 0:
                    variation = round(((offline - span) / span) * 100, 2)
                    row.variation = variation
                    if abs(variation) > 5:
                        all_within_range = False
                else:
                    row.variation = 0
            except:
                row.variation = 0
                all_within_range = False

        self.result = "The calibration test pass." if all_within_range else "The calibration test failed."

    def after_insert(self):
        if self.customer_email:
            try:
                # Render HTML with specific letterhead and print format
                html = frappe.get_print(
                    self.doctype,
                    self.name,
                    print_format="Neer Instruments",
                    doc=self,
                    letterhead="Neer Instruments"
                )

                # Convert to PDF
                pdf_content = get_pdf(html)

                # Send Email
                frappe.sendmail(
                    recipients=[self.customer_email],
                    subject=f"Calibration Certificate - {self.name}",
                    message="Dear Customer,<br><br>Please find attached the calibration certificate.<br><br>Regards,<br>Neer Instruments",
                    attachments=[{
                        "fname": f"{self.name}.pdf",
                        "fcontent": pdf_content
                    }]
                )

            except Exception:
                frappe.log_error(frappe.get_traceback(), "Calibration Report Email Error")
