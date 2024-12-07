import json
from logging import getLogger
from odoo import http
from ..utils import authKeyRequired, logTracer

_logger = getLogger(__name__)

V1_API = "/api/v1"

ROUTE_PREFIX = V1_API + "/services/orcl"

KEY_IDENTIFIER = "API_KEY"


class SyncInventoryController(http.Controller):
    def _update_product_quantity(self, product, location, qty):
        quant = (
            http.request.env["stock.quant"]
            .sudo()
            .search([("product_id", "=", product.id), ("location_id", "=", location.id)], limit=1)
        )

        if quant:
            quant.quantity = qty
        else:
            http.request.env["stock.quant"].sudo().create(
                {"product_id": product.id, "location_id": location.id, "quantity": qty}
            )

    def _convert_qty_to_sell_uom(self, product, qty):
        factor = product.product_tmpl_id.uom_id.factor
        quant = factor * float(qty)
        return quant

    @http.route(f"{ROUTE_PREFIX}/sync-inventory", auth="public", methods=["POST"], type="json", website=False)
    @logTracer
    @authKeyRequired
    def index(self, **kw):
        kw.pop("API_KEY")
        product = kw["InputParameters"]["P_INPITMTRANTABTYP"]["P_INPITMTRANTABTYP_ITEM"]
        item_code = product.get("ITEM_CODE")
        qty = product.get("TRANSACTION_QUATITY")
        store = product.get("SUBINVENTORY")

        if not all([item_code, qty, store]):
            return {"status": "error", "message": "Missing requried fields !"}
        product = http.request.env["product.product"].sudo().search([("default_code", "=", item_code)], limit=1)

        if not product:
            return {"status": "error", "message": "Product not found !"}

        location = http.request.env["stock.location"].sudo().search([("name", "=", store)], limit=1)

        if not location:
            return {"status": "error", "message": "Location not found!"}

        qty = self._convert_qty_to_sell_uom(product, qty)

        self._update_product_quantity(product, location, float(qty))

        return {"status": "success", "message": "product quantity has been updated."}

    def _get_or_create_category(self, category_hierarchy):
        """
        Creates or fetches the category based on the provided hierarchy.
        """
        # Split the category hierarchy
        category_list = category_hierarchy.split(" / ")
        parent_category = False
        category_obj = http.request.env["product.category"].sudo()
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


    @http.route(f"{ROUTE_PREFIX}/add-item", auth="public", methods=["POST"], type="json", website=False)
    @logTracer
    def create_product(self, **kw):
        try:
            data = kw["OutputParameters"]["P_OUTITMTABTYP"]["P_OUTITMTABTYP_ITEM"]

            for item in data:
                name = item.get("ITEM_DESCRIPTION")
                item_code = item.get("ITEM_CODE")
                category = item.get("ATTRIBUTE2")
                price = item.get("PRICE", 0)

                if category:
                    category_id = self._get_or_create_category(category) if category else False
                else:
                    category_id = self._get_or_create_category("Non Categorized")

                # Split the category hierarchy
                if not all([name, item_code]):
                    _logger.error("Missing requried fields for Item create")
                    _logger.error(json.dumps(data, indent=4))
                    return

                if name == "" or item_code == "":
                    _logger.error("Failed to create item due to name error")
                    _logger.error(json.dumps(data, indent=4))
                    return

                if category != "" and category:
                    category_id = self._get_or_create_category(category) if category else False
                else:
                    category_id = self._get_or_create_category("Non Categorized")

                try:
                    _ = (
                        http.request.env["product.template"]
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
                    pass
                _logger.info("product created with Item(%s)", item_code)
        except Exception as exc:
            _logger.error("Failed to Create Item with error %s", str(exc))
            return