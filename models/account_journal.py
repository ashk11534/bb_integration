from odoo import models, fields


class ExtendedAccountJournal(models.Model):
    _inherit = "account.journal"
    _rec_names_search = ["name", "code", "orcl_gl_code", "oracle_pointer"]

    orcl_gl_code = fields.Char(string="Oracle GL Code", index=True)
    oracle_pointer = fields.Char(string="Oracle Short Code", index=True)
