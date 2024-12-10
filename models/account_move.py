from odoo import models, fields
from ..serializers import ItemTxnSerializer, JournalSerializer
from ..utils import RequestSender
from odoo.http import request as req

BASE_URL_PWC = "https://ebs-uat.nmohammadgroup.com:4460"
journal_api_url = f"{BASE_URL_PWC}/webservices/rest/pos_details/pos_journal_import/?"
serializer = JournalSerializer()

class ExtendedAccountMove(models.Model):
    _inherit = "account.move"

    sent_to_oracle = fields.Boolean(string="Sent To Oracle", default=False)

    def get_cash_unsent_moves(self):
        _domain = [
            ("state", "in", ["posted"]),
            ("journal_id.type", "=", "cash"),
            ("sent_to_oracle", "<>", "NULL"),
            ("sent_to_oracle", "<>", "TRUE"),
        ]

        moves = self.search(_domain)

        return moves.ids

    def get_bank_moves(self, bank_code):
        _domain = [
            ("state", "in", ["posted"]),
            ("journal_id.type", "=", "bank"),
            ("journal_id.oracle_pointer", "=", bank_code),
            ("sent_to_oracle", "<>", "NULL"),
            ("sent_to_oracle", "<>", "TRUE"),
        ]

        moves = self.search(_domain)

        return moves.ids

    def get_moves_for_oracle(self, ids):
        query = """
            SELECT 
                am.id,
                c.org_name AS entity_name,
                am.name,
                am.ref,
                aj.name,
                aj.oracle_pointer as transaction_type,
                am.payment_state,
                am.create_date AS trx_date,
                am.amount_total ,
                am.move_type
            FROM 
                account_move am
            JOIN 
                res_company c ON am.company_id = c.id
            join
                account_journal aj ON am.journal_id = aj.id
            WHERE 
                am.id in %s
            """

        self.env.cr.execute(query, (ids,))

        mapped_moves = self.env.cr.dictfetchall()
        # Fetch and add debit and credit amounts for each move
        for move in mapped_moves:
            move_id = move["id"]
            line_query = """
                SELECT
                    sum(aml.debit) as debit,
                    sum(aml.credit) as credit
                FROM 
                    account_move_line aml
                WHERE 
                    aml.move_id = %s
            """
            self.env.cr.execute(line_query, (move_id,))

            move_lines = self.env.cr.dictfetchall()
            if move_lines:
                line = move_lines[0]
                # Add debit and credit totals to the move dictionary
                move["debit"] = line.get("debit")
                move["credit"] = line.get("credit")

        return mapped_moves

    def get_payment_journals(self, date):
        """Fetch the Payment Journals for Cash, Bank including Advance Collections"""
        query = """
                select
                    am.id as journal_id,
                    rc.org_name as company_name,
                    am.name as order_reference,
                    am.date as txn_date,
                    aj.name as journal_name,
                    aj.type as journal_type,
                    aj.oracle_pointer,
                    aa.code as journal_item_code,
                    SUM(aml.quantity) AS transaction_qty,
                    SUM(aml.debit) AS total_debit_amount,
                    SUM(aml.credit) AS total_credit_amount
                from
                    account_move am
                join account_journal aj on
                    aj.id = am.journal_id
                join res_company rc on 
                    rc.id = am.company_id
                join 
                    account_move_line aml ON aml.move_id = am.id
                join account_account aa ON
                    aa.id = aml.account_id 
                where
                    aj.type in ('cash', 'bank')
                    and am.state in ('posted')
                    and am.date <= %s
                    and am.sent_to_oracle = FALSE
                group by
                    am.id,
                    rc.org_name,
                    am.name,
                    am.date,
                    aj.name,
                    aj.type,
                    aj.oracle_pointer,
                    aa.code
                """
        self.env.cr.execute(query, (date,))
        return self.env.cr.dictfetchall()

    def mark_moves_sent_to_oracle(self, ids):
        moves = self.browse(ids)
        moves.write({"sent_to_oracle": True})
        self.env.cr.commit()  # commit the txn

    def get_refund_moves(self, date):
        query = """
                select
                    -- am.id,
                    rc.org_name as company_name,
                    -- am.name as order_reference,
                    aj.name as journal_name,
                    aj.type as journal_type,
                    aj.oracle_pointer,
                    am.date as txn_date,
                    sum(aml.credit) as total_credit_amount,
                    sum(aml.debit) as total_debit_amount
                from
                    account_journal aj
                join 
                    account_move am on
                    aj.id = am.journal_id
                join
                    res_company rc on
                    rc.id = am.company_id
                join 
                    account_move_line aml on
                    am.id = aml.move_id
                where
                    aj.name = 'Refund Sales Revenue'
                    and am.state in ('posted')
                    and am.date = %s
                    and am.sent_to_oracle = FALSE
                group by 
                    rc.org_name,
                    aj.name,
                    am.date,
                    aj.oracle_pointer,
                    aj.type
            """
        self.env.cr.execute(query, (date,))
        return self.env.cr.dictfetchall()

    def sales_revenue(self):
        query = """
                select
                --		am.id,
                    aa.code as account_code,
                    aa.name as account_name,
                    am.date as txn_date,
                    sum(aml.debit) as total_debit_amount,
                    sum(aml.credit) as total_credit_amount,
                    rc.org_name as company_name,
                    case
                        when aa.code in ('121000', '101501', '101404') then 'SALES_REC'
                        when aa.code = '400000' then 'SALES_REV'
                    end as oracle_pointer
                from
                    account_move_line aml
                join account_account aa on
                    aa.id = aml.account_id
                join account_move am on
                    am.id = aml.move_id
                join res_company rc on
                    rc.id = aml.company_id
                join account_journal aj on
                    aj.id = am.journal_id
                where
                    aa.code in ('121000', '400000', '101404', '101501')
                    and aj.type in ('general', 'sale')
                    and aj.oracle_pointer not in ('DNT')
                    and am.state = 'posted'
                    and am.move_type in ('out_invoice', 'entry')
                	and aml.create_date::date = current_date
                    and am.sent_to_oracle = false
                group by
                --		am.id,
                    aa.code,
                    rc.org_name,
                    aa.name,
                    am.date
                order by
                    am.date
        """

        self.env.cr.execute(query)

        return self.env.cr.dictfetchall()

    def get_daily_advance_settlements(self):
        query = """
                select
                    rc.org_name as company_name,
                    aa.code,
                    am.date as txn_date,
                    sum(aml.debit) as total_debit_amount,
                    sum(aml.credit) as total_credit_amount,
                    sum(aml.balance) as total_balance,
                    'SETTLE_ON_ACCT_ADV_RCPT' as oracle_pointer
                from
                    account_move_line aml
                join
                    account_move am on
                    am.id = aml.move_id
                join
                    account_account aa on
                    aa.id = aml.account_id
                join res_company rc on
                    rc.id = am.company_id
                where
                    aa.code = '101003'
                    and am.date::date = current_date
                    and am.sent_to_oracle = FALSE
                group by 
                    rc.org_name,
                    aa.code,
                    am.date
        """

        self.env.cr.execute(query)

        return self.env.cr.dictfetchall()

    def get_daily_settlement_against_bill(self):
        query = """
                select
                    rc.org_name as company_name,
                    aa.code,
                    am.date as txn_date,
                    sum(aml.debit) as total_debit_amount,
                    sum(aml.credit) as total_credit_amount,
                    sum(aml.balance) as total_balance,
                    'SETTLE_UNAPP_RCPT_BILL' as oracle_pointer
                from
                    account_move_line aml
                join
                    account_move am on
                    am.id = aml.move_id
                join
                    account_account aa on
                    aa.id = aml.account_id
                join res_company rc on
                    rc.id = am.company_id
                where
                    aa.code = '101004'
                    and am.date::date = current_date
                    and am.sent_to_oracle = FALSE
                group by 
                    rc.org_name,
                    aa.code,
                    am.date
        """

        self.env.cr.execute(query)

        return self.env.cr.dictfetchall()

    def get_advance_refund_settlement(self):
        query = """
                select
                    rc.org_name as company_name,
                    -- aa.code,
                    am.date as txn_date,
                    sum(aml.debit) as total_debit_amount,
                    sum(aml.credit) as total_credit_amount,
                    sum(aml.balance) as total_balance,
                    'REFUND_CASH_ACCT_RCPT' as oracle_pointer
                from
                    account_move_line aml
                join
                    account_move am on
                    am.id = aml.move_id
                join res_company rc on
                    rc.id = am.company_id
                join
                    account_journal aj on
                    aj.id = am.journal_id
                where
                    aj.oracle_pointer = 'REFUND_CASH_ACCT_RCPT'
                    and am.date::date = current_date
                    and am.sent_to_oracle = FALSE
                group by 
                    rc.org_name,
                    am.date
        """

        self.env.cr.execute(query)

        return self.env.cr.dictfetchall()

    def update_ledgers_sent(self):
        query = """
                update
                    account_move
                set
                    sent_to_oracle = true
                where date::date <= current_date
                and sent_to_oracle is not true
        """
        self.env.cr.execute(query)

    def action_post(self):
        res = super(ExtendedAccountMove, self).action_post()

        for move in self:

            print(move.ref.startswith('Reversal'))

            if move.state == 'posted' and not self.sent_to_oracle:
                journal_item_sales_dis = move.line_ids[0]

                input_payload = {
                    'oracle_pointer': 'SALES_DIS',
                    'total_credit_amount': journal_item_sales_dis.credit,
                    'total_debit_amount': journal_item_sales_dis.debit,
                    'txn_date': self.invoice_date,
                    'company_name': 'BMU',
                    'journal_id': f'JOURNAL-{move.journal_id.id}',
                    'order_reference': move.invoice_origin,
                    'invoice_reference': self.name
                }

                payload = serializer.serialize([input_payload])
                print(payload)
                if not self.sent_to_oracle and self.discount_rate > 0:
                    RequestSender(journal_api_url, payload=payload).post()

                journal_item_receivable_accounts = move.line_ids[-1]

                input_payload = {
                    'oracle_pointer': 'RETURN_SALES_REC',
                    'total_credit_amount': journal_item_receivable_accounts.credit,
                    'total_debit_amount': journal_item_receivable_accounts.debit,
                    'txn_date': self.invoice_date,
                    'company_name': 'BMU',
                    'journal_id': f'JOURNAL-{move.journal_id.id}',
                    'order_reference': move.invoice_origin,
                    'invoice_reference': self.name
                }

                payload = serializer.serialize([input_payload])
                print(payload)
                if not self.sent_to_oracle and self.discount_rate > 0:
                    res = RequestSender(journal_api_url, payload=payload).post()
                    if res != False:
                        self.sent_to_oracle = True

            if move.ref.startswith('Reversal'):

                print('Hmm')

                self.sent_to_oracle = False

                journal_item_sales_dis = move.line_ids[0]

                input_payload = {
                    'oracle_pointer': 'RETURN_SALES_DIS',
                    'total_credit_amount': journal_item_sales_dis.credit,
                    'total_debit_amount': journal_item_sales_dis.debit,
                    'txn_date': self.invoice_date,
                    'company_name': 'BMU',
                    'journal_id': f'JOURNAL-{move.journal_id.id}',
                    'order_reference': move.invoice_origin,
                    'invoice_reference': self.name
                }

                payload = serializer.serialize([input_payload])
                print(payload)
                if not self.sent_to_oracle and self.discount_rate > 0:
                    RequestSender(journal_api_url, payload=payload).post()

                journal_item_receivable_accounts = move.line_ids[-1]

                input_payload = {
                    'oracle_pointer': 'REFUND_SALES_REC',
                    'total_credit_amount': journal_item_receivable_accounts.credit,
                    'total_debit_amount': journal_item_receivable_accounts.debit,
                    'txn_date': self.invoice_date,
                    'company_name': 'BMU',
                    'journal_id': f'JOURNAL-{move.journal_id.id}',
                    'order_reference': move.invoice_origin,
                    'invoice_reference': move.ref
                }

                payload = serializer.serialize([input_payload])
                print(payload)
                if not self.sent_to_oracle and self.discount_rate > 0:
                    res = RequestSender(journal_api_url, payload=payload).post()
                    if res != False:
                        self.sent_to_oracle = True

            break

        return res
