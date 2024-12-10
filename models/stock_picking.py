from odoo import models, fields
from ..serializers import ItemTxnSerializer
from ..utils import RequestSender
from logging import getLogger
import json

_logger = getLogger(__name__)

serializer = ItemTxnSerializer()
BASE_URL_PWC = "https://ebs-uat.nmohammadgroup.com:4460"
item_txn_api_url = f"{BASE_URL_PWC}/webservices/rest/pos_details/post_inventory_transaction/?"

class ExtendedStockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(ExtendedStockPicking, self).button_validate()

        if self.state == 'assigned' and self.origin.startswith('Return'):

            stock_move_model = self.env["stock.move.line"]

            orders = []

            for move in self.move_ids:

                orders.append({
                    'org_unit': 'BMU',
                    'src_loc': 'BMU-MUR-01',
                    'item_code': move.product_id.name,
                    'sold_in_puom': move.product_uom_qty,
                    'oracle_pointer': 'RETURN_SALES_REV',
                    'txn_date': self.scheduled_date,
                    'move_id': f'stock_move-{self.id}'
                })

            oracle_orders = serializer.serialize(orders)

            if orders:
                resp = RequestSender(item_txn_api_url, payload=oracle_orders).post()

                print(resp)

                arrays = resp["OutputParameters"]["P_OUTPITMTRANTABTYP"]["P_OUTPITMTRANTABTYP_ITEM"]

                if resp:
                    _logger.info("Inventory Update")
                    _logger.info(json.dumps(resp, indent=4))

                success_item = []
                for arr in arrays:
                    if arr["R_STATUS"] != "S":
                        success_item.append(arr["ITEM_CODE"])
                    else:
                        pass

                if success_item:
                    stock_move_model.update_item_oracle_status(success_item)

            _logger.info(f"Executed PwC Cron(send_inventory_update_of_sold_items) at {serializer.timeit()}")

        return res

