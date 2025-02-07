# -*- coding: utf-8 -*-


{
    'name': 'Vendor Outstanding Statement',
    'version': '16.0.1.0.0',
    'category': 'Accounting & Finance',
    'summary': 'OCA Financial Reports',
    'author': "Ameen",
    'license': 'AGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/report_action.xml',

        'report/invoice_outstanding_template.xml',
        'wizard/vendor_outstanding_statement_wizard.xml',
        'views/statement.xml',

        'views/moveline.xml'
    ],
    'installable': True,
    'application': False,
}
