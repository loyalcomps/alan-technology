# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api
from datetime import datetime

_STATES = [
    ('draft', 'Draft'),
    ('assigned', 'Assigned'),
    ('partially_complete', 'Partially Completed'),
    ('completed', 'Completed'),
    ('cancel', 'Cancelled')]


class Task(models.Model):
    _inherit = "project.task"

    def start_send_by_email(self):
        self.start_email_sent = True
        return True

    def service_assign(self):
        for data in self:
            data.write({'kg_state': 'assigned'})
        return True

    def service_partial(self):
        for data in self:
            data.write({'kg_state': 'partially_complete'})
        return True

    def service_complete(self):
        for data in self:
            data.write({'kg_state': 'completed'})
        return True

    def done_send_by_email(self):
        self.done_email_sent = True
        return True

    def done(self):
        self.is_it_done = True
        return True

    @api.depends('project_id')
    def _get_material_status(self):
        for data in self:
            if data.project_id.kg_required == True:
                data.date_required = True
            else:
                data.date_required = False

    # def convert_datetime_field(self, datetime_field):
    #     user = self.env.user
    #     dt = datetime.strptime(datetime_field, '%Y-%m-%d %H:%M:%S')
    #     if user and user.tz:
    #         user_tz = user.tz
    #         if user_tz in pytz.all_timezones:
    #             old_tz = pytz.timezone('UTC')
    #             new_tz = pytz.timezone(user_tz)
    #             dt = old_tz.localize(dt).astimezone(new_tz)
    #         else:
    #             old_tz = pytz.timezone('UTC')
    #             dt = old_tz.localize(dt).astimezone('UTC')
    #             # _logger.info("Unknown timezone {}".format(user_tz))
    #
    #     return datetime.strftime(dt, '%d/%m/%Y %H:%M:%S')
    #
    # def convert_TZ_UTC(self, TZ_datetime):
    #     fmt = "%Y-%m-%d %H:%M:%S"
    #     fmt1 = "%d-%m-%Y %H:%M:%S"
    #     # Current time in UTC
    #     now_utc = datetime.now(pytz.timezone('UTC'))
    #     # Convert to current user time zone
    #     now_timezone = now_utc.astimezone(pytz.timezone(self.env.user.tz))
    #     UTC_OFFSET_TIMEDELTA = datetime.strptime(now_utc.strftime(fmt), fmt) - datetime.strptime(
    #         now_timezone.strftime(fmt), fmt)
    #     local_datetime = datetime.strptime(TZ_datetime, fmt)
    #     result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
    #     return result_utc_datetime.strftime(fmt1)

    @api.depends('timesheet_ids.unit_amount')
    def _hours_worked(self):
        for rec in self:
            now = fields.Datetime.from_string(fields.Datetime.now())
            duration = relativedelta(now, now)
            total_hr = 0
            for data in rec.timesheet_ids:
                if data.date_from and data.date_to:
                    start_date = fields.Datetime.from_string(data.date_from)
                    end_date = fields.Datetime.from_string(data.date_to)
                    dif_tot = relativedelta(end_date, start_date)
                    duration = duration + dif_tot
                    dif_minut = (duration.days * 24 * 60) + (duration.hours * 60) + (duration.minutes)
                    total_hr = (dif_minut / 60) + (dif_minut % 60) / float(100)
            rec.kg_effective_hours = total_hr
            rec.kg_remaining_hours = rec.planned_hours - total_hr

    @api.depends('kg_hourly_rate', 'total_worked_hours')
    def _get_compute_cost(self):
        for data in self:
            kg_hourly_rate = data.kg_hourly_rate
            total_worked_hours = data.total_worked_hours
            data.total_cost = total_worked_hours * kg_hourly_rate

    project_id = fields.Many2one('project.project',
                                 default=lambda self: self.env.ref('kg_project.new_project_dummy'))
    user_id = fields.Many2one('res.users', 'Service Engineer', default=False)
    ticket_number = fields.Char(required=True, copy=False, readonly=True, index=True,
                                default=lambda self: ('New'), string='Ticket No.')
    start_email_sent = fields.Boolean('Start Alert')
    kg_effective_hours = fields.Float(compute='_hours_worked', store=True, string='Worked Hours1',
                                   help="Computed using the sum of the task work done.")
    planned_hours = fields.Float(string='Initially Planned Hours',
                                 help='Estimated time to do the task, usually set by the project manager when the task is in draft state.')
    kg_remaining_hours = fields.Float(compute='_hours_worked', store=True, string='Remaining Hours1',
                                   help="hoo using the sum of the task work done.")
    gp_deduction_required = fields.Boolean('GP Deduction')
    sale_line_id = fields.Many2one('sale.order.line', 'Order Line')
    done_email_sent = fields.Boolean('Done Alert')
    kg_need_subcontractor = fields.Boolean('Need Third Party')
    kg_sub_contractor_id = fields.Many2one('res.partner', 'Sub Contractor')
    kg_hourly_rate = fields.Float(string="Hourly Rate")
    kg_time_from = fields.Datetime(string="From")
    kg_time_to = fields.Datetime(string="To")
    is_it_done = fields.Boolean(string="Completed")
    total_worked_hours = fields.Float(related='kg_effective_hours', string="Total Worked Hours")
    total_cost = fields.Float(compute='_get_compute_cost', string="Total Cost", store="True")
    date_required = fields.Boolean(compute=_get_material_status, store=True)
    kg_sector = fields.Selection([('managed_service', 'Managed Service'),
                                  ('elv_division', 'ELV Division'),
                                  ('it_product_sales', 'IT Product Sales'),
                                  ], string='Sector', default='managed_service')
    kg_servicecall_categories = fields.Selection([('new_installation', 'New Installation'),
                                                  ('amc', 'Annual Maintenance Contract(AMC)'),
                                                  ('rma', 'RMA - Faulty Product Service'),
                                                  ('poc', 'Proof Of Concept(POC)')],
                                                 store=True, default='new_installation', string='Service Type')
    proposed_service_charge = fields.Float(string="Proposed Service Charge")
    kg_type = fields.Selection([
        ('free', 'Free'),
        ('paid', 'Paid'),
    ], string='Cost Type', readonly=False, default='free')

    kg_type_of_service = fields.Selection([
        ('on_site', 'ON-Site'),
        ('remotely', 'Remotely'),
        ('over_the_phone', 'Over the Phone'),
        ('in_house', 'In House'),
    ], string='Support Type', readonly=False, )
    service_requested_date = fields.Date(string="Service Requested Date", default=fields.Datetime.now, )
    kg_salesman_id = fields.Many2one('res.users', string="Salesperson", default=lambda self: self.env.user)
    kg_state_name = fields.Char('Status', related='stage_id.name')
    kg_state = fields.Selection(selection=_STATES,
                                string='Status',
                                index=True,
                                track_visibility='onchange',
                                required=True,
                                copy=False,
                                default='draft')

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        values['ticket_number'] = self.env['ir.sequence'].next_by_code('request.number') or 'New'

        customer_id = values.get('partner_id', False)
        # res = super(Task, self).create(values)
        result = super(Task, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True,
                                               mail_notrack=False)).create(
            values)
        users = self.env['res.users'].browse(customer_id)
        if users:
            self.message_subscribe(users.ids)
        return result

    def write(self, vals):
        # result = super(Task, self).write(vals)
        result = super(Task, self).write(vals)
        customer_id = vals.get('partner_id')
        users = self.env['res.users'].browse(customer_id)
        if users:
            self.message_subscribe(users.ids)
        return result

    @api.onchange('user_id')
    def _onchange_user(self):
        if self.user_id:
            employee_obj = self.env['hr.employee'].search([('user_id', '=', self.user_id and self.user_id.id)])
            self.kg_hourly_rate = employee_obj.kg_hourly_rate or 0


