# -*- coding: utf-8 -*-
{
    "name": "Sale Customization",
    "summary": "Sale Customization",
    "version": "16.0",
    "category": "CRM",
    "website": "www.loyalitsolutions.com",
    "description": """
		Sales approval and set credit limit inside the customer
    """,

    "author": "KG",
    "installable": True,
    "depends": ['base', 'sale_management'
                ],
    "data": [
        'security/security.xml',
        'data/cron_jobs.xml',
        'views/approval.xml',
        'views/partner.xml'
        #      'views/validity.xml',
        #      'views/lpo_terms.xml',
        #      'views/delivery.xml',
        #      'views/warranty.xml',
        #      'views/size.xml',
        #      'views/crm_menu.xml',
        # 'views/product.xml',

    ],
}
