
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang


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

    @api.depends()
    def _compute_is_sales_manager(self):
        sales_manager_group = self.env.ref('sale_customization.group_sales_manager')
        for order in self:
            if sales_manager_group:
                order.is_sales_manager = sales_manager_group in self.env.user.groups_id
            else:
                order.is_sales_manager = False

    @api.constrains('amount_total')
    def _check_order_amount(self):
        company = self.env.company
        if self.amount_total > company.max_order_amount:
            raise UserError(
                f"The total amount of this sale order exceeds the configured limit of {company.max_order_amount}. Approval required.")

    def action_confirm(self):
        if self.state == 'approve':
            result = super(SaleOrder, self).action_confirm()
            for order_line in self.order_line:
                for picking in self.picking_ids:
                    for move in picking.move_ids_without_package:
                        if order_line.product_id == move.product_id:
                            move.description = order_line.name
            return result
        else:
            raise UserError("You cannot confirm the Sale Order unless the state is 'Approved'.")
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