class Followers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def create(self, vals):
        if 'res_model' in vals and 'res_id' in vals and 'partner_id' in vals:
            dups = self.env['mail.followers'].search([('res_model', '=', vals.get('res_model')),
                                                      ('res_id', '=', vals.get('res_id')),
                                                      ('partner_id', '=', vals.get('partner_id'))])
            if len(dups):
                for p in dups:
                    p.unlink()
        res = super(Followers, self).create(vals)
        return res


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    kg_servicecall_categories = fields.Selection([
        ('new_installation', 'New Installation'),
        ('amc', 'Annual Maintenance Contract(AMC)'),
        ('rma', 'RMA - Faulty Product Service'),
        ('poc', 'Proof Of Concept(POC)')],
        string='Service Type')


class AccountLine(models.Model):
    _inherit = 'account.analytic.line'
    _order = 'date'

    user_id = fields.Many2one('res.users', 'User')
    my_datetime = fields.Datetime(string='My datetime', compute='_get_datetime_from_date')
    date_from = fields.Datetime('From')
    date_to = fields.Datetime('To')
    kg_status = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')],
        string='Status')
    unit_amount = fields.Float('Duration', compute='_compute_duration', store=True)

    @api.depends('date_from', 'date_to')
    def _compute_duration(self):
        for data in self:
            # data.unit_amount = 0.0
            if data.date_from and data.date_to:
                start_date = fields.Datetime.from_string(data.date_from)
                end_date = fields.Datetime.from_string(data.date_to)
                dif_tot = relativedelta(end_date, start_date)
                dif_minut = dif_tot.hours * 60 + dif_tot.minutes
                diff1 = end_date - start_date
                total_minut = int(diff1.days) * 24 * 60 + dif_minut
                total_hr = (total_minut / 60) + (total_minut % 60) / float(100)
                t1 = datetime.strptime(str(data.date_from), '%Y-%m-%d %H:%M:%S')
                t2 = datetime.strptime(str(data.date_to), '%Y-%m-%d %H:%M:%S')
                t3 = t2 - t1
                data.unit_amount = total_hr
            else:
                data.unit_amount = 0.0
