# -*- coding: utf-8 -*-
{
    'name': "PDC Payment",

    'summary': """
        Allows users to handle PDC payment from payment window""",

    'description': """
        Allows users to handle PDC payment from payment window
    """,

    'author': "Loyal IT Solutions Pvt Ltd",
    'website': "http://www.loyalitsolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '16.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'om_account_accountant','branch'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/pdc_security.xml',
        'data/data.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
}
