# -*- coding: utf-8 -*-
{
    'name': "Misc Journal Matching",

    'summary': """
        Miscallaneous Journal Matching""",

    'description': """
        Long description of module's purpose
    """,

'author': "Loyal IT Solutions Pvt Ltd",
    'website': "https://www.loyalitsolutions.com/",
    'category': 'account',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list

    'version': '17.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
'wizard/payment_allocation_wizard.xml',
        'views/account_move_inherit.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
