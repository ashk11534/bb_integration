from odoo import fields, models, api

class SaleOrderInherit(models.Model):
    _inherit='sale.order'

    def action_confirm(self):
        print('Sale is getting confirmed')
        res = super(SaleOrderInherit, self).action_confirm()

        self.env['sales.transaction'].sudo().create({
            'entity_name': 'Build Best',
            'trx_date': self.date_order,
            'cr_amount': 0,
            'dr_amount': 0,
            'transaction_type': 'SALES_REV',
            'discount_rate': self.discount_rate,
            'journal_id': None,
            'description': f'SALES_REVENUE_{self.id} WITH REVENUE VALUE OF {self.amount_untaxed} AND DISCOUNT VALUE OF {self.amount_discount}',
            'invoice_origin': self.name,
            'attribute_1': self.name
        })

        return res