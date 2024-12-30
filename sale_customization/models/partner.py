from odoo import models, fields, api
from datetime import timedelta, date
from odoo.exceptions import UserError


class SalespersonInactive(models.Model):
    _inherit = 'res.partner'
    customer_state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], default='active', string="Customer State")
    last_invoice_date = fields.Date(string='Last Invoice Date', compute="_compute_last_invoice_date")
    credit_limit = fields.Float(string="Credit Limit")
    is_sales_manager = fields.Boolean(
        string="Is Sales Manager",
        compute='_compute_is_sales_manager',
        store=False
    )
    property_payment_term_id = fields.Many2one('account.payment.term',string='Payment Terms', domain="[('state', '=', 'approve')]")
    @api.depends()
    def _compute_is_sales_manager(self):
        sales_manager_group = self.env.ref('sale_customization.group_sales_manager')
        for order in self:
            if sales_manager_group:
                order.is_sales_manager = sales_manager_group in self.env.user.groups_id
            else:
                order.is_sales_manager = False

    @api.depends('invoice_ids', 'child_ids.invoice_ids')
    def _compute_last_invoice_date(self):
        for record in self:
            all_invoices = self.env['account.move'].sudo().search([
                '|',
                ('partner_id', '=', record.id),
                ('partner_id', 'in', record.child_ids.ids)
            ])
            sorted_invoices = all_invoices.sorted(key=lambda r: r.invoice_date or fields.Date.to_date('1900-01-01'),
                                                  reverse=True)

            if sorted_invoices:
                record.last_invoice_date = sorted_invoices[0].invoice_date
            elif record.invoice_ids:
                sorted_invoices = record.invoice_ids.sorted(
                    key=lambda r: r.invoice_date or fields.Date.to_date('1900-01-01'), reverse=True)
                record.last_invoice_date = sorted_invoices[0].invoice_date
            else:
                record.last_invoice_date = False

    def set_customers_inactive(self):
        today = fields.Date.today()
        contacts = self.env['res.partner'].search([('last_invoice_date', '=', True)])
        if contacts:
            for contact in contacts:
                last_invoice_date = contact.last_invoice_date
                if last_invoice_date:
                   days_difference = (today - last_invoice_date).days
                   if days_difference >= 90:
                      contact.customer_state = 'inactive'
                   else:
                      contact.customer_state = 'active'
        else:
            print("No contacts found with a last_invoice_date.")
class ResCompany(models.Model):
    _inherit = 'res.company'

    max_order_amount = fields.Float(string="Maximum Order Amount")

class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    min_days= fields.Integer(string='Minimum Days Approval')
    max_days= fields.Integer(string='Maximmum Days Approval')
    state = fields.Selection([
        ('toapprove', 'To approve'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ], default='toapprove', string="Status")
    is_approval = fields.Boolean(
        string="Is approval",
        compute='_compute_is_directors',
        store=False
    )
    is_sales_manager = fields.Boolean(
        string="Is Sales Manager",
        compute='_compute_is_sales_manager',
        store=False
    )
    is_standard = fields.Boolean(string="Standard Payment Term")

    def action_approve(self):
        self.state='approve'

    def action_reject(self):
        self.state='reject'

    def action_draft(self):
        self.state='toapprove'

    @api.depends()
    def _compute_is_sales_manager(self):
        sales_manager_group = self.env.ref('sale_customization.group_sales_manager')
        for order in self:
            if sales_manager_group:
                order.is_sales_manager = sales_manager_group in self.env.user.groups_id
            else:
                order.is_sales_manager = False

    @api.depends()
    def _compute_is_directors(self):
        sales_manager_group = self.env.ref('sale_customization.group_directors')
        for order in self:
            if sales_manager_group:
                order.is_approval = sales_manager_group in self.env.user.groups_id
            else:
                order.is_approval = False




