from odoo import models, fields


class Influencer(models.Model):
    _name = "bb.influencer"
    _description = "Influencer lists for customers"

    name = fields.Char(string="Influencer Name")