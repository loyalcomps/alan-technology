{
    'name': 'KG Project',
    'version': '16.0.1.0.0',
    'description': 'KG Project',
    'depends': ['base', 'project', 'sale_management', 'uom', 'sale_timesheet', 'hr_timesheet', 'account'],
    'data': [
        'security/security_group.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/res_config_settings_views.xml',
        'views/employee_views.xml',
        'views/res_partner_views.xml',
        'views/project_views.xml',
        'views/task_views.xml',
        'views/search_menu_views.xml',
        'views/project_issue_view.xml',
        'views/asset.xml',
        'reports/project_issue_report_views.xml',
        'reports/task_assigned_report.xml',
        'reports/task_completed_report.xml'
    ]
}
