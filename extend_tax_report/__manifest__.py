# -*- coding: utf-8 -*-

{
    'name': 'Extend Tax Report',
    'version': '16.0.1.0.1',
    'category': 'Sales',
    'summary': "Tax Report with detailed lines",
    'description': """Tax Report with detailed lines""",
    'sequence': '10',
    'author': 'Knowledge Bonds',
    'license': 'LGPL-3',
    'company': 'Knowledge Bonds',
    'maintainer': 'Knowledge Bonds',
    'depends': ['accounting_pdf_reports'],
    'demo': [],
    'data': [
        'wizards/tax_report_wizard.xml',
        'reports/tax_report.xml',
        'reports/report.xml',
        # 'views/templates.xml'

    ],

    'installable': True,
    'application': False,
    'auto_install': False,
    'qweb': [],
    'images': ['static/description/banner.png'],
}