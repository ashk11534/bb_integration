from odoo import models, fields


class ExtendedStockMoveLine(models.Model):
    _inherit = "stock.move.line"

    is_processed = fields.Boolean(string="Sent?", default=False)

    def get_stock_moves_today(self):
        query = """
                select
                    sml.move_id as move_id,
                    rc.short_code as org_unit,
                    src_location.name as src_loc,
                    dest_location.name as dest_loc,
                    pt.default_code as item_code,
                    'MISC_ISSUE_INV_VAL' as oracle_pointer,
                    sml.date as txn_date,
                    sum(sml.qty_done / uu.factor) as sold_in_puom
                from
                    stock_move_line sml
                join
                    stock_location src_location on
                    src_location.id = sml.location_id
                join
                    stock_location dest_location on
                    dest_location.id = sml.location_dest_id
                join
                    product_product pt on
                    pt.id = sml.product_id
                join product_template pt2 on
                    pt2.id = pt.product_tmpl_id
                join
                    uom_uom uu on
                    uu.id = pt2.uom_id
                join
                    res_company rc on
                    rc.id = sml.company_id
                left join
                    stock_quant sq on
                    sq.product_id = pt.id
                    and sq.location_id = src_location.id
                where
                    dest_location.usage = 'customer'
                    and pt.default_code is not null
                    and sml.date::date = current_date
                    and sml.is_processed is not true
                group by
                    sml.move_id,
                    rc.short_code,
                    src_location.name,
                    dest_location.name,
                    pt.default_code,
                    sml.date
                HAVING
                SUM(sml.qty_done / uu.factor) > 0
        """

        self.env.cr.execute(query)

        return self.env.cr.dictfetchall()
    
    def get_return_stock_moves_today(self):
        query = """
            select
                rc.short_code as org_unit,
                src_location.name as dest_loc,
                dest_location.name as src_loc,
                pt.default_code as item_code,
                current_date as txn_date,
                'MISC_RCPT_INV_VAL' as oracle_pointer,
                sml.is_processed,
                sum(sml.qty_done / uu.factor) as sold_in_puom
            from
                stock_move_line sml
            join
                stock_location src_location on
                src_location.id = sml.location_id
            join
                stock_location dest_location on
                dest_location.id = sml.location_dest_id
            join
                product_product pt on
                pt.id = sml.product_id
            join 
                product_template pt2 on
                pt2.id = pt.product_tmpl_id
            join
                uom_uom uu on
                uu.id = pt2.uom_id
            join
                res_company rc on
                rc.id = sml.company_id 
            left join
                stock_quant sq on
                sq.product_id = pt.id
                and sq.location_id = src_location.id
            where
                src_location.usage = 'customer'
                and sml.date::date = current_date
                and sml.is_processed is not true 
            group by 
                rc.short_code,
                src_location.name,
                dest_location.name,
                sml.is_processed ,
                pt.default_code
        """

        self.env.cr.execute(query)

        return self.env.cr.dictfetchall()
    
    def update_today_stock_status(self):
        query = """
                update
                    stock_move_line sml
                set
                    is_processed = true
                from
                    stock_location dest_loc
                where
                    sml.location_dest_id = dest_loc.id
                    and dest_loc.usage = 'customer'
                    and sml.date::date = current_date
        """
        self.env.cr.execute(query)

    def update_today_stock_status_for_refund(self):
        query = """
                update
                    stock_move_line sml
                set
                    is_processed = true
                from
                    stock_location src_loc
                where
                    sml.location_id = src_loc.id
                    and src_loc.usage = 'customer'
                    and sml.date::date = current_date
        """
        self.env.cr.execute(query)

    def update_item_oracle_status(self, arr):
        query = """
                update
                    stock_move_line sml
                set
                    is_processed = true
                from
                    stock_location dest_loc, product_product pp
                where
                    sml.location_dest_id = dest_loc.id
                    and dest_loc.usage = 'customer'
                    and sml.date::date = current_date
                    and sml.product_id = pp.id
                    and pp.default_code in %s

        """
        self.env.cr.execute(query, (tuple(arr),))
