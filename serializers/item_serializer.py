from logging import getLogger
from . import Serializer

_logger = getLogger(__name__)


class ItemTxnSerializer(Serializer):
    def _validate(self, values):
        """Validate the Payload as per Business Rule of Oracle"""
        # check if transaction type is defined
        for v in values:
            item_code = v.get("item_code", None)
            if not bool(item_code):
                _logger.error("Item Code not defined for below Order")
                _logger.error(v)
                return False
        return True

    def serialize(self, values):
        """serialize the response to oracle format"""
        if not self._validate(values):
            return
        response = {"P_INPITMTRANTABTYP": {}}

        for i, v in enumerate(values):
            if v.get("item_code") not in (None, ""):
                response["P_INPITMTRANTABTYP"][f"P_INPITMTRANTABTYP_ITEM{i+1}"] = {
                    "INVENTORY_ORGANIZATION": v.get("org_unit"),
                    "SUBINVENTORY": v.get("src_loc"),
                    "ITEM_CODE": v.get("item_code"),
                    "TRANSACTION_QUATITY": str(v.get("sold_in_puom")),
                    "TRANSACTION_TYPE": v.get("oracle_pointer"),
                    "ATTRIBUTE1": self.format_date(v.get("txn_date")),
                    "ATTRIBUTE2": v.get("move_id"),
                    "ATTRIBUTE3": "",
                    "ATTRIBUTE4": "",
                }
        return {
            "TESTUSERNAME_Input": {
                "RESTHeader": self.APIHeader,
                "InputParameters": response,
            },
        }
