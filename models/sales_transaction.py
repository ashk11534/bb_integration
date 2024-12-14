from odoo import fields, models, api
from ..serializers import JournalSerializer
from ..utils import RequestSender

BASE_URL_PWC = "https://ebs-uat.nmohammadgroup.com:4460"
# BASE_URL_PWC = "https://ebsprod.nmohammadgroup.com:4480"

class SalesTransaction(models.Model):
    _name = 'sales.transaction'
    _description = 'sales.transaction.description'
    _rec_name = 'sequence'
    _order = 'id desc'

    serializer = JournalSerializer()
    journal_api_url = f"{BASE_URL_PWC}/webservices/rest/pos_details/pos_journal_import/?"

    sequence = fields.Char(string='Sequence')
    entity_name = fields.Char(string='Entity name')
    trx_date = fields.Datetime(string='Transaction date', default=lambda self: fields.Datetime.now())
    cr_amount = fields.Float(string='Credit amount')
    dr_amount = fields.Float(string='Debit amount')
    transaction_type = fields.Char(string='Transaction type', required=True)
    discount_rate = fields.Float(string='Discount rate')
    journal_id = fields.Integer(string='Journal ID')
    invoice_origin = fields.Char(string='Invoice origin')
    description = fields.Text(string='Description')
    attribute_1 = fields.Char(string='Attribute_1')
    attribute_2 = fields.Char(string='Attribute_2')
    attribute_3 = fields.Char(string='Attribute_3')
    attribute_4 = fields.Char(string='Attribute_4')
    sent_to_oracle = fields.Boolean(string='Sent to oracle', default=False)

    def send_transaction_to_oracle(self):
        print('Sending to Oracle.')
        if self.transaction_type == 'RETURN_SALES_REV':
            input_payload = {
                'oracle_pointer': self.transaction_type,
                'total_credit_amount': self.cr_amount,
                'total_debit_amount': self.dr_amount,
                'txn_date': self.trx_date,
                'company_name': self.entity_name,
                'journal_id': self.journal_id,
                'order_reference': self.invoice_origin,
                'invoice_reference': self.attribute_1
            }

            if not self.sent_to_oracle:
                payload = self.serializer.serialize([input_payload])
                print(payload)
                RequestSender(self.journal_api_url, payload=payload).post()
                self.sent_to_oracle = True

                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': 'The transaction has been sent successfully!',
                        'img_url': '/web/static/img/smile.svg',
                        'type': 'rainbow_man',
                    }
                }

        if self.transaction_type == 'RETURN_SALES_DIS':
            input_payload = {
                'oracle_pointer': self.transaction_type,
                'total_credit_amount': self.cr_amount,
                'total_debit_amount': self.dr_amount,
                'txn_date': self.trx_date,
                'company_name': self.entity_name,
                'journal_id': self.journal_id,
                'order_reference': self.invoice_origin,
                'invoice_reference': self.attribute_1
            }

            if not self.sent_to_oracle and self.attribute_1.startswith('Compa'):
                payload = self.serializer.serialize([input_payload])
                print(payload)
                RequestSender(self.journal_api_url, payload=payload).post()
                self.sent_to_oracle = True

                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': 'The transaction has been sent successfully!',
                        'img_url': '/web/static/img/smile.svg',
                        'type': 'rainbow_man',
                    }
                }

        if self.transaction_type == 'REFUND_SALES_REC':
            input_payload = {
                'oracle_pointer': self.transaction_type,
                'total_credit_amount': self.cr_amount,
                'total_debit_amount': self.dr_amount,
                'txn_date': self.trx_date,
                'company_name': self.entity_name,
                'journal_id': self.journal_id,
                'order_reference': self.invoice_origin,
                'invoice_reference': self.attribute_1
            }

            if not self.sent_to_oracle and self.discount_rate > 0:
                payload = self.serializer.serialize([input_payload])
                print(payload)
                res = RequestSender(self.journal_api_url, payload=payload).post()
                if res != False:
                    self.sent_to_oracle = True

                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'The transaction has been sent successfully!',
                            'img_url': '/web/static/img/smile.svg',
                            'type': 'rainbow_man',
                        }
                    }

        if self.transaction_type == 'RETURN_SALES_DIS' and self.discount_rate > 0:
            input_payload = {
                'oracle_pointer': self.transaction_type,
                'total_credit_amount': self.cr_amount,
                'total_debit_amount': self.dr_amount,
                'txn_date': self.trx_date,
                'company_name': self.entity_name,
                'journal_id': self.journal_id,
                'order_reference': self.invoice_origin,
                'invoice_reference': self.attribute_1
            }

            if not self.sent_to_oracle and (self.discount_rate > 0 or self.attribute_1.startswith('Compa')):
                payload = self.serializer.serialize([input_payload])
                print(payload)
                res = RequestSender(self.journal_api_url, payload=payload).post()
                if res != False:
                    self.sent_to_oracle = True

                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'The transaction has been sent successfully!',
                            'img_url': '/web/static/img/smile.svg',
                            'type': 'rainbow_man',
                        }
                    }

        if self.transaction_type == 'SALES_DIS':
            input_payload = {
                'oracle_pointer': self.transaction_type,
                'total_credit_amount': self.cr_amount,
                'total_debit_amount': self.dr_amount,
                'txn_date': self.trx_date,
                'company_name': self.entity_name,
                'journal_id': self.journal_id,
                'order_reference': self.invoice_origin,
                'invoice_reference': self.attribute_1
            }

            if not self.sent_to_oracle and self.discount_rate > 0:
                payload = self.serializer.serialize([input_payload])
                print(payload)
                res = RequestSender(self.journal_api_url, payload=payload).post()
                if res != False:
                    self.sent_to_oracle = True

                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'The transaction has been sent successfully!',
                            'img_url': '/web/static/img/smile.svg',
                            'type': 'rainbow_man',
                        }
                    }

        if self.transaction_type == 'RETURN_SALES_REC':
            input_payload = {
                'oracle_pointer': self.transaction_type,
                'total_credit_amount': self.cr_amount,
                'total_debit_amount': self.dr_amount,
                'txn_date': self.trx_date,
                'company_name': self.entity_name,
                'journal_id': self.journal_id,
                'order_reference': self.invoice_origin,
                'invoice_reference': self.attribute_1
            }

            if not self.sent_to_oracle and self.discount_rate > 0:
                payload = self.serializer.serialize([input_payload])
                print(payload)
                res = RequestSender(self.journal_api_url, payload=payload).post()
                if res != False:
                    self.sent_to_oracle = True

                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'The transaction has been sent successfully!',
                            'img_url': '/web/static/img/smile.svg',
                            'type': 'rainbow_man',
                        }
                    }


    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('sales.transaction.seq')
        return super(SalesTransaction, self).create(vals)