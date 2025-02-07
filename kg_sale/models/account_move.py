# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
import logging

_logger = logging.getLogger(__name__)



class AccountInvoice(models.Model):
    _inherit = 'account.move'

    picking_id = fields.Many2one('stock.picking', string='Picking')
    kg_sale_order_id = fields.Many2one('sale.order',string='Sale Order')
    kg_bank_id = fields.Many2one('res.bank', string='Bank')




    @api.depends('invoice_line_ids')
    def _compute_kg_net_discount(self):
        """Computes the total discount applied to the invoice lines.

        This method calculates the total discount across all invoice lines by
        checking the `discount` field on each line and applying it to the
        `quantity` and `price_unit` fields. The discount for each line is
        computed as `(discount / 100) * (quantity * price_unit)` and added to
        the total discount. The final result is stored in the `kg_net_discount` field.

        Fields Updated:
            - `kg_net_discount`: The total discount value across all invoice lines.

        Returns:
            None
        """
        for inv in self:
            lines = inv.invoice_line_ids
            total_discount = 0
            for line in lines:

                if line.discount > 0:
                    qty = line.quantity
                    price_unit = line.price_unit
                    discount = float(float(line.discount) / float(100)) * (float(qty * price_unit))
                    total_discount = total_discount + discount
            self.kg_net_discount = total_discount

    kg_discount_per = fields.Float(string='Discount(%)')
    kg_discount = fields.Float(string='Discount')
    kg_discount_acc_id = fields.Many2one('account.account', 'Discount Account')
    number = fields.Char( store=True, copy=False)
    kg_terms_condition_line = fields.One2many('kg.invoice.terms.line', 'invoice_id', string="Terms Line")

    kg_warranty_id = fields.Many2one('kg.warranty', string="Warranty")
    kg_validity_id = fields.Many2one('kg.validity', string="Validity")
    kg_lpo_term_id = fields.Many2one('kg.lpo.terms', string="LPO")
    kg_delivery_id = fields.Many2one('kg.delivery', string="Delivery")

    kg_skip_shipaddress = fields.Boolean(string='Skip Shipping Address', default=True)
    kg_trans_exp_acc_id = fields.Many2one('account.account', 'Transportation Expense Account')
    kg_trans_pro_acc_id = fields.Many2one('account.account', 'Transportation Provision Account')
    kg_net_discount = fields.Float(compute='_compute_kg_net_discount', string="Discount", store="True")
    kg_another_ref = fields.Char(string='P.Ref')
    kg_amount_words = fields.Char(string="Amount(words)")
    kg_department_id = fields.Many2one('hr.department', string="Department")


    @api.constrains('number')
    def _check_constriant(self):
        """Checks for duplicate invoice numbers before saving the record.

        This method is triggered when the `number` field is modified or validated.
        It searches for existing invoices (`account.invoice`) that have the same
        `number`. If more than one invoice with the same number is found, a
        `UserError` is raised, preventing duplicate invoice numbers.

        Raises:
            UserError: If there is more than one invoice with the same number.

        Returns:
            None
        """
        number = self.number
        if number:
            invoice = self.env['account.invoice'].search([('number', '=', number)])
            _logger.info("Found invoices with the number %s: %s", number, invoice)
            nos = len(invoice)
            if nos > 1:
                raise UserError(_('invoice number is duplicated'))



    def finalize_invoice_move_lines(self, move_lines):
        """Finalizes the invoice move lines and checks for any remaining discounts.

        This method is called to finalize the move lines for an invoice. It first
        calls the parent method to perform the standard finalization process. Then,
        it checks if any discount fields (`kg_discount_per` or `kg_discount`) have
        non-zero values. If any of these discount fields are set, it raises a
        `UserError` to prevent further processing, requiring the user to adjust the
        discount in the invoice lines.

        Args:
            move_lines (recordset): The move lines associated with the invoice.

        Returns:
            recordset: The result of the parent `finalize_invoice_move_lines` method.

        Raises:
            UserError: If any discount fields (`kg_discount` or `kg_discount_per`)
                       are non-zero.
        """
        result = super(AccountInvoice, self).finalize_invoice_move_lines(move_lines)
        type = self.type

        kg_discount_per = self.kg_discount_per
        kg_discount = self.kg_discount
        if kg_discount_per or kg_discount:
            raise UserError(_('adjust discount in lines and the fields discount and discount% should be zero'))


        return result


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'


    kg_is_it_tranpcharge = fields.Boolean('Other Cost')
    kg_provision_acc_id = fields.Many2one('account.account', string="Pro.Tranportation")


class KgInvoiceTermsLine(models.Model):
    _name = "kg.invoice.terms.line"
    invoice_id = fields.Many2one('account.invoice', string="Invoice")
    terms_id = fields.Many2one('kg.terms.condition', string="Terms and Condition")
