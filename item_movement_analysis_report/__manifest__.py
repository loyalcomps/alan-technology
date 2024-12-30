{
    'name': "Item Movement Analysis Report",
    'author': 'Klystron',
    'category': 'Account',
    'summary': """Report for product movement analysis""",
    'license': 'AGPL-3',
    'description': """
""",
    'version': '16.0.1.0.0',
    'depends': ['base', 'stock', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard.xml',
        'report/item_analysis_template.xml',
        'report/report.xml'
    ],
    'installable': True,

    'application': True,
    'auto_install': False,
}
