# -*- coding: utf-8 -*-
# Copyright 2016 Openworx, LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "KG Sale",
    "summary": "Sale Modifications",
    "version": "16.0",
    "category": "Sale",
    "website": "www.klystronglobal.com",
    "description": """
		Sale Modifications
    """,

    "author": "KG",
    "installable": True,
    "depends": [
        'sale', 'hr', 'sales_team', 'web', 'kg_crm', 'sale_margin', 'kg_inventory', 'sale_management', 'product','sale_customization',
        'stock', 'contacts', 'base', 'kg_purchase', 'account', 'iwesabe_slno_in_sale_order_line', 'kg_amount_words','account_debit_note'
    ],
    "data": [
        'security/ir.model.access.csv',
        'security/menu_hide_security.xml',
        'data/proforma_invoice_seq.xml',
        'wizard/so_po_wizard_view.xml',
        'views/res_partner_view.xml',
        'views/menu.xml',
        'views/brand_view.xml',
        'views/product_category_view.xml',
        'views/product_cost_history_view.xml',
        'views/optional_product_view.xml',

        'views/product.xml',
        'views/revisions_view.xml',
        'views/account_move.xml',
        # 'views/order_line_template.xml',
        'views/account_payment_view.xml',
        'views/sale_order.xml',
        'views/stock_picking.xml',
        'views/account_menu.xml',
        'report/invoice_temp_new_without_header.xml',
        'report/report.xml',
        'report/quotation_alan_with_h.xml',
        'report/proforma_invoice_without.xml',

        'report/qoutation_alan.xml',
        'report/so_alan.xml',
        'report/report_picking_template.xml',

        'report/rak_checq.xml',
        'report/emirates_islamic_checq.xml',
        'report/invoice_template_new.xml',
        'report/proforma_invoice_template.xml',
        'report/refund_invoice_new.xml'

    ],
    'assets': {
        'web.assets_backend': [
            # 'kg_sale/static/src/css/line.css',
            'kg_sale/static/src/css/order_line_style.css',

        ],
    },
    'license': 'LGPL-3',
}
