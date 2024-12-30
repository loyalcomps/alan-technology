# -*- coding: utf-8 -*-
# Copyright 2016 Openworx, LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "KG CRM",
    "summary": "CRM Modifications",
    "version": "16.0",
    "category": "CRM",
    "website": "www.klystronglobal.com",
	"description": """
		CRM Modifications
    """,
	
    "author": "KG",
    "installable": True,
    "depends": [
        'crm','hr',
    ],
    "data": ['security/ir.model.access.csv',
      'views/industry_view.xml',
      'views/payment_extension.xml',
      'views/validity.xml',
      'views/lpo_terms.xml',
      'views/delivery.xml',
      'views/warranty.xml',
      'views/size.xml',
      'views/crm_menu.xml',
      # 'views/product.xml',

    ],
}

