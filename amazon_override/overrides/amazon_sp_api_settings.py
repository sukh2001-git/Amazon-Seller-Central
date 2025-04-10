# -*- coding: utf-8 -*-
"""
Amazon SP API Settings Override
This module overrides the Amazon SP API Settings doctype to customize
the behavior of the Amazon SP API integration.
It includes custom validation for credentials, order details retrieval,
and custom field setup.
"""

from datetime import datetime

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.document import Document
from frappe.utils import add_days, today
from ecommerce_integrations.amazon.doctype.amazon_sp_api_settings.amazon_sp_api_settings import AmazonSPAPISettings as BaseAmazonSPAPISettings


class AmazonSPAPISettings(BaseAmazonSPAPISettings):
    def validate(self):
        """Override to skip AWS credential validation"""
        self.validate_amazon_fields_map()
        self.validate_after_date()

        if self.is_active == 1:
            self.validate_credentials()
            setup_custom_fields()
        else:
            self.enable_sync = 0

        if not self.max_retry_limit:
            self.max_retry_limit = 1
        elif self.max_retry_limit and self.max_retry_limit > 5:
            frappe.throw(frappe._("Value for <b>Max Retry Limit</b> must be less than or equal to 5."))

    def validate_credentials(self):
        """Override to validate only OAuth credentials instead of AWS credentials"""
        from amazon_override.overrides.amazon_repository import validate_amazon_sp_api_credentials
        
        validate_amazon_sp_api_credentials(
            client_id=self.get("client_id"),
            client_secret=self.get_password("client_secret"),
            refresh_token=self.get("refresh_token"),
            country=self.get("country"),
        )

    @frappe.whitelist()
    def get_order_details(self):
        """Override to use custom amazon_repository implementation"""
        from amazon_override.overrides.amazon_repository import get_orders
        
        if self.is_active == 1:
            job_name = f"Get Amazon Orders - {self.name}"

            if frappe.db.get_all("RQ Job", {"job_name": job_name, "status": ["in", ["queued", "started"]]}):
                return frappe.msgprint(_("The order details are currently being fetched in the background."))

            frappe.enqueue(
                job_name=job_name,
                method=get_orders,
                amz_setting_name=self.name,
                created_after=self.after_date,
                timeout=4000,
                now=frappe.flags.in_test,
            )

            frappe.msgprint(_("Order details will be fetched in the background."))
        else:
            frappe.msgprint(
                _("Please enable the Amazon SP API Settings {0}.").format(frappe.bold(self.name))
            )


# Called via a hook in every hour - override to use your custom implementation
def schedule_get_order_details():
    from amazon_override.overrides.amazon_repository import get_orders
    
    amz_settings = frappe.get_all(
        "Amazon SP API Settings",
        filters={"is_active": 1, "enable_sync": 1},
        fields=["name", "after_date"],
    )

    for amz_setting in amz_settings:
        get_orders(amz_setting_name=amz_setting.name, created_after=amz_setting.after_date)


def setup_custom_fields():
    """Re-use the existing setup_custom_fields function"""
    custom_fields = {
        "Sales Order": [
            dict(
                fieldname="amazon_order_id",
                label="Amazon Order ID",
                fieldtype="Data",
                insert_after="title",
                read_only=1,
                print_hide=1,
            )
        ],
    }

    create_custom_fields(custom_fields)