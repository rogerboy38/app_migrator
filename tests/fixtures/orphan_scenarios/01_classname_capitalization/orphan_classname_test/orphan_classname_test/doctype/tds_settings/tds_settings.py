import frappe
from frappe.model.document import Document


class TdsSettings(Document):  # WRONG: should be TDSSettings to preserve acronym
    pass
