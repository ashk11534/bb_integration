odoo.define("bb_integrations.SendSMS", function (require) {
    "use strict"

    const { Gui } = require("point_of_sale.Gui");
    const PosComponent = require("point_of_sale.PosComponent");
    const Registries = require("point_of_sale.Registries");


    class SendSMSButton extends PosComponent {

        async onClick() {
            const order = this.env.pos.get_order();
            const mobileNumber = order.partner.mobile;
            if (order) {
                const orderData = order.export_as_JSON();
                if (mobileNumber) {
                    await this.rpc({
                        model: "pos.order",
                        method: "action_send_sms",
                        args: [orderData],
                    });

                    Gui.showPopup('ConfirmPopup', {
                        title: "SMS Sent",
                        body: "An SMS has been sent to the customer",
                    })
                } else {
                    Gui.showPopup('ErrorPopup', {
                        title: 'No Customer Mobile',
                        body: 'Please make sure customer has mobile first.',
                    });
                }
            }
        }
    }

    SendSMSButton.template = "SendSMSButton";
    Registries.Component.add(SendSMSButton);

    return SendSMSButton;
});