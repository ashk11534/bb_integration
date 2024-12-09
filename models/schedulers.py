# -*- coding: utf-8 -*-
from datetime import datetime
from logging import getLogger

from odoo import models
import copy
import json

from ..serializers import ItemTxnSerializer, JournalSerializer
from ..utils import RequestSender

import pandas as pd


from rich import print  # noqa

_logger = getLogger(__name__)


BASE_URL_PWC = "https://ebs-uat.nmohammadgroup.com:4460"
# BASE_URL_PWC = "https://ebsprod.nmohammadgroup.com:4480"


def change_oracle_pointer(rows, pointer_code):
    copy_rows = copy.deepcopy(rows)

    for row in copy_rows:
        row["oracle_pointer"] = pointer_code

    return copy_rows


class InventoryTransaction(models.Model):
    _name = "inventory.transaction"
    _description = "Stock Movement Tracking Schedulers"

    serializer = ItemTxnSerializer()
    # item_txn_api_url = f"{BASE_URL_PWC}/webservices/rest/pos_details3/post_inventory_transaction/"
    item_txn_api_url = f"{BASE_URL_PWC}/webservices/rest/pos_details/post_inventory_transaction/?"

    def send_inventory_update_of_sold_items(self):
        stock_move_model = self.env["stock.move.line"]

        orders = stock_move_model.get_stock_moves_today()

        oracle_orders = self.serializer.serialize(orders)

        if orders:
            resp = RequestSender(self.item_txn_api_url, payload=oracle_orders).post()

            arrays = resp["OutputParameters"]["P_OUTPITMTRANTABTYP"]["P_OUTPITMTRANTABTYP_ITEM"]

            if resp:
                _logger.info("Inventory Update")
                _logger.info(json.dumps(resp, indent=4))

            # is_ok = True
            success_item = []
            for arr in arrays:
                if arr["R_STATUS"] != "S":
                    success_item.append(arr["ITEM_CODE"])
                else:
                    pass
                    # success_item.append(arr["ITEM_CODE"])
                
            if success_item:
                stock_move_model.update_item_oracle_status(success_item)

            # if is_ok:
            #     stock_move_model.update_today_stock_status()

        _logger.info(f"Executed PwC Cron(send_inventory_update_of_sold_items) at {self.serializer.timeit()}")

    def send_refund_update_to_pwc(self):
        stock_move_model = self.env["stock.move.line"]

        orders = stock_move_model.get_return_stock_moves_today()

        oracle_orders = self.serializer.serialize(orders)
        print(f"orcale orders : {oracle_orders}")

        if orders:
            resp = RequestSender(self.item_txn_api_url, payload=oracle_orders).post()

            arrays = resp["OutputParameters"]["P_OUTPITMTRANTABTYP"]["P_OUTPITMTRANTABTYP_ITEM"]

            is_ok = True

            for arr in arrays:
                if arr["R_STATUS"] != "S":
                    _logger.info("Fallback for Return sale stock move line update due to oracle failed.")
                    is_ok = False
                    break

            if is_ok:
                stock_move_model.update_today_stock_status_for_refund()

        _logger.info(f"Executed PwC Cron(send_inventory_update_of_sold_items) at {self.serializer.timeit()}")

    def _get_or_create_category(self, category_hierarchy):
        """
        Creates or fetches the category based on the provided hierarchy.
        """
        # Split the category hierarchy
        category_list = category_hierarchy.split(" / ")
        parent_category = False
        category_obj = self.env["product.category"].sudo()
        for category_name in category_list:
            # Search for the category at this level
            category = category_obj.search([("name", "=", category_name), ("parent_id", "=", parent_category)], limit=1)

            # If not found, create the category
            if not category:
                _logger.error("Category %s not found. Creating new with parent %s", category_name, parent_category)
                category = category_obj.create({"name": category_name, "parent_id": parent_category})

            # Set parent for the next iteration
            parent_category = category.id
        return parent_category

    def add_new_products(self):
        url = f"{BASE_URL_PWC}/webservices/rest/pos_details/GET_ITEMS/"

        response = RequestSender(url, None).get()

        try:
            data = response["OutputParameters"]["P_OUTITMTABTYP"]["P_OUTITMTABTYP_ITEM"]


            if not data:
                _logger.info("body is null !!!")
                return

            for item in data:
                name = item.get("ITEM_DESCRIPTION")
                item_code = item.get("ITEM_CODE")
                category = item.get("ATTRIBUTE2")
                price = item.get("PRICE", 0)

                # Check if item_code already exists
                existing_product = self.env["product.template"].sudo().search([('default_code', '=', item_code)], limit=1)

                if existing_product:
                    _logger.info("new_product: Item Code (%s) already exists, skipping creation.", item_code)
                    continue  # Skip to the next item if it exists

                # Split the category hierarchy
                if not all([name, item_code]):
                    _logger.error("new_product: Missing requried fields for Item create")
                    _logger.error(json.dumps(data, indent=4))
                    return

                if name == "" or item_code == "":
                    _logger.error("new_product: Failed to create item due to name error")
                    _logger.error(json.dumps(data, indent=4))
                    return

                if category != "" and category:
                    category_id = self._get_or_create_category(category) if category else False
                else:
                    category_id = self._get_or_create_category("Non Categorized")

                try:
                    _ = (
                        self.env["product.template"]
                        .sudo()
                        .create(
                            {
                                "name": name,
                                "list_price": price,
                                "detailed_type": "product",
                                "invoice_policy": "order",
                                "default_code": item_code,
                                "available_in_pos": False,
                                "categ_id": category_id,
                                "responsible_id": 1,
                            }
                        )
                    )
                except Exception as e:
                    _logger.error(e)
                    continue
                _logger.info("new_product: product created with Item(%s)", item_code)
        except TypeError:
            _logger.info("new_product: no payload found in body !!!")
            return
        except Exception as exc:
            _logger.exception(exc)
            _logger.error("new_product: Failed to Create Item with error %s", str(exc))
            return


