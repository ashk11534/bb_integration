from odoo import fields, models, api

class SalesTransaction(models.Model):
    _name = 'sales.transaction'
    _description = 'sales.transaction.description'
    _rec_name = 'sequence'

    sequence = fields.Char(string='Sequence')
    entity_name = fields.Char(string='Entity name')
    trx_date = fields.Datetime(string='Transaction date', default=lambda self: fields.Datetime.now())
    cr_amount = fields.Float(string='Credit amount')
    dr_amount = fields.Float(string='Debit amount')
    transaction_type = fields.Char(string='Transaction type', required=True)
    description = fields.Text(string='Description')
    attribute_1 = fields.Char(string='Attribute_1')
    attribute_2 = fields.Char(string='Attribute_2')
    attribute_3 = fields.Char(string='Attribute_3')
    attribute_4 = fields.Char(string='Attribute_4')

    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('sales.transaction.seq')
        return super(SalesTransaction, self).create(vals)