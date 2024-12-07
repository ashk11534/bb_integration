from odoo import models



class ExtendedPosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_res_company(self):
        return {
            'search_params': {
                'domain': [('id', '=', self.company_id.id)],
                'fields': [
                    'currency_id', 'email', 'website', 'company_registry', 'vat', 'name', 'phone', 'partner_id',
                    'country_id', 'state_id', 'tax_calculation_rounding_method', 'nomenclature_id', 'point_of_sale_use_ticket_qr_code',
                    'street', 'city'
                ],
            }
        }
