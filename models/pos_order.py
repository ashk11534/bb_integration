from logging import getLogger
from odoo import models, fields, api
import requests as r


_logger = getLogger(__name__)

class ExtendedPosOrder(models.Model):
    _inherit = "pos.order"

    sent_to_oracle = fields.Boolean(string="Sent to Oracle", default=False)

    @api.model
    def get_unsent_order_ids(self):
        # Fetch order Ids where sent_to_oracle is not True and Null
        _domain = [
            ("state", "in", ["paid", "done", "posted"]),
            ("sent_to_oracle", "<>", "true"),
        ]
        orders = self.search(_domain, limit=50)

        order_ids = orders.ids

        return order_ids

    @api.model
    def get_orders_for_oracle(self, order_ids):
        agg_qty_query = """
                        select
                        distinct 
                                    case
                            when pprod.product_tmpl_id = pt.id then pprod.default_code
                            else pt.default_code
                        end as ITEM_CODE,
                        --                sm.name,
                        --                sum(pol.qty) AS TRANSACTED_QUANTITY,
                        pt.name as PRODUCT_NAME,
                        --                po.name,
                        --                ppm.name AS PAYMENT_METHOD,
                        --                aj.oracle_pointer AS ORACLE_POINTER,
                        pc.name as PRODUCT_CATEGORY,
                        rc.name as COMPANY_NAME,
                        rc.short_code AS COMPANY_SHORT_CODE,
                                    CASE
                                        WHEN pprod.product_tmpl_id = pt.id THEN 'Variant'
                                        ELSE 'Product'
                                    END AS ITEM_TYPE,
                                    sl.name AS PRODUCT_STOCK_LOCATION_NAME,
                                    sq.quantity AS CURRENT_STOCK_QUANTITY, -- Current stock quantity
                                    puom.name AS PRODUCT_UOM_NAME, -- Product unit of measurement
                                    puom_purchase.name AS PURCHASE_UOM_NAME -- Purchase unit of measurement
                                FROM
                                    pos_order_line pol
                                JOIN
                                    pos_order po ON pol.order_id = po.id
                                JOIN
                                    pos_payment pp ON po.id = pp.pos_order_id
                                JOIN
                                    pos_payment_method ppm ON pp.payment_method_id = ppm.id
                                JOIN
                                    product_product pprod ON pol.product_id = pprod.id
                                JOIN
                                    product_template pt ON pprod.product_tmpl_id = pt.id
                                JOIN
                                    product_category pc ON pt.categ_id = pc.id
                                JOIN
                                    res_company rc ON po.company_id = rc.id
                                JOIN
                                    account_journal aj ON aj.id = ppm.journal_id
                                JOIN
                                    stock_move sm ON sm.product_id = pol.product_id -- AND sm.name = po.name
                                JOIN
                                    stock_location sl ON sm.location_id = sl.id
                                LEFT JOIN
                                    stock_quant sq ON sq.product_id = pol.product_id AND sq.location_id = sl.id
                                JOIN
                                    uom_uom puom ON pt.uom_id = puom.id -- Join for product UoM
                                JOIN
                                    uom_uom puom_purchase ON pt.uom_po_id = puom_purchase.id -- Join for purchase UoM
                                WHERE
                                    po.id in %s and
                                    sl.name not in ('Customers', 'Inventory adjustment')
                                GROUP BY
                                    -- pol.qty,
                    --                sm.name,
                                    ITEM_CODE,
                                    pt.name,
                                    po.name,
                    --                ppm.name,
                                    pc.name,
                                    rc.name,
                                    rc.short_code,
                                    aj.oracle_pointer,
                                    sl.name,
                                    ITEM_TYPE,
                                    sq.quantity,
                                    puom.name,
                                    puom_purchase.name
        """

        self.env.cr.execute(agg_qty_query, (order_ids,))

        return self.env.cr.dictfetchall()

    def get_return_orders(self):
        query = """
                select
                    distinct
                    po.id,
                    case, '
                        when pprod.product_tmpl_id = pt.id then pprod.default_code
                        else pt.default_code
                    end as ITEM_CODE,
                    pol.qty as TRANSACTED_QUANTITY,
                    pt.name as PRODUCT_NAME,
                    ppm.name as PAYMENT_METHOD,
                    aj.oracle_pointer as ORACLE_POINTER,
                    pc.name as PRODUCT_CATEGORY,
                    rc.name as COMPANY_NAME,
                    rc.short_code as COMPANY_SHORT_CODE,
                    case
                        when pprod.product_tmpl_id = pt.id then 'Variant'
                        else 'Product'
                    end as ITEM_TYPE,
                    sl.name as PRODUCT_STOCK_LOCATION_NAME,
                    sq.quantity as CURRENT_STOCK_QUANTITY,
                    -- Current stock quantity
                    puom.name as PRODUCT_UOM_NAME,
                    -- Product unit of measurement
                    puom_purchase.name as PURCHASE_UOM_NAME
                    -- Purchase unit of measurement
                from
                    pos_order_line pol
                join
                                pos_order po on
                    pol.order_id = po.id
                join
                                pos_payment pp on
                    po.id = pp.pos_order_id
                join
                                pos_payment_method ppm on
                    pp.payment_method_id = ppm.id
                join
                                product_product pprod on
                    pol.product_id = pprod.id
                join
                                product_template pt on
                    pprod.product_tmpl_id = pt.id
                join
                                product_category pc on
                    pt.categ_id = pc.id
                join
                                res_company rc on
                    po.company_id = rc.id
                join
                                account_journal aj on
                    aj.id = ppm.journal_id
                join
                                stock_move sm on
                    sm.product_id = pol.product_id
                join
                                stock_location sl on
                    sm.location_id = sl.id
                left join
                                stock_quant sq on
                    sq.product_id = pol.product_id
                    and sq.location_id = sl.id
                join
                                uom_uom puom on
                    pt.uom_id = puom.id
                    -- Join for product UoM
                join
                                uom_uom puom_purchase on
                    pt.uom_po_id = puom_purchase.id
                    -- Join for purchase UoM
                where
                    pol.qty < 0
                    and sl.name not in ('Customers', 'Inventory adjustment')
                group by
                    pol.qty,
                    po.id,
                    sm.name,
                    po.name,
                    ITEM_CODE,
                    pt.name,
                    po.name,
                    ppm.name,
                    pc.name,
                    rc.name,
                    rc.short_code,
                    aj.oracle_pointer,
                    sl.name,
                    ITEM_TYPE,
                    sq.quantity,
                    puom.name,
                    puom_purchase.name
        """

        self.env.cr.execute(query)

        return self.env.cr.dictfetchall()

    def mark_orders_sent_to_oracle(self, order_ids):
        orders = self.browse(order_ids)
        orders.write({"sent_to_oracle": True})
        self.env.cr.commit()  # Commit the transaction

    @api.model
    def action_send_sms(self, order_data):
        try:
            partner_id = order_data.get("partner_id")
            name = order_data.get("name")
            amount_paid = order_data.get("amount_paid")
            message = f"{name} has been paid with {amount_paid} BDT. Thankyou from BuildBest."
            if partner_id:
                partner = self.env["res.partner"].browse(partner_id)
                if partner.mobile:
                    payload = {
                        "username": "NMohdadmin",
                        "password": "NMohdadmin@123",
                        "apicode": "1",
                        "msisdn": partner.mobile,
                        "countrycode": "880",
                        "cli": "Build Best",
                        "messagetype": "1",
                        "message": message,
                        "messageid": "0",
                    }
                    resp = r.post("https://gpcmp.grameenphone.com/ecmapigw/webresources/ecmapigw.v2", json=payload)
                    
                    msg = resp.json()

                    if msg.get("statusCode") == "200":
                        _logger.info(f"SMS has been sent to {partner.mobile}")
                        return True

                _logger.error(f"SMS Send Action Failed with Message [{msg.get('message')}] for Order {name}")
                return False
        except Exception as exc:
            _logger.exception(exc)
            return False

    def update_orders_to_sent(self):
        query = """
                update
                    pos_order po
                set
                    po.sent_to_oracle = true
                where po.date_order::date <= current_date
        """
        self.env.cr.execute(query)