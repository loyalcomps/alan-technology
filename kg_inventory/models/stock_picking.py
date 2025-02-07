# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang


class Quant(models.Model):
    _inherit = "stock.quant"

    kg_total_cost = fields.Float(string="Total Cost")

    @api.model
    def create(self, vals):
        if vals.get('qty') and vals.get('cost'):
            vals['kg_total_cost'] = vals.get('cost') * vals.get('qty')

        result = super(Quant, self).create(vals)
        return result


class StockPicking(models.Model):
    _inherit = "stock.picking"

    priority = fields.Selection([
        ('0', 'Not urgent'),
        ('1', 'Normal'),
        ('2', 'Urgent'),
        ('3', 'Very Urgent')
    ], default='0', index=True)
    kg_po_ref = fields.Char(string='PO Reference')

    def do_new_transfer(self):

        result = super(StockPicking, self).do_new_transfer()

        return result

    kg_sale_order_id = fields.Many2one('sale.order', string="Sale Order")

    kg_invoice_status = fields.Selection([
        ('no_invoice', 'Invoice Not Created'),
        ('proforma_invoice', 'Proforma Invoice Created'),
        ('original', 'Actual Invoice Created'),
    ], string='Invoice Status', default='no_invoice')

    kg_type = fields.Selection([
        ('sale', 'Delivery'),
        ('purchase', 'Receipt'),
        ('internal', 'Internal Transfer'),
    ], string='Type of Operation', default='internal')

    kg_invoice_id = fields.Many2one('account.move', string="Pro-forma Invoice")
    kg_actual_invoice_id = fields.Many2one('account.move', string="Actual Invoice")
    related_so = fields.Char(string='Related SO', compute='_compute_proforma_seq')

    def _compute_proforma_seq(self):
        self.related_so = False
        if self.sale_id:
            self.related_so = self.sale_id.pro_seq

    @api.model
    def create(self, vals):
        if vals.get('origin'):
            sale_obj = self.env['sale.order'].search([('name', '=', vals.get('origin'))])
            vals['kg_sale_order_id'] = sale_obj and sale_obj.id or False

        if vals.get('picking_type_id'):
            picking_type_obj = self.env['stock.picking.type'].browse(vals.get('picking_type_id'))
            code = picking_type_obj.code
            if code == 'internal':
                vals['kg_type'] = 'internal'

            if code == 'outgoing':
                vals['kg_type'] = 'sale'
            if code == 'incoming':
                vals['kg_type'] = 'purchase'
        result = super(StockPicking, self).create(vals)
        return result

    def create_invoice_from_delivery(self):
        if self.kg_actual_invoice_id and self.kg_actual_invoice_id.id:
            raise UserError(_('already actual invoice created'))
        if self.kg_type != 'sale':
            raise UserError(_('this option only for delivery orders'))
        sale_order_obj = self.kg_sale_order_id
        # result = sale_order_obj.create_invoice()

        if self.kg_invoice_status == 'proforma_invoice':
            if not (self.kg_invoice_id and self.kg_invoice_id.id):
                raise UserError(
                    _('Performa Invoice Link not found,please check,it may lead to invoice number mismatch'))

        self.kg_invoice_status = 'original'

        # sale_order_obj.kg_invoice_status = 'original'
        if self.kg_invoice_id and self.kg_invoice_id.id:
            self.kg_actual_invoice_id.action_invoice_open()
            self.kg_actual_invoice_id.kg_do_id = self.id

        return True

    def create_dummy_invoice(self):
        if self.kg_actual_invoice_id and self.kg_actual_invoice_id.id:
            raise UserError(_('already actual invoice created'))

        if self.kg_type != 'sale':
            raise UserError(_('this option only for delivery orders'))
        if self.state in 'done':
            raise UserError(_('you cannot create proforma invoice in this stage'))
        if self.kg_invoice_id and self.kg_invoice_id.id and self.kg_invoice_status == 'proforma_invoice':
            raise UserError(_('already proforma invoice created'))

        sale_order_obj = self.kg_sale_order_id
        sale_order_obj.kg_invoice_status_1 = 'proforma_invoice'
        partner_invoice_id = sale_order_obj.partner_invoice_id and sale_order_obj.partner_invoice_id.id
        partner_shipping_id = sale_order_obj.partner_shipping_id and sale_order_obj.partner_shipping_id.id
        currency_id = sale_order_obj.currency_id and sale_order_obj.currency_id.id
        user_id = sale_order_obj.user_id and sale_order_obj.user_id.id
        payment_term_id = sale_order_obj.payment_term_id and sale_order_obj.payment_term_id.id
        team_id = sale_order_obj.team_id and sale_order_obj.team_id.id
        client_order_ref = sale_order_obj.client_order_ref

        lines = sale_order_obj.order_line
        kg_warranty_id = sale_order_obj.kg_warranty_id and sale_order_obj.kg_warranty_id.id
        kg_validity_id = sale_order_obj.kg_validity_id and sale_order_obj.kg_validity_id.id
        kg_lpo_term_id = sale_order_obj.kg_lpo_term_id and sale_order_obj.kg_lpo_term_id.id
        kg_delivery_id = sale_order_obj.kg_delivery_id and sale_order_obj.kg_delivery_id.id
        kg_so_id = self.kg_sale_order_id and self.kg_sale_order_id.id or False
        receivable_account_id = sale_order_obj.partner_id and sale_order_obj.partner_id.property_account_receivable_id and sale_order_obj.partner_id.property_account_receivable_id.id

        if not receivable_account_id:
            raise UserError(_('Please define receivable account in customer master'))
        invoice_lines = []
        for line in lines:
            account_id = line.product_id and line.product_id.categ_id and line.product_id.categ_id.property_account_income_categ_id and line.product_id.categ_id.property_account_income_categ_id.id
            tax_ids = []
            for tax in line.tax_id:
                tax_ids.append(tax.id)
            if not account_id:
                raise UserError(_('please define income account in product category.'))
            vals = (0, 0, {'product_id': line.product_id and line.product_id.id,
                           'name': line.name,
                           'product_uom_id': line.product_uom and line.product_uom.id,
                           'quantity': line.product_uom_qty,
                           'price_unit': line.price_unit,
                           'discount': line.discount,
                           'tax_ids': [(6, 0, tax_ids)]
                           })
            invoice_lines.append(vals)
        invoice_vals = {'partner_id': partner_invoice_id,
                        'partner_shipping_id': partner_shipping_id,
                        'currency_id': currency_id,
                        'user_id': user_id,
                        'invoice_payment_term_id': payment_term_id,
                        'team_id': team_id,
                        'kg_so_id': kg_so_id,
                        'kg_do_id': self.id,
                        'move_type': 'out_invoice',
                        'invoice_line_ids': invoice_lines,
                        'name': client_order_ref,
                        }
        inv_obj = self.env['account.move'].create(invoice_vals)
        inv_obj.action_post()
        self.kg_invoice_id = inv_obj and inv_obj.id
        name = inv_obj.name
        inv_obj.button_cancel()
        inv_obj.name = name

        inv_obj.kg_inv_type = 'proforma'

        self.kg_invoice_status = 'proforma_invoice'

        return True
