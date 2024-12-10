from logging import getLogger
from . import Serializer

_logger = getLogger(__name__)


class JournalSerializer(Serializer):
    def _validate(self, values):
        """Validate the Payload as per Business Rule of Oracle"""

        # check if transaction type is defined
        for v in values:
            txn_type = v.get("oracle_pointer", None)
            if not bool(txn_type):
                _logger.error("Transaction Type not defined for below Journal")
                _logger.error(v)
                return False
        return True

    def serialize(self, values):
        """serialize the response to oracle format"""
        if not self._validate(values):
            return

        response = {"P_INPJLTABTYP": {}}

        for i, v in enumerate(values):

            print(v)

            response["P_INPJLTABTYP"][f"P_INPJLTABTYP_ITEM{i+1}"] = {
                "ENTITY_NAME": v.get("company_name"),
                "TRX_DATE": self.format_date(v.get("txn_date")),
                "CR_AMOUNT": str(v.get("total_credit_amount", 0)),
                "DR_AMOUNT": str(v.get("total_debit_amount", 0)),
                "TRANSACTION_TYPE": v.get("oracle_pointer"),
                "DESCRIPTION": f"RefNo: {v.get('order_reference', 'NA')}",
                "ATTRIBUTE1": v.get('journal_id', 'NA'),
                "ATTRIBUTE2": v.get('invoice_reference', 'NA'),
                "ATTRIBUTE3": "",
                "ATTRIBUTE4": "",
            }
        return {
            "TESTUSERNAME_Input": {
                "RESTHeader": self.APIHeader,
                "InputParameters": response,
            },
        }
