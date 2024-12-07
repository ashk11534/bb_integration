from odoo import models, fields


class ExtendedResCompany(models.Model):
    _inherit = "res.company"

    org_name = fields.Char(string="Organization", required=True, default="Build Best")
    short_code = fields.Char(string="Short Code", required=True, default="N/A")
