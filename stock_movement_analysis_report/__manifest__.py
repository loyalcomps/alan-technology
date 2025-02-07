{
    'name': "Stock Movement Analysis",

    'summary': """
        Its used for print the repot
        of stock movement analysis""",

    'description': """
        Its used for print the repot
        of stock movement analysis
    """,

    'author': "Klystron",
    'maintainer': 'KG',
    'website': "www.klystronglobal.com",

    'category': 'Generic Modules/Warehouse',
    'version': '10.0.0.1',

    'depends': [
        'purchase',
        'account',
        'sale_stock',
        'stock',
        'kg_sale',
        'kg_inventory'
    ],

    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard.xml',
        'report/report.xml',
        'report/stock_analysis_template.xml',

    ]

}
