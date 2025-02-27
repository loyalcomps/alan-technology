# -*- coding: utf-8 -*-
{
    'name': "KG Bank Reconcilation Module",

    'author': "SHARMI SV",
    'website': 'https://www.klystronglobal.com',

    'version': '16.0.3.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/bank_statement_view.xml',
        'report/bank_statement_reconciliation_alan.xml',
        'report/bank_statement_reconciliation_template.xml',
        'report/report_bank_stmnt_reconciliation_week.xml',
        'report/report.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}