{
    'name': 'KG Purchase',
    'version': '16.0.1.0.0',
    'description': 'KG Purchase',
    'depends': ['base', 'purchase', 'account', 'sale','stock'],
    'data': [
        'security/ir.model.access.csv',
        'reports/po_template.xml',
        'reports/purchase_order_template.xml',
        'reports/delivery_note.xml',
        'reports/deliver_note_without_header.xml',
        'reports/stock_report_delivery_slip_inherit.xml',
        'wizard/purchase_order_group_view.xml',
        'views/purchase_order_view.xml',
        'views/company.xml',
        'views/product_product_views.xml',
        'views/kg_supplier_type_view.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_view.xml',
        'views/res_users_view.xml',
        ]
}
