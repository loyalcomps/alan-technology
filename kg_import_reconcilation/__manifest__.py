# -*- coding: utf-8 -*-
{
    'name': "Import Reconcilation",
    'version': '16.0.1.0.0',
    'depends': ['base','account'],
    'author': 'Ashvad',
    'description': "Import Reconcilation",
    'maintainer': "Ashvad",
    'category': 'import/Reconcilation',

    'data': [
        'security/ir.model.access.csv',
        'views/import_reconcile.xml'
    ],

    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False
}
