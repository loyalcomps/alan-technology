# Ashish Thomas
{
    "name": "Check layout",
    "summary": "Set Layout for Check",
    "version": "14.0.1.0.0",
    'category': 'Accounting/Accounting',
    "author": "Ashish Thomas",
    "license": "AGPL-3",
    "depends": ["account_check_printing"],
    "data": [
        'security/ir.model.access.csv',
        'views/check_layout_view.xml',
        'views/payment_view.xml',
        'reports/check_layout_print.xml'
             ],
    "installable": True,
}
