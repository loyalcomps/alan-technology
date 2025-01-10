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
    is_sales_manager = fields.Boolean(
        string="Is Sales Manager",
        compute='_compute_is_sales_manager',
        store=False
    )
    show_approve = fields.Boolean(compute='_compute_is_sales_manager')
    approval_description=fields.Text(compute='_compute_is_sales_manager')
    first_confirm = fields.Boolean(default=False,store=True)

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
        for i in self:
            purchase_orders = self.env['purchase.order'].search([('kg_sale_order_id', 'in', i.ids),('state','in',['purchase','done'])])
            if purchase_orders:
                raise UserError("You cannot cancel sale order.")
            else:
                return {
                    'name': _('Cancel'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.cancel.custom',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_sale_id': self.id,
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
            order.approval_description=''
            # Check if the user belongs to the Sales Manager group
            order.is_sales_manager = sales_manager_group and sales_manager_group in self.env.user.groups_id


            # Check conditions to show approval
            order.show_approve = (
                    order.amount_total > company.max_order_amount or
                    (order.payment_term_id.min_days and
                     order.date_order and
                     today >=
                     order.date_order.date() + relativedelta(days=order.payment_term_id.min_days))
            )

            if (order.amount_total > company.max_order_amount and
                    (order.payment_term_id.min_days and
                     order.date_order and
                     today >=
                     order.date_order.date() + relativedelta(days=order.payment_term_id.min_days))):
                order.approval_description= ' Order Amount Exceeded and Minimum Days for Payment Exceeded !!!!!!'
            elif order.amount_total > company.max_order_amount:
                order.approval_description = 'Order Amount Exceeded !!!!!!'
            elif (order.payment_term_id.min_days and
                     order.date_order and
                     today >=
                     order.date_order.date() + relativedelta(days=order.payment_term_id.min_days)):
                order.approval_description = ' Minimum Days for Payment Exceeded !!!!!!'
            else:
                order.approval_description = ''





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
        self.state = 'approve'


class StockMove(models.Model):
    _inherit = "stock.move"

    description = fields.Char('Description',store=True)
class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    description = fields.Char('Description',store=True,related='move_id.description')


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    description = fields.Char('Description',store=True)


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