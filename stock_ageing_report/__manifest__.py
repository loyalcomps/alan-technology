# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Devintelle Software Solutions (<http://devintellecs.com>).
#
##############################################################################
{
    'name': "Stock Inventory Aging Report PDF/Excel",
    'summary': """
        Apps will print Stock Aging Report by Compnay, Warehoouse, Location, Product Category and Product.""",
    'description': """
        Apps will print Stock Aging Report by Compnay, Warehoouse, Location, Product Category and Product.


Stock Inventory Aging Report PDF/Excel
Odoo Stock Inventory Aging Report PDF/Excel
Stock inventory againg report
Oddo stock againg report
Print stock inventory againg report
Odoo print stock againg report
Non moving product report
Odoo non moving report
Print non moving product report
Odoo print non moving product report
Non moving inventory 
Odoo non moving inventory
Non moving inventory report
Odoo non moving inventory report
Inventory age report
Odoo inventory age report
Inventory break down report
Odoo inventory break down report
Inventory Age Report & Break Down Report
Inventory Age Report and Break Down Report
Odoo Inventory Age Report and Break Down Report

Odoo  Inventory Age Report & Break Down Report
Print inventory age report
Odoo print inventory age report
Stock ageing report
Odoo stock ageing report
Stock Ageing Excel Report
Odoo Stock Ageing Excel Report
Stock Aging Report by Company
Odoo Stock Aging Report by Company
   Odoo inventory report 

    """,
    'author': "DevIntelle Consulting Service Pvt.Ltd",
    'website': "http://devintelle.com/",
    'category': 'Generic Modules/Warehouse',
    'version': '1.1',
    'sequence': 1,
    'depends': [
        'base',
        'mrp',
        'mrp_account',
        'uom',
        'purchase',
        'account',
        'stock',
        'sale_stock',
        'kg_sale',
        'product'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard.xml',
        'report/report.xml',
        'report/stock_ageing_template.xml',
    ],

    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 35.0,
    'currency': 'EUR',
    'live_test_url': 'https://youtu.be/Sg7NnM_Bz7E',

}
