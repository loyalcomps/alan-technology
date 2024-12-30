# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime


class Project(models.Model):
    _inherit = 'project.project'
    _order = 'ticket_number asc'

    def project_asset_action(self):
        return {
            'name': _('Asset'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.asset',
            'view_mode': 'tree,form',
            'context': {
                'default_project_id': self.id,
            }
        }

    def _compute_task_count(self):
        for project in self:
            project.task_count = len(project.task_ids)

    def attachment_tree_view(self):
        self.ensure_one()
        domain = [
            '|',
            '&', ('res_model', '=', 'project.project'), ('res_id', 'in', self.ids),
            '&', ('res_model', '=', 'project.task'), ('res_id', 'in', self.task_ids.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                        Documents are attached to the tasks and issues of your project.</p><p>
                        Send messages or log internal notes with attachments to link
                        documents to your project.
                    </p>'''),
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }


    @api.depends('task_ids.total_cost')
    def _get_compute_cost(self):
        for data in self:
            task_ids = data.task_ids
            cost = 0
            for task in task_ids:
                cost = cost + task.total_cost
            data.total_cost = cost

    def _compute_issue_count(self):
        for project in self:
            project.issue_count = self.env['project.issue'].search_count(
                [('project_id', '=', project.id), '|', ('stage_id.fold', '=', False), ('stage_id', '=', False)])

    privacy_visibility = fields.Selection([
        ('followers', _('On invitation only')),
        ('employees', _('Visible by all employees')),
        ('portal', _('Visible by following customers')),
    ],
        string='Privacy', required=True,
        default='portal',
        help="Holds visibility of the tasks or issues that belong to the current project:\n"
             "- On invitation only: Employees may only see the followed project, tasks or issues\n"
             "- Visible by all employees: Employees may see all project, tasks or issues\n"
             "- Visible by following customers: employees see everything;\n"
             "   if website is activated, portal users may see project, tasks or issues followed by\n"
             "   them or by someone of their company\n")
    use_tasks = fields.Boolean('Tasks', default="False")
    use_issues = fields.Boolean('Issues', default="False")
    task_count = fields.Integer(compute='_compute_task_count')
    issue_count = fields.Integer(compute='_compute_issue_count')

    kg_sector = fields.Selection([
        ('managed_service', 'Managed Service'),
        ('elv_division', 'ELV Division'),
        ('it_product_sales', 'IT Product Sales'),
    ], string='Sector', default='managed_service')
    kg_servicecall_categories = fields.Selection([
        ('new_installation', 'New Installation'),
        ('amc', 'Annual Maintenance Contract(AMC)'),
        ('rma', 'RMA - Faulty Product Service'),
        ('poc', 'Proof Of Concept(POC)'),
    ], store=True, default='new_installation', string='Service Type')
    sub_task_project_id = fields.Many2one('project.project')
    type_ids = fields.One2many('project.task.type', 'project_ids')

    kg_type = fields.Selection([
        ('free', 'Free'),
        ('paid', 'Paid'),
    ], string='Cost Type', default='free')
    # service_type1 = fields.Selection(string='Service Type1',related='analytic_account_id.kg_servicecall_categories')
    user_id = fields.Many2one('res.users')
    alias_name = fields.Char('Email Alias')
    alias_model = fields.Selection(selection=[('project.task', 'Tasks'), ('project.issue', 'Issues')],
                                   string="Incoming Emails create")
    alias_contact = fields.Selection(
        selection=[('everyone', 'Everyone'), ('partners', 'Authenticated Partners'), ('followers', 'Followers Only'),
                   ('employees', 'Authenticated Employees')], string="Accept Emails From")
    kg_type_of_service = fields.Selection([
        ('on_site', 'ON-Site'),
        ('remotely', 'Remote'),
        ('over_the_phone', 'Over the Phone'),
        ('in_house', 'In House'),
    ], string='Support Type', default='on_site')

    kg_state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_complete', 'In Progress'),
        ('completed', 'Done'),
    ], string='State', default='draft')

    kg_required = fields.Boolean(default=False)
    kg_actual_start_date = fields.Datetime('Pro Start Date')
    kg_actual_end_date = fields.Datetime('Pro End Date')
    sequence = fields.Integer('Sequence')
    resource_calendar_id = fields.Many2one('resource.calendar', 'Working Time')
    service_requested_date = fields.Date(string="Service Requested Date", default=fields.Datetime.now, )

    proposed_service_charge = fields.Float(string="Proposed Service Charge")
    kg_salesman_id = fields.Many2one('res.users', string="Salesperson", default=lambda self: self.env.user)
    total_cost = fields.Float(compute='_get_compute_cost', string="Total Cost", store="True")
    sale_order_id = fields.Many2one('sale.order', 'Sale Order')
    ticket_number = fields.Char(required=True, copy=False, readonly=True, index=True,
                                default=lambda self: ('New'), string='Ticket No.')
    serial_no = fields.Char('Serial No:/Invoice No:')

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        values['ticket_number'] = self.env['ir.sequence'].next_by_code('ticket.number') or 'New'
        result = super(Project, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True,
                                                  mail_notrack=False)).create(values)
        customer_id = values.get('partner_id', False)
        users = self.env['res.users'].browse(customer_id)
        if users:
            result.message_subscribe(users.ids)
        return result

    def write(self, values):
        """ Override to avoid automatic logging of creation """
        result = super(Project, self).write(values)
        customer_id = values.get('partner_id', False)
        users = self.env['res.users'].browse(customer_id)
        return result

    @api.onchange('kg_servicecall_categories')
    def onchange_categories(self):
        if self.kg_servicecall_categories == 'amc':
            self.kg_required = True
        else:
            self.kg_required = False

    def start(self):
        self.kg_state = 'in_complete'
        start_date = datetime.today()
        self.kg_actual_start_date = start_date
        return True

    def done(self):
        self.kg_state = 'completed'
        project_id = self.id
        task_ids = self.env['project.task'].search([('project_id', '=', project_id)])
        for task in task_ids:
            if not task.is_it_done:
                raise UserError(_('some of the tasks are not completed'))
        end_date = datetime.now()
        self.kg_actual_end_date = end_date
        return True


