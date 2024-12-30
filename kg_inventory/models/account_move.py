# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'
    kg_so_id = fields.Many2one('sale.order', string="Sale Order")

    kg_po_id = fields.Many2one('purchase.order', string="LPO")
    kg_do_id = fields.Many2one('stock.picking', string="DO.No")
    kg_inv_type = fields.Selection([
        ('proforma', 'Pro Forma Invoice'),
        ('original', 'Actual Invoice'),
    ], string='Invoice Type', default='original')

    def action_post(self):
        result = super(AccountMove, self).action_post()
        for invoice in self:
            performa_invoice_name = ''
            if invoice.kg_inv_type == 'proforma':
                raise UserError(_("you cannot validate a performa invoice"))

            if invoice.move_type == 'out_invoice':
                sale_order_id = invoice.kg_so_id and invoice.kg_so_id.id or False
                if sale_order_id:
                    delivery_order = self.env['stock.picking'].search(
                        [('state', '!=', 'cancel'), ('kg_sale_order_id', '=', sale_order_id),
                         ('kg_invoice_id', '!=', False)])

                    delivery_id = delivery_order and delivery_order[0].id or False
                    kg_actual_invoice_id = delivery_order and delivery_order[0].kg_actual_invoice_id and delivery_order[
                        0].kg_actual_invoice_id.id
                    if delivery_id and kg_actual_invoice_id:
                        delivery_obj = delivery_order[0]
                        performa_invoice_name = delivery_obj.kg_invoice_id.number[10:]
            if invoice.move_type in ('in_invoice', 'in_refund') and invoice.ref:
                if self.search([('move_type', '=', invoice.move_type), ('ref', '=', invoice.ref),
                                ('company_id', '=', invoice.company_id.id),
                                ('commercial_partner_id', '=', invoice.commercial_partner_id.id),
                                ('id', '!=', invoice.id)]):
                    raise UserError(
                        _("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/refund."))
            if performa_invoice_name:
                invoice.number = performa_invoice_name

                return self.write({'state': 'posted'})

    def kg_duplicate(self):

        move_lines = self.line_ids
        for line in move_lines:
            if line.kg_dup:
                account_id = line.account_id and line.account_id.id
                name = line.name
                date_maturity = line.date_maturity or False
                debit = line.debit
                credit = line.credit
                if line.debit > 0:
                    credit = line.debit
                    debit = 0
                if line.credit > 0:
                    debit = line.credit
                    credit = 0
                vals = {'account_id': account_id,
                        'name': name,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'credit': credit,
                        'debit': debit}

                self.env['account.move.line'].create(vals)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    kg_dup = fields.Boolean('Duplicate')
