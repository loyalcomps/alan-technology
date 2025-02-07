from odoo import models, fields, api
from datetime import timedelta, date
from odoo.exceptions import UserError


class SalespersonInactive(models.Model):
    _inherit = 'res.partner'
    customer_state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], default='inactive', string="Customer State")
    last_invoice_date = fields.Date(string='Last Invoice Date', compute="_compute_last_invoice_date")
    credit_limit = fields.Float(string="Credit Limit")
    is_sales_manager = fields.Boolean(
        string="Is Sales Manager",
        compute='_compute_is_sales_manager',
        store=False
    )
    property_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',
                                               domain="[('state', '=', 'approve')]")

    @api.depends()
    def _compute_is_sales_manager(self):
        """Computes whether the current user is a sales manager.

        This method checks if the current user belongs to the 'Sales Manager' group
        defined in the `sale_customization.group_sales_manager`. It updates the
        `is_sales_manager` field for each sale order based on whether the user is
        part of the sales manager group.

        Fields Updated:
            - `is_sales_manager`: A boolean field indicating if the user is a sales manager.
        """
        sales_manager_group = self.env.ref('sale_customization.group_sales_manager')
        for order in self:
            if sales_manager_group:
                order.is_sales_manager = sales_manager_group in self.env.user.groups_id
            else:
                order.is_sales_manager = False

    @api.depends('invoice_ids', 'child_ids.invoice_ids')
    def _compute_last_invoice_date(self):
        """Computes the last invoice date for the partner and its children.

        This method calculates the most recent invoice date for the partner by
        considering both the invoices directly linked to the partner (`invoice_ids`)
        and the invoices of its child partners (`child_ids.invoice_ids`). The result
        is stored in the `last_invoice_date` field.

        The invoices are sorted by their invoice date, and the most recent one is
        selected. If no invoices are found, the field is set to `False`.

        Fields Updated:
            - `last_invoice_date`: The date of the most recent invoice for the partner
              or its child partners.
        """
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
        """Sets customers to inactive based on the last invoice date and company configuration.

        This method checks all contacts (customers) in the system who have a `last_invoice_date` set.
        It compares the difference between the current date and their last invoice date against the
        `max_inactive_days` configuration from the company settings. If the contact has not been invoiced
        within the allowed number of days, their status is set to 'inactive', and their user account is
        disassociated. Contacts who have a recent invoice within the allowed time remain marked as 'active'.

        If no contacts are found with a `last_invoice_date`, the method will set the `customer_state`
        of the calling object (`self`) to 'inactive'.

        Fields Updated:
            - `customer_state`: Set to 'inactive' or 'active' based on the invoice date comparison.
            - `user_id`: Set to `None` for inactive customers to disassociate them from users.

        Returns:
            None
        """
        today = fields.Date.today()
        contacts = self.env['res.partner'].search([('last_invoice_date', '=', True)])
        company = self.env.company
        if company.max_inactive_days:
            if contacts:
                for contact in contacts:
                    last_invoice_date = contact.last_invoice_date
                    if last_invoice_date:
                        days_difference = (today - last_invoice_date).days
                        if days_difference <= company.max_inactive_days:
                            contact.customer_state = 'active'
                        else:
                            contact.sudo().write({
                                'customer_state': 'inactive',
                                'user_id': None
                            })

            else:
                for j in self:
                    j.customer_state = 'inactive'


class ResCompany(models.Model):
    _inherit = 'res.company'

    max_order_amount = fields.Float(string="Maximum Order Amount")
    max_inactive_days = fields.Integer(string='Maximum Inactive Days')


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    min_days = fields.Integer(string='Minimum Days Approval')
    max_days = fields.Integer(string='Maximmum Days Approval')
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
        """Sets the state of the record to 'approve'.

        This method updates the state of the record to 'approve', indicating that the
        record has been approved.

        Returns:
            None
        """
        self.state = 'approve'

    def action_reject(self):
        """Sets the state of the record to 'reject'.

        This method updates the state of the record to 'reject', indicating that the
        record has been rejected.

        Returns:
            None
        """
        self.state = 'reject'

    def action_draft(self):
        """Sets the state of the record to 'toapprove'.

        This method updates the state of the record to 'toapprove', indicating that
        the record is in a draft state and awaiting approval.

        Returns:
            None
        """
        self.state = 'toapprove'

    @api.depends()
    def _compute_is_sales_manager(self):
        """Computes whether the current user is a sales manager.

        This method checks if the current user belongs to the 'Sales Manager' group
        defined in the `sale_customization.group_sales_manager`. It updates the
        `is_sales_manager` field for each sale order based on whether the user is
        part of the sales manager group.

        Fields Updated:
            - `is_sales_manager`: A boolean field indicating if the user is a sales manager.

        Returns:
            None
        """
        sales_manager_group = self.env.ref('sale_customization.group_sales_manager')
        for order in self:
            if sales_manager_group:
                order.is_sales_manager = sales_manager_group in self.env.user.groups_id
            else:
                order.is_sales_manager = False

    @api.depends()
    def _compute_is_directors(self):
        """Computes whether the current user is a director.

        This method checks if the current user belongs to the 'Directors' group
        defined in the `sale_customization.group_directors`. It updates the
        `is_approval` field for each order based on whether the user is part of
        the directors group.

        Fields Updated:
            - `is_approval`: A boolean field indicating if the user is a director.

        Returns:
            None
        """
        sales_manager_group = self.env.ref('sale_customization.group_directors')
        for order in self:
            if sales_manager_group:
                order.is_approval = sales_manager_group in self.env.user.groups_id
            else:
                order.is_approval = False
