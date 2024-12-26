
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


    def action_confirm(self):
        if self.state == 'approve':
            return super(SaleOrder, self).action_confirm()
        else:
            raise UserError("You cannot confirm the Sale Order unless the state is 'Approved'.")
    def action_approve(self):
        self.state = 'approve'