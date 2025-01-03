# -*- coding: utf-8 -*-
{
    'name': "PDC Management (Community) ",
     'summary': """
 PDC ( Post Dated Cheque) Management. | PDC Payment for single Invoice/Bill |PDC Payment can be monitored in chatter
        """,
    'description': """
In Invoice/Bill, a post-dated cheque is a cheque written by the customer/vendor (payer) for a date in the future. Whether a post-dated cheque may be cashed or deposited before the date written on it depends on the country. Currently, odoo does not provide any kind of feature to manage post-dated cheque. That why we make this module, it will help to manage a post-dated cheque with accounting journal entries. This module provides a feature to Register PDC Cheque in an account. This module allows to manage postdated cheque for the customer as well vendors, you can easily track/move to a different state of cheque like new, registered, return, deposit, bounce, done. We have taken care of all states with accounting journal entries, You can easily list filter cheque with different states.There is an user role Accountant Treasury. The user who has access for that user role can only do the bounce and done process. To verify the process from Treasury end if the other process are done by a junior accountant. 
    """,
    'author': "Loyal IT Solutions Pvt Ltd",
    'website': "https://www.loyalitsolutions.com/",
    'category': 'account',
    'version': '16.0.1',
    'license': 'AGPL-3',
    'price': '20.00',
    'currency': 'EUR',    
    'support': "support@loyalitsolutions.com",
    'depends': ['base', 'account',],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/res_config_settings_views.xml',
        'security/pdc_security.xml',
         'security/accounts_security.xml',
        'wizard/pdc_date_wizard_view.xml',
        'wizard/account_pdc_register_view.xml',
        'views/views.xml',
        'views/account_move_view.xml',
    ],
    'images': ['static/description/banner.png'],
}