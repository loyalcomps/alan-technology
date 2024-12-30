from typing import final

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError



class SaleOrder(models.Model):
    _inherit = "sale.order"

    state = fields.Selection(
        selection=[
            ('draft', "Quotation"),
            ('sent', "Quotation Sent"),
            ('approve', "Approved"),
            ('sale', "Sales Order"),
            ('done', "Locked"),
            ('cancel', "Cancelled"),
        ],
        string="Status",
        readonly=True,
        copy=False,
        index=True,
        tracking=3,
        default='draft'
    )
    is_sales_manager = fields.Boolean(
        string="Is Sales Manager",
        compute='_compute_is_sales_manager',
        store=False
    )
    show_approve = fields.Boolean(compute='_compute_is_sales_manager')

    payment_term_id = fields.Many2one('account.payment.term',string='Payment Terms', domain="[('state', '=', 'approve')]")
    customer_state = fields.Selection([
        ('inactive', 'Inactive'),
        ('final', 'Final'),
    ],compute='_compute_customer_status',string="Customer Status",store=True)

    cancelled_reason=fields.Text()

    @api.depends('partner_id', 'partner_id.customer_state')
    def _compute_customer_status(self):
        for i in  self:
            if i.partner_id.customer_state == 'active':
                i.customer_state = 'final'
            if i.partner_id.customer_state == 'inactive':
                i.customer_state = 'inactive'

    def action_custom_cancel(self):
        print("k")

    @api.depends()
    def _compute_is_sales_manager(self):
        """
        Computes if the current user is a Sales Manager and whether the approval button should be shown.
        """
        company = self.env.company
        today = fields.Date.today()

        # Get the Sales Manager group once
        sales_manager_group = self.env.ref('sale_customization.group_sales_manager', raise_if_not_found=False)

        for order in self:
            # Check if the user belongs to the Sales Manager group
            order.is_sales_manager = sales_manager_group and sales_manager_group in self.env.user.groups_id
            print("------------TODAYYYdate",today)

            print("------------------", order.date_order.date() + relativedelta(days=order.payment_term_id.min_days))

            # Check conditions to show approval
            order.show_approve = (
                    order.amount_total > company.max_order_amount or
                    (order.payment_term_id.min_days and
                     order.date_order and
                     today >=
                     order.date_order.date() + relativedelta(days=order.payment_term_id.min_days))
            )




    @api.constrains('amount_total')
    def _check_order_amount(self):
        company = self.env.company
        if self.amount_total > company.max_order_amount:
            raise UserError(
                f"The total amount of this sale order exceeds the configured limit of {company.max_order_amount}. Approval required.")


    def action_confirm(self):


        print("============================state",self.state)
        if self.state == 'approve':
            result = super(SaleOrder, self).action_confirm()
            print("state approve")

            for order_line in self.order_line:
                for picking in self.picking_ids:
                    for move in picking.move_ids_without_package:
                        if order_line.product_id == move.product_id:
                            move.description = order_line.name
            return result
        else:
            print("not approveeeeeeeeeeeeeeeeeeeeee")
            if self.show_approve:
                raise UserError("You cannot confirm the Sale Order unless the state is 'Approved'.")

            return  super(SaleOrder, self).action_confirm()


    def action_approve(self):
        self.state = 'approve'



class StockMove(models.Model):
    _inherit = "stock.move"

    description = fields.Char('Description')

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    description = fields.Char('Description')

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        self.ensure_one()
        if self.product_id:
            res.update({
                'description': self.name,
            })
        return res