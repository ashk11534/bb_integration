# -*- coding: utf-8 -*-
{
    "name": "Build Best Integrations",
    "version": "1.0.0",
    "summary": """
        All the integrations happens in this module for Build Best Org.""",
    "description": """
        This only one module should be used for Build Best Integrations with Oracle and others in 
        future.
    """,
    "author": "Jiaul Islam Jibon",
    "website": "https://www.waltondigitech.com",
    "category": "Technical",
    "sequence": "1",
    "maintainer": "WDTIL",
    "support": "computer.it21@waltonbd.com",
    "depends": ["base", "point_of_sale", "stock"],
    "installable": True,
    "application": True,
    "auto_install": False,
    "data": [
        "views/ir_cron.xml",
        "views/account_journal_views.xml",
        "views/account_move_views.xml",
        "views/pos_order_views.xml",
        "views/res_company_views.xml",
        "views/pos_index.xml",
        "views/res_partner_views.xml",
        "security/ir.model.access.csv",
        "views/stock_immediate_transfer_views.xml",
        "views/invoice_report.xml",
    ],
    "assets": {
        "point_of_sale.assets": [
            "bb_integrations/static/src/js/**/*",
            "bb_integrations/static/src/xml/**/*",
            "bb_integrations/static/src/scss/*.scss",
        ]
    },
}
