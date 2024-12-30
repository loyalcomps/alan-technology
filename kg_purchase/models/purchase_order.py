# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from num2words import num2words

from odoo import models, fields, _, api
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # partner_signature = fields.Binary(string='Signature', help="Field for adding the signature of the Partner")
    # check_signature = fields.Boolean(compute='_compute_check_signature')
    kg_merge_line = fields.One2many('kg.merge.details', 'order_id', domain=[('merged', '=', True)],
                                    string="Merged From", readonly="1")
    kg_combined_line = fields.One2many('kg.merge.details', 'order_id', domain=[('merged', '=', False)],
                                       string="Merged To", readonly="1")
    kg_sale_order_id = fields.Many2many('sale.order', string='Sale Order')

    kg_po_order_type = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),

    ], string='Type', default='normal')


    payment_state = fields.Selection([

        ('partial_invoiced', 'Partial Invoice'),
        ('full_invoiced', 'Full Invoice'),

    ], string='Payment Status')



    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_id.vendor = True
        else:
            self.partner_id.vendor = False


    # @api.depends('partner_signature')
    # def _compute_check_signature(self):
    #     """In this function computes the value of the boolean field check signature
    #     which is used to hide/unhide the validate button in the current document"""
    #     if self.env['ir.config_parameter'].sudo().get_param('purchase.purchase_document_approve'):
    #
    #         if self.partner_signature:
    #
    #             self.check_signature = False
    #
    #         else:
    #             self.check_signature = True
    #     else:
    #         self.check_signature = False

    def amount_to_text(self, amount_total):
        amount_txt = num2words(amount_total)
        return amount_txt

    def action_merge_order(self):
        return {
            'res_model': 'purchase.order.group',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def do_merge(self, order_obj, ids):
        order_objects = order_obj.browse(ids)
        vendor_ids = []
        currency_ids = []
        types = []
        result = []
        partner_id = False
        currency_id = False
        date_order = False
        kg_po_order_type = 'normal'
        date_planned = False
        for order in order_objects:
            order_line = order.order_line
            partner_id = order.partner_id and order.partner_id.id
            currency_id = order.currency_id and order.currency_id.id
            date_order = order.date_order
            kg_po_order_type = order.kg_po_order_type
            date_planned = order.date_planned
            for line in order_line:
                tax_ids = []
                for tax in line.taxes_id:
                    tax_ids.append(tax.id)
                if line.order_id.state != 'draft':
                    raise UserError(
                        _('%s purchase quotation not in draft state.', line.order_id.name))
                vals = (0, 0, {
                    'product_id': line.product_id and line.product_id.id,
                    'name': line.name,
                    'price_unit': line.price_unit,
                    'product_qty': line.product_qty,
                    'date_planned': line.date_planned,
                    'product_uom': line.product_uom and line.product_uom.id,
                    'taxes_id': [(6, 0, tax_ids)],
                })
                result.append(vals)

        new_vals = {'order_line': result,
                    'partner_id': partner_id,
                    'currency_id': currency_id,
                    'date_order': date_order,
                    'kg_po_order_type': kg_po_order_type,
                    'date_planned': date_planned}
        purchase_order = self.env['purchase.order'].create(new_vals)
        new_id = purchase_order and purchase_order.id
        for order in order_objects:
            vendor_ids.append(order and order.partner_id and order.partner_id.id)
            currency_ids.append(order and order.currency_id and order.currency_id.id)
            types.append(order and order.kg_po_order_type)
            sale_order_id = order.kg_sale_order_id and order.kg_sale_order_id.id or False
            order.button_cancel()
            self.env['kg.merge.details'].create(
                {'purchase_order_id': new_id, 'order_id': order.id, 'merged': False})
            self.env['kg.merge.details'].create(
                {'purchase_order_id': order.id, 'order_id': new_id, 'merged': True, 'sale_order_id': sale_order_id})
        if len(list(set(vendor_ids))) > 1:
            raise UserError(
                _('Cannot merge, more than one vendor found'))
        if len(list(set(currency_ids))) > 1:
            raise UserError(
                _('Cannot merge,difference currency found'))
        if len(list(set(types))) > 1:
            raise UserError(
                _('Cannot merge,difference urgency found'))
        return new_id



class AccountMove(models.Model):
    _inherit = "account.move"


    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if self.invoice_origin and  len(self.invoice_origin)>0:
            purchase_order = self.env['purchase.order'].search([('name', '=', self.invoice_origin[0])])
            if purchase_order:
                total_qty_ordered = sum(purchase_order.order_line.mapped('product_qty'))
                total_qty_invoiced = sum(purchase_order.order_line.mapped('qty_invoiced'))
                if total_qty_ordered > total_qty_invoiced:
                    purchase_order.payment_state = 'partial_invoiced'
                else:
                    purchase_order.payment_state = 'full_invoiced'





class KGMergeDetails(models.Model):
    _name = 'kg.merge.details'
    sale_order_id = fields.Many2one('sale.order', 'SO')
    purchase_order_id = fields.Many2one('purchase.order', 'PO')
    order_id = fields.Many2one('purchase.order', 'Current Order')
    merged = fields.Boolean('Merged')
