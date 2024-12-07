odoo.define("bb_integrations.models", function (require) {
    "use strict"

    var { Order } = require("point_of_sale.models");
    var Registries = require("point_of_sale.Registries");

    const ExtendedOrder = (Order) => class ExtendedOrder extends Order {

        get_client_info() {
            const client = this.get_partner();
            return {
                name: client ? client.name : null,
                mobile: client ? client.mobile : null,
            };
        }

        get_company_full_addr() {
            const company = this.pos.company;
            return `${company.street}, ${company.city}`;
        }

        export_for_printing() {
            var output = super.export_for_printing(...arguments);
            output.company.full_address = this.get_company_full_addr();
            output.client = this.get_client_info();
            return output;
        }

    }
    Registries.Model.extend(Order, ExtendedOrder);
})