class JournalEntryTransaction(models.Model):
    _name = "sync.journal"
    _description = "Payment Journal Entry Scheduler Incl. Advance & Refund"

    serializer = JournalSerializer()
    # journal_api_url = f"{BASE_URL_PWC}/webservices/rest/pos_details3/pos_journal_import/"
    journal_api_url = f"{BASE_URL_PWC}/webservices/rest/pos_details/pos_journal_import/?"

    def send_payment_journals(self):
        _logger.info("Sending Journal Entry for Oracle")
        model = self.env["account.move"]
        today = datetime.today().strftime("%Y-%m-%d")

        journals = model.get_payment_journals(today)

        for j in journals:
            print(j.get('journal_id'))

        sales_journals = []
        advance_journals = []
        refund_sales = []
        refund_cash = []
        sales_discount = []
        sales_return = []
        receivable_accounts = []
        return_discount = []
        receivable_accounts_refund_sales = []

        for journal in journals:
            if journal["oracle_pointer"].startswith("ADV"):
                journal["total_credit_amount"] = 0.0
                advance_journals.append(journal)
            elif journal["oracle_pointer"].startswith("REFUND_SALES"):
                journal["total_credit_amount"] = 0.0
                refund_sales.append(journal)
            elif journal["oracle_pointer"].startswith("REFUND_CASH"):
                journal["total_credit_amount"] = 0.0
                refund_cash.append(journal)

            elif journal["oracle_pointer"].startswith("SALES_DIS"):
                journal["total_credit_amount"] = 0.0
                sales_discount.append(journal)

            elif journal["oracle_pointer"].startswith("RETURN_SALES_REV"):
                journal["total_credit_amount"] = 0.0
                sales_return.append(journal)

            elif journal["oracle_pointer"].startswith("RETURN_SALES_REC"):
                journal["total_credit_amount"] = 0.0
                receivable_accounts.append(journal)

            elif journal["oracle_pointer"].startswith("RETURN_SALES_DIS"):
                journal["total_credit_amount"] = 0.0
                return_discount.append(journal)

            elif journal["oracle_pointer"].startswith("REFUND_SALES_REC"):
                journal["total_credit_amount"] = 0.0
                receivable_accounts_refund_sales.append(journal)

            else:
                journal["total_credit_amount"] = 0.0
                sales_journals.append(journal)

        if len(sales_discount):
            credit_lines = []
            for discount in sales_discount:
                line = discount.copy()
                debit_amount = line.get("total_debit_amount", 0)
                line["oracle_pointer"] = "SALES_DIS"
                line["total_credit_amount"] = debit_amount
                line["total_debit_amount"] = 0.0
                credit_lines.append(line)

            sales_discount.extend(credit_lines)
            payload = self.serializer.serialize(sales_discount)
            print(payload)
            RequestSender(self.journal_api_url, payload=payload).post()

        if len(sales_return):
            credit_lines = []
            for s_return in sales_return:
                line = s_return.copy()
                debit_amount = line.get("total_debit_amount", 0)
                line["oracle_pointer"] = "RETURN_SALES_REV"
                line["total_credit_amount"] = debit_amount
                line["total_debit_amount"] = 0.0
                credit_lines.append(line)

            sales_return.extend(credit_lines)
            payload = self.serializer.serialize(sales_return)

            RequestSender(self.journal_api_url, payload=payload).post()

        if len(receivable_accounts):
            credit_lines = []
            for r_account in receivable_accounts:
                line = r_account.copy()
                debit_amount = line.get("total_debit_amount", 0)
                line["oracle_pointer"] = "RETURN_SALES_REC"
                line["total_credit_amount"] = debit_amount
                line["total_debit_amount"] = 0.0
                credit_lines.append(line)

            receivable_accounts.extend(credit_lines)
            payload = self.serializer.serialize(receivable_accounts)

            RequestSender(self.journal_api_url, payload=payload).post()

        if len(return_discount):
            credit_lines = []
            for r_discount in return_discount:
                line = r_discount.copy()
                debit_amount = line.get("total_debit_amount", 0)
                line["oracle_pointer"] = "RETURN_SALES_DIS"
                line["total_credit_amount"] = debit_amount
                line["total_debit_amount"] = 0.0
                credit_lines.append(line)

            return_discount.extend(credit_lines)
            payload = self.serializer.serialize(return_discount)

            print('Sales discount', payload)

            RequestSender(self.journal_api_url, payload=payload).post()

        if len(receivable_accounts_refund_sales):
            credit_lines = []
            for r_account_ref_sales in receivable_accounts_refund_sales:
                line = r_account_ref_sales.copy()
                debit_amount = line.get("total_debit_amount", 0)
                line["oracle_pointer"] = "REFUND_SALES_REC"
                line["total_credit_amount"] = debit_amount
                line["total_debit_amount"] = 0.0
                credit_lines.append(line)

            receivable_accounts_refund_sales.extend(credit_lines)
            payload = self.serializer.serialize(receivable_accounts_refund_sales)

            RequestSender(self.journal_api_url, payload=payload).post()

        # unapplied receipts/ Collections
        if len(sales_journals):
            credit_lines = []
            for sale in sales_journals:
                line = sale.copy()
                debit_amt = line.get("total_debit_amount", 0)
                line["oracle_pointer"] = "BILL_UNAPP_RCPT"
                line["total_credit_amount"] = debit_amt
                line["total_debit_amount"] = 0.0
                credit_lines.append(line)

            sales_journals.extend(credit_lines)

            payload = self.serializer.serialize(sales_journals)

            RequestSender(self.journal_api_url, payload=payload).post()

        # advance collections
        if len(advance_journals):
            credit_lines = []
            for journal in advance_journals:
                line = journal.copy()
                debit_amt = line.get("total_debit_amount", 0)
                line["oracle_pointer"] = "ADV_ONACCOUNT_COL"
                line["total_credit_amount"] = debit_amt
                line["total_debit_amount"] = 0.0
                credit_lines.append(line)

            advance_journals.extend(credit_lines)

            payload = self.serializer.serialize(advance_journals)

            RequestSender(self.journal_api_url, payload=payload).post()

        # Refund Works
        if len(refund_sales):
            credit_lines = []
            for journal in refund_sales:
                line = journal.copy()
                debit_amt = line.get("total_debit_amount", 0)
                line["oracle_pointer"] = "REFUND_CASH_ACT"
                line["total_credit_amount"] = debit_amt
                line["total_debit_amount"] = 0.0
                credit_lines.append(line)
            refund_sales.extend(credit_lines)
            payload = self.serializer.serialize(refund_sales)
            RequestSender(self.journal_api_url, payload=payload).post()

        # Refund Works
        if len(refund_cash):
            credit_lines = []
            for journal in refund_cash:
                line = journal.copy()
                debit_amt = line.get("total_debit_amount", 0)
                line["oracle_pointer"] = "REFUND_ON_ACCT_RCPT"
                line["total_credit_amount"] = debit_amt
                line["total_debit_amount"] = 0.0
                credit_lines.append(line)
            refund_cash.extend(credit_lines)
            payload = self.serializer.serialize(refund_cash)
            RequestSender(self.journal_api_url, payload=payload).post()


        _logger.info(f"Executed PwC Cron(send_payment_journals) at {self.serializer.timeit()}")

    def send_sales_revenue(self):
        """
        Oracle Push Service
            - Sales Revenue -> SALES_REV
            - Account Receivable -> SALES_REC
            - Discount -> SALES_DIS
        """
        model = self.env["account.move"]
        discount_pointer = "SALES_DIS"

        sales_rev = model.sales_revenue()

        df = pd.DataFrame(sales_rev)

        if "account_code" in df.columns and "total_debit_amount" in df.columns:
            # Apply filtering only when columns are present
            product_sale_rows = df[(df["account_code"] == "400000") & (df["total_debit_amount"] > 0)]
        else:
            product_sale_rows = pd.DataFrame()

        discount_records = product_sale_rows.to_dict(orient="records")

        if discount_records:
            _changed_discount_records = change_oracle_pointer(discount_records, discount_pointer)
            for rec in _changed_discount_records:
                rec["total_credit_amount"] = 0.0
            sales_rev.extend(_changed_discount_records)

        for sale in sales_rev:
            if sale["oracle_pointer"] == "SALES_REV":
                sale["total_debit_amount"] = 0.0
            else:
                sale["total_credit_amount"] = 0.0

        payload = self.serializer.serialize(sales_rev)

        if sales_rev:
            print(json.dumps(payload, indent=4))
            RequestSender(self.journal_api_url, payload=payload).post()

    def send_misc_advance_settlement(self):
        model = self.env["account.move"]

        advance_settlements = model.get_daily_advance_settlements()

        if advance_settlements:
            credit_lines = []
            for settlement in advance_settlements:
                settlement["total_credit_amount"] = 0.0

                line = settlement.copy()
                debit_amt = line.get("total_debit_amount", 0)
                line["oracle_pointer"] = "SETTLE_REC_ACT_RCPT"
                line["total_credit_amount"] = debit_amt
                line["total_debit_amount"] = 0.0
                credit_lines.append(line)

            advance_settlements.extend(credit_lines)
            serialized_settlements = self.serializer.serialize(advance_settlements)
            RequestSender(self.journal_api_url, serialized_settlements).post()

    def send_advance_settlement_bill(self):
        model = self.env["account.move"]

        advance_settlements = model.get_daily_settlement_against_bill()

        if advance_settlements:
            data = self.serializer.serialize(advance_settlements)
            RequestSender(self.journal_api_url, data).post()

            for rec in advance_settlements:
                rec["total_credit_amount"] = 0.0
                rec["oracle_pointer"] = "SETTLE_REC_ACT_BILL"

            rcv_accounts = self.serializer.serialize(advance_settlements)
            RequestSender(self.journal_api_url, rcv_accounts).post()

    def send_advance_refund_settlement(self):
        model = self.env["account.move"]

        advance_settlements = model.get_advance_refund_settlement()

        if advance_settlements:
            credit_lines = []
            for settlement in advance_settlements:
                line = settlement.copy()
                credit_amt = line.get("total_credit_amount", 0)
                settlement["total_debit_amount"] = 0.0
                line["oracle_pointer"] = "REFUND_ON_ACCT_RCPT"
                line["total_credit_amount"] = 0.0
                line["total_debit_amount"] = credit_amt
                credit_lines.append(line)

            advance_settlements.extend(credit_lines)

            rcv_accounts = self.serializer.serialize(advance_settlements)
            RequestSender(self.journal_api_url, rcv_accounts).post()

    def update_ledger_status(self):
        model = self.env["account.move"]

        _ = model.update_ledgers_sent()
