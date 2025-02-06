# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons.sale.models.sale_order import LOCKED_FIELD_STATES
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang


class Picking(models.Model):
    _inherit = "stock.picking"


    kg_sale_order_type = fields.Selection(related='sale_id.kg_sale_order_type')

    client_order_do_ref = fields.Char(string='Customer Reference')
    invoice_count = fields.Integer(string="Invoice Count", compute='_compute_invoice_count')

    def _compute_invoice_count(self):
        """Computes the number of invoices associated with the picking.

        This method calculates the number of invoices that are linked to a specific
        picking based on the picking's name, which is used as the `invoice_origin`.
        The result is stored in the `invoice_count` field of the picking.

        The method checks if there are any invoices matching the `invoice_origin`
        and updates the `invoice_count` accordingly.

        Fields Updated:
            - `invoice_count`: The count of invoices related to the picking.
        """

        for picking_id in self:
            move_ids = picking_id.env['account.move'].search([('invoice_origin', '=', picking_id.name)])
            if move_ids:
                self.invoice_count = len(move_ids)
            else:
                self.invoice_count = 0

    def action_view_invoice(self):
        """Returns an action to view the invoices related to the picking.

        This method opens a window displaying a list of invoices (in `tree` and `form`
        views) related to the current picking based on the `invoice_origin`. The
        action prevents creation of new invoices and targets the current window.

        Returns:
            dict: An action dictionary to open the invoice list view filtered by the
                  picking's name in the `invoice_origin`.
        """
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('invoice_origin', '=', self.name)],
            'context': {'create': False},
            'target': 'current'
        }

    def create_invoice_from_delivery(self):
        """Creates an invoice from the delivery (picking) for outgoing shipments.

        This method generates an invoice from a delivery (picking) of type 'outgoing'.
        It creates invoice lines based on the products and quantities in the picking,
        calculates the appropriate account and tax information, and associates the
        invoice with the sale order. The invoice is then created and linked to the
        picking and sale order.

        The method also updates the sale order's invoice status depending on the 
        delivery quantity and the total sale order quantity, and links the 
        `kg_po_ref` (purchase order reference) if available to the invoice.

        Process:
        1. It checks if the picking is of type 'outgoing'.
        2. Loops through the move lines of the picking and creates the corresponding 
        invoice lines.
        3. Creates an invoice based on the picking details.
        4. Updates the sale order's invoice status based on the invoiced and delivered quantities.
        5. Links the generated invoice to the picking and updates relevant references.

        Returns:
            account.move: The created invoice record.
        """
        for picking_id in self:
            current_user = self.env.uid
            if picking_id.picking_type_id.code == 'outgoing':
                invoice_line_list = []
                for move_ids_without_package in picking_id.move_ids_without_package:
                    sale_line = move_ids_without_package.sale_line_id

                    vals = (0, 0, {
                        'name': move_ids_without_package.description_picking,
                        'product_id': move_ids_without_package.product_id.id,
                        'price_unit': move_ids_without_package.sale_line_id.price_unit,

                        'account_id': move_ids_without_package.product_id.property_account_income_id.id if move_ids_without_package.product_id.property_account_income_id
                        else move_ids_without_package.product_id.categ_id.property_account_income_categ_id.id,

                        'tax_ids': move_ids_without_package.sale_line_id.tax_id.ids,
                        'quantity': move_ids_without_package.quantity_done,
                        'description': move_ids_without_package.description,
                        'sale_line_ids': [(6, 0, [sale_line.id])]

                    })
                    invoice_line_list.append(vals)
                invoice = picking_id.env['account.move'].create({
                    'move_type': 'out_invoice',
                    'invoice_origin': picking_id.name,
                    'invoice_user_id': current_user,
                    'narration': picking_id.name,
                    'partner_id': picking_id.partner_id.id,
                    'currency_id': picking_id.env.user.company_id.currency_id.id,
                    'kg_so_id': picking_id.kg_sale_order_id.id,
                    'kg_bank_id': self.sale_id.bank_id.id,
                    'payment_reference': picking_id.name,
                    'picking_id': picking_id.id,
                    'invoice_line_ids': invoice_line_list
                })
                picking_id.update({'kg_invoice_id': invoice.id})
                so = picking_id.kg_sale_order_id
                so.update({'invoice_ids': [(4, invoice.id)]})
                picking_id.kg_invoice_status='original'
                delivery_qty = sum(self.sale_id.picking_ids.filtered(lambda p: p.state == 'done').mapped(
                    'move_line_ids_without_package').mapped('qty_done'))
                sale_qty = sum(self.sale_id.order_line.mapped('product_uom_qty'))
                if sale_qty == delivery_qty:
                    self.sale_id.kg_invoice_status_1 = 'invoiced'
                else:
                    self.sale_id.kg_invoice_status_1 = 'invoice_p'
                if self.kg_po_ref:
                    self.kg_invoice_id.kg_another_ref = self.kg_po_ref
                return invoice
