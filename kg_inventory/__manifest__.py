# -*- coding: utf-8 -*-
# Copyright 2016 Openworx, LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "KG Inventory",
    "summary": "Inventory Modifications",
    "version": "10.0",
    "category": "Inventory",
    "website": "www.klystronglobal.com",
    "description": """
		Inventory Modifications
    """,

    "author": "KG",
    "installable": True,
    "depends": [
        'stock', 'sale', 'account', 'kg_purchase'
    ],
    "data": [
        'security/ir.model.access.csv',
        'security/security_groups.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
        'views/amc_assets.xml',
        'report/report.xml',
        'report/proforma_invoice_template.xml'

    ],
}
