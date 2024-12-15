from odoo import fields, models, api

class SalesTransactionOP(models.Model):
    _name = 'sales.transaction.op'
    _description = 'sales transaction output payload'
    _rec_name = 'sequence'
    _order = 'id desc'

    sequence = fields.Char(string='Sequence')
    entity_name = fields.Char(string='Entity name')
    trx_date = fields.Datetime(string='Transaction date')
    cr_amount = fields.Float(string='Credit amount')
    dr_amount = fields.Float(string='Debit amount')
    transaction_type = fields.Char(string='Transaction type')
    description = fields.Text(string='Description')
    r_status = fields.Char(string='R_STATUS')
    r_msg = fields.Char(string='R_MSG')
    attribute_1 = fields.Char(string='Attribute_1')
    attribute_2 = fields.Char(string='Attribute_2')
    attribute_3 = fields.Char(string='Attribute_3')
    attribute_4 = fields.Char(string='Attribute_4')

    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('sales.transaction.op.seq')
        return super(SalesTransactionOP, self).create(vals)