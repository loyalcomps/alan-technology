from typing import final
import threading

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
import logging

_logger = logging.getLogger(__name__)
from collections import defaultdict


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
    is_manager_approval = fields.Boolean(
        string="Sales Manager Approval",
        compute='_compute_is_sales_manager',
        store=False
    )
    is_director_approval = fields.Boolean(
        string="Sales Director Approval",
        compute='_compute_is_sales_manager',
        store=False
    )

    is_sales_manager = fields.Boolean(
        string="Is Sales Manager",
        compute='_compute_is_sales_manager',
        store=False
    )
    show_approve = fields.Boolean(compute='_compute_is_sales_manager')
    approval_description = fields.Text(compute='_compute_is_sales_manager')
    director_description = fields.Text(compute='_compute_is_sales_manager')
    manager_description = fields.Text(compute='_compute_is_sales_manager')
    first_confirm = fields.Boolean(default=False, store=True)

    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',
                                      domain="[('state', '=', 'approve')]")
    customer_state = fields.Selection([
        ('inactive', 'Inactive'),
        ('final', 'Final'),
    ], compute='_compute_customer_status', string="Customer Status", store=True)

    cancelled_reason = fields.Text()
    custom_status = fields.Selection([
        ('quotation', 'Quotation'),
        ('sale', 'Sale Order'),
        ('partial_purchase', 'Partially PO Created'),
        ('po_created', 'PO Created'),
        ('po_confirm', 'PO Confirm'),
    ], compute='_compute_custom_status', string="Custom Status")
    is_approve_visible = fields.Boolean(string='Visible Approve', compute='_compute_is_approve_visible', default=False,
                                       )
    @api.depends('state', 'first_confirm')
    def _compute_is_approve_visible(self):
        for order in self:
            is_manager_approval = self.env.user.has_group('sale_customization.group_sales_manager')
            is_director_approval = self.env.user.has_group('sale_customization.group_directors')
            if (is_director_approval or is_manager_approval) and order.first_confirm and order.state in ['draft','sent']:
                order.is_approve_visible = True
            else:
                order.is_approve_visible = False

    @api.depends('state')
    def _compute_custom_status(self):
        for order in self:
            order.custom_status = 'quotation'
            try:
                purchase_orders = self.env['purchase.order'].search([('kg_sale_order_id', 'in', order.ids)])
                if not purchase_orders:
                    if order.state == 'draft':
                        order.custom_status = 'quotation'
                    elif order.state == 'sale':
                        order.custom_status = 'sale'
                else:
                    for line in order.order_line:
                        sale_product_id = line.product_id
                        sale_qty = line.product_uom_qty
                        for purchase in purchase_orders:
                            for record in purchase.order_line:
                                purchase_product_id = record.product_id
                                purchase_qty = record.product_qty
                                if sale_product_id == purchase_product_id:
                                    if sale_qty == purchase_qty:
                                        if purchase.state == 'draft':
                                            order.custom_status = 'po_created'
                                        elif purchase.state == 'purchase':
                                            order.custom_status = 'po_confirm'
                                    else:
                                        order.custom_status = 'partial_purchase'
            except Exception as e:
                _logger.error("Error computing custom_status for sale.order ID: %s. Error: %s", order.id, str(e))

    @api.depends('partner_id', 'partner_id.customer_state')
    def _compute_customer_status(self):
        for i in self:
            if i.partner_id.customer_state == 'active':
                i.customer_state = 'final'
            if i.partner_id.customer_state == 'inactive':
                i.customer_state = 'inactive'

    def action_custom_cancel(self):
        is_manager = self.env.user.has_group('sale_customization.group_sales_manager')
        is_director = self.env.user.has_group('sale_customization.group_directors')
        for order in self:
            purchase_orders = self.env['purchase.order'].search(
                [('kg_sale_order_id', 'in', i.ids), ('state', 'in', ['purchase', 'done'])])
            if purchase_orders and not is_manager and not is_director:
                raise UserError("You cannot cancel sale order.")
            else:
                return {
                    'name': _('Cancel'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.cancel.custom',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_sale_id': order.id,
                    },
                }

            # if not purchase_orders:
            #     self.state = 'cancel'
            # for j in purchase_orders:
            #     if j.state in ['purchase', 'done','cancel']:

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
            order.show_approve = min_days = max_days = show_manager_alert = show_director_alert = is_manager_approval = is_director_approval = False
            if order.payment_term_id:
                if order.payment_term_id.min_days:
                    min_days = order.payment_term_id.min_days
                if order.payment_term_id.max_days:
                    max_days = order.payment_term_id.max_days

            # Check conditions to show approval
            # order.show_approve = (
            #         order.amount_total > company.max_order_amount or
            #         (order.payment_term_id.min_days and
            #          order.date_order and
            #          today >=
            #          order.date_order.date() + relativedelta(days=order.payment_term_id.min_days))
            # )

            if order.amount_total > company.max_order_amount:
                order.show_approve = True
            invoice_recs = self.env['account.move'].search(
                [('partner_id', '=', order.partner_id.id), ('state', '=', 'posted'), ('payment_state', '!=', 'paid')])

            if invoice_recs:
                for rec in invoice_recs:
                    invoice_date = rec.invoice_date
                    required_approval = False
                    if rec.invoice_payment_term_id:
                        if rec.invoice_payment_term_id.min_days != 0:
                            min_days = rec.invoice_payment_term_id.min_days
                        if rec.invoice_payment_term_id.max_days != 0:
                            max_days = rec.invoice_payment_term_id.max_days
                        if rec.invoice_payment_term_id.max_days != 0 and rec.invoice_payment_term_id.min_days != 0 and today >= invoice_date + relativedelta(
                                days=min_days) and today <= invoice_date + relativedelta(days=max_days):
                            show_manager_alert = True
                            order.show_approve = True
                            required_approval = True
                        elif rec.invoice_payment_term_id.max_days != 0 and rec.invoice_payment_term_id.min_days != 0 and today > invoice_date + relativedelta(
                                days=max_days):
                            show_director_alert = True
                            order.show_approve = True
                            required_approval = True
                        if required_approval:
                            break

            approval_description = ''
            manager_description = ''
            director_description = ''

            if order.amount_total > company.max_order_amount:
                approval_description = 'Congratulations for your order, having above AED ' + str(
                    company.max_order_amount) + ' value, you may request an Approval from Sales Director.'
                director_description = 'Sale order <b>  ' + str(order.name) + '</b> - is having above AED ' + str(
                    company.max_order_amount) + ' value .'
                is_director_approval = True
            if show_director_alert:
                approval_description = approval_description + ' Previous Payments overdue by ' + str(
                    max_days) + ' days for this customer, Approval required from Sales Director !!'
                director_description = director_description + '   Previous Payments overdue by ' + str(
                    max_days) + ' days for the customer <b> ' + str(order.partner_id.name) + '</b>. .'
            if show_manager_alert:
                approval_description = approval_description + ' Previous Payments overdue by ' + str(
                    min_days) + ' days for the customer, Approval required from Sales Manager !!'
                manager_description = manager_description + '   Previous Payments overdue by ' + str(
                    min_days) + ' days for the customer <b>' + str(order.partner_id.name) + ' </b>.'

                is_manager_approval = True
            if (show_manager_alert and show_director_alert) or show_director_alert:
                is_director_approval = True
                is_manager_approval = False

            order.is_manager_approval = is_manager_approval
            order.is_director_approval = is_director_approval
            order.approval_description = approval_description
            order.manager_description = manager_description + '<br> Please Approve the Sale Order -<b> ' + str(
                order.name) + '!! </b>.'
            order.director_description = director_description + '<br> Please Approve the Sale Order - <b>' + str(
                order.name) + '!! </b>.'

    # @api.constrains('amount_total')
    # def _check_order_amount(self):
    #     company = self.env.company
    #     if self.amount_total > company.max_order_amount:
    #         raise UserError(
    #             f"The total amount of this sale order exceeds the configured limit of {company.max_order_amount}. Approval required.")

    # def update_first_confirm(self):
    #     self.env.cr.execute("""
    #                        UPDATE sale_order
    #                        SET first_confirm = TRUE
    #                        WHERE id = %s
    #                    """, (self.id,))
    def action_confirm(self):
        """Confirm sale order and update move descriptions from order lines.

        Returns:
            Result from super call after confirming sale order

        Raises:
            UserError: If order requires approval but hasn't been approved yet
        """
        # self.sudo().update_first_confirm()

        if self.show_approve and self.state not in ['approve']:
            return {
                'name': _('Approval Required'),
                'type': 'ir.actions.act_window',
                'res_model': 'sale.cancel.custom',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_sale_id': self.id,
                    'default_check_approve': True,
                    'default_description': self.approval_description,

                },
            }

        if self.state not in ['draft', 'approve', 'sent']:
            return super(SaleOrder, self).action_confirm()

        result = super(SaleOrder, self).action_confirm()

        # Create mapping of product_id to order line name for efficient lookup
        product_descriptions = {
            line.product_id: line.name
            for line in self.order_line
        }

        # Update move descriptions in a single pass
        for picking in self.picking_ids:
            for move in picking.move_ids_without_package:
                if move.product_id in product_descriptions:
                    move.description = product_descriptions[move.product_id]
            for move in picking.move_line_ids_without_package:

                if move.product_id in product_descriptions:
                    move.description = product_descriptions[move.product_id]

        return result

    def action_approve(self):
        for order in self:
            is_manager_approval = self.env.user.has_group('sale_customization.group_sales_manager')
            is_director_approval = self.env.user.has_group('sale_customization.group_directors')
            if order.is_manager_approval and not is_manager_approval:
                raise AccessError("You are not authorized to approve this order.")
            if order.is_director_approval and not is_director_approval:
                raise AccessError("You are not authorized to approve this order.")
            order.state = 'approve'


class StockMove(models.Model):
    _inherit = "stock.move"

    description = fields.Char('Description', store=True)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    description = fields.Char('Description', store=True, related='move_id.description')


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    description = fields.Char('Description', store=True)


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


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        result = super(PurchaseOrder, self).button_confirm()
        product_descriptions = {
            line.product_id: line.name
            for line in self.order_line
        }
        for picking in self.picking_ids:
            for move in picking.move_ids_without_package:
                if move.product_id in product_descriptions:
                    move.description = product_descriptions[move.product_id]
        return result
