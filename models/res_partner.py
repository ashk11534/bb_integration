from odoo import models, fields


class ExtendedResPartner(models.Model):
    _inherit = "res.partner"

    influencer_id = fields.Many2one('bb.influencer', string="Influencer")