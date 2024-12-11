from odoo import models, fields
from ..serializers import ItemTxnSerializer, JournalSerializer
from ..utils import RequestSender
from logging import getLogger
import json

_logger = getLogger(__name__)

BASE_URL_PWC = "https://ebs-uat.nmohammadgroup.com:4460"
journal_api_url = f"{BASE_URL_PWC}/webservices/rest/pos_details/pos_journal_import/?"
serializer = JournalSerializer()

class ExtendedStockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(ExtendedStockPicking, self).button_validate()

        if self.state == 'assigned' and self.origin.startswith('Return'):

            sales_reference = self.group_id.name

            sale_obj = self.env['sale.order'].sudo().search([('name', '=', sales_reference)])

            total_sales_rev = 0

            move_idss = [m_id.product_id.id for m_id in self.move_ids]

            for line in sale_obj.order_line:
                if line.product_id.id in move_idss:
                    total_sales_rev += line.price_subtotal

            input_payload = {
                'oracle_pointer': 'RETURN_SALES_REV',
                'total_credit_amount': 0,
                'total_debit_amount': 0,
                'txn_date': self.scheduled_date,
                'company_name': 'Build Best',
                'journal_id': f'DELIVERY_RETURN_{self.id} WITH SALES RETURNED VALUE OF {total_sales_rev}',
                'order_reference': self.group_id.name,
                'invoice_reference': self.name
            }

            payload = serializer.serialize([input_payload])
            print(payload)
            RequestSender(journal_api_url, payload=payload).post()


        return res

