from odoo import models, api


class StockUpdate(models.Model):
    _inherit = 'product.product'

    @api.model
    def update_stock_from_external_system(self, item_code, quantity, location_code):
        # Find the product by item code
        product = self.env['product.product'].search([('default_code', '=', item_code)], limit=1)
        if not product:
            raise ValueError(f"Product with item code {item_code} not found.")
        
        # Find the stock location by location code
        location = self.env['stock.location'].search([('name', '=', location_code)], limit=1)
        if not location:
            raise ValueError(f"Location with code {location_code} not found.")
        
        # Create an inventory adjustment for the specific location
        inventory = self.env['stock.inventory'].create({
            'name': f'Stock Adjustment for {product.name} at {location.complete_name}',
            'location_id': location.id,
            'product_ids': [(6, 0, [product.id])],
        })
        
        # Create an inventory line for the adjustment
        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'product_id': product.id,
            'product_qty': quantity,
            'location_id': location.id,
        })
        
        # Start and validate the inventory adjustment
        inventory.action_start()
        inventory.action_validate()
        
        return True