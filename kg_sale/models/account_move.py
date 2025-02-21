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
    kg_sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    kg_bank_id = fields.Many2one('res.bank', string='Bank')

    def _search_default_journal(self):
        if self.payment_id and self.payment_id.journal_id:
            return self.payment_id.journal_id
        if self.statement_line_id and self.statement_line_id.journal_id:
            return self.statement_line_id.journal_id
        if self.statement_line_ids.statement_id.journal_id:
            return self.statement_line_ids.statement_id.journal_id[:1]

        journal_types = self._get_valid_journal_types()
        company_id = (self.company_id or self.env.company).id
        domain = [('company_id', '=', company_id), ('type', 'in', journal_types)]

        journal = None
        # the currency is not a hard dependence, it triggers via manual add_to_compute
        # avoid computing the currency before all it's dependences are set (like the journal...)
        if self.env.cache.contains(self, self._fields['currency_id']):
            currency_id = self.currency_id.id or self._context.get('default_currency_id')
            if currency_id and currency_id != self.company_id.currency_id.id:
                currency_domain = domain + [('currency_id', '=', currency_id)]
                journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)

        if not journal:
            company = self.env['res.company'].browse(company_id)

            error_msg = _(
                "No journal could be found in company %(company_name)s for any of those types: %(journal_types)s",
                company_name=company.display_name,
                journal_types=', '.join(journal_types),
            )
            raise UserError(error_msg)

        if self._context.get('default_move_type') == 'entry':
            return None
        return journal

    def get_capital(self, text):
        return text.title()

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """hide report based on company"""
        arch, view = super()._get_view(view_id, view_type, **options)
        if not self.env.company.country_id.name == "Saudi Arabia":
            reports = self.env['ir.actions.report'].search([('company_type', '=', 'saudi')])
            for rp in reports:
                rp.unlink_action()
            reports = self.env['ir.actions.report'].search([('company_type', '=', 'non_saudi')])
            for nrp in reports:
                nrp.create_action()
        else:
            reports = self.env['ir.actions.report'].search([('company_type', '=', 'saudi')])
            for rp in reports:
                rp.create_action()
            reports = self.env['ir.actions.report'].search([('company_type', '=', 'non_saudi')])
            for nrp in reports:
                nrp.unlink_action()
        return arch, view

    # @api.depends(
    #     'state', 'currency_id', 'invoice_line_ids.price_subtotal',
    #     'move_id.line_ids.amount_residual',
    #     'move_id.line_ids.currency_id')
    # def _compute_residual(self):
    #
    #     residual = 0.0
    #     residual_company_signed = 0.0
    #     sign = self.move_type in ['in_refund', 'out_refund'] and -1 or 1
    #     for line in self.sudo().move_id.line_ids:
    #         if line.account_id.internal_type in ('receivable', 'payable') and line.name != 'Recievable Adjust':
    #
    #             residual_company_signed += line.amount_residual
    #             if line.currency_id == self.currency_id:
    #                 residual += line.amount_residual_currency if line.currency_id else line.amount_residual
    #             else:
    #                 from_currency = (line.currency_id and line.currency_id.with_context(
    #                     date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
    #                 residual += from_currency.compute(line.amount_residual, self.currency_id)
    #
    #     self.residual_company_signed = abs(residual_company_signed) * sign
    #     self.residual_signed = abs(residual) * sign
    #     self.residual = abs(residual)
    #     digits_rounding_precision = self.currency_id.rounding
    #     if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
    #         self.reconciled = True
    #     else:
    #         self.reconciled = False

    @api.depends('invoice_line_ids')
    def _compute_kg_net_discount(self):
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
    number = fields.Char(store=True, copy=False)
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

    ###over written for discount
    #
    # @api.depends('kg_discount', 'kg_discount_per','invoice_line_ids.price_subtotal','move_type','invoice_line_ids.price_subtotal')
    # def _compute_amount(self, ):
    #     if self.kg_discount and self.kg_discount_per:
    #         raise UserError(_('At a time choose one option discount(%) or discount'))
    #
    #     if self.kg_discount_per > 100:
    #         raise UserError(_('maximum value 100'))
    #
    #     amount_untaxed = 0
    #
    #     for line in self.invoice_line_ids:
    #         if not line.kg_is_it_tranpcharge:
    #             amount_untaxed = amount_untaxed + line.price_subtotal
    #
    #     #        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
    #     self.amount_untaxed = amount_untaxed
    #     # self.amount_tax = sum(line.amount for line in self.tax_ids)
    #     # self.amount_tax = 0
    #     #
    #     discount = 0
    #     if self.kg_discount:
    #         discount = self.kg_discount
    #     if self.kg_discount_per:
    #         discount = float(float(self.kg_discount_per) / float(100)) * (self.amount_untaxed + self.amount_tax)
    #
    #     self.amount_total = (self.amount_untaxed + self.amount_tax) - discount
    #     amount_total_company_signed = self.amount_total
    #     amount_untaxed_signed = self.amount_untaxed
    #     if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
    #         currency_id = self.currency_id.with_context(date=self.date_invoice)
    #
    #         amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
    #         amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
    #     sign = self.move_type in ['in_refund', 'out_refund'] and -1 or 1
    #     amount_total_company_signed = amount_total_company_signed * sign
    #     self.amount_total_signed = self.amount_total * sign
    #     self.amount_untaxed_signed = amount_untaxed_signed * sign

    ###overwritten for discount entry

    def finalize_invoice_move_lines(self, move_lines):
        result = super(AccountInvoice, self).finalize_invoice_move_lines(move_lines)
        type = self.type

        kg_discount_per = self.kg_discount_per
        kg_discount = self.kg_discount
        if kg_discount_per or kg_discount:
            raise UserError(_('adjust discount in lines and the fields discount and discount% should be zero'))
        #        kg_discount_acc_id = self.kg_discount_acc_id and self.kg_discount_acc_id.id

        #        rate = self.currency_id and self.currency_id.rate or 1

        #        if type == 'out_invoice':
        #			invoice_line = self.invoice_line_ids
        #			invoice_id = self.id
        #			howmanyothercostlines = self.env['account.invoice.line'].search([('invoice_id', '=', invoice_id),('kg_is_it_tranpcharge', '!=', False)])
        #			if len(invoice_line) == 1 and len(howmanyothercostlines) == 1:
        #				raise UserError(_('you cannot invoice other cost item alone'))
        #			if len(howmanyothercostlines) == 1 and type == 'out_invoice':
        #				if len(howmanyothercostlines) >=2:
        #					raise UserError(_('you cannot have more than one other cost items in a single invoice'))

        #				total_transportcharge = howmanyothercostlines.price_subtotal
        #				kg_trans_exp_acc_id = self.kg_trans_exp_acc_id and self.kg_trans_exp_acc_id.id or False
        #				kg_trans_pro_acc_id = self.kg_trans_pro_acc_id and self.kg_trans_pro_acc_id.id or False
        #				if not kg_trans_pro_acc_id or not kg_trans_exp_acc_id:
        #					raise UserError(_('Please fill the transportation account details'))
        #				othercost_pdt_id = howmanyothercostlines.product_id and howmanyothercostlines.product_id.id
        #				if howmanyothercostlines.product_id.type != 'service':
        #					raise UserError(_('Transportation product must be service type'))

        #
        #
        #				count = 0
        #				for vals in result:
        #					account_id = vals[2]['account_id']
        #					account_obj = self.env['account.account'].browse(account_id)
        #					user_type_id = account_obj.user_type_id and account_obj.user_type_id.name
        #					if user_type_id == 'Receivable':
        #						vals[2]['debit'] = vals[2]['debit'] - total_transportcharge
        #					if vals[2]['product_id'] == othercost_pdt_id and not count:

        #						val = (0, 0, {'analytic_account_id': vals[2]['analytic_account_id'], 'name': 'Transportation Expense',  'product_uom_id': vals[2]['product_uom_id'], 'invoice_id': vals[2]['invoice_id'],'currency_id': vals[2]['currency_id'], 'debit': total_transportcharge, 'product_id': vals[2]['product_id'], 'date_maturity': vals[2]['date_maturity'], 'credit': False, 'amount_currency': vals[2]['amount_currency'], 'quantity': 1, 'partner_id': vals[2]['partner_id'], 'account_id': kg_trans_exp_acc_id})
        #						count = count +1
        #						result.append(val)

        #					if vals[2]['product_id'] == othercost_pdt_id and vals[2]['credit']:
        #						vals[2]['account_id'] = kg_trans_pro_acc_id

        #

        #        print "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",result
        #        if (kg_discount_per or kg_discount) and type == 'out_invoice':
        #			if not kg_discount_acc_id:
        #				raise UserError(_('define discount account'))
        ##				print "????????????????????????",result

        #			for line in result:
        #				account_id = line[2]['account_id']
        #				account_obj = self.env['account.account'].browse(account_id)
        #				user_type_id = account_obj.user_type_id and account_obj.user_type_id.name
        #				if line[2]['debit'] and user_type_id == 'Receivable':
        #					discount = 0
        #					if kg_discount:
        #						discount = kg_discount
        #						if rate >=1:
        #							discount = rate * discount
        #						else:
        #							discount = float(discount) / float(rate)
        #					else:
        #						discount = float(float(float(kg_discount_per) / float(100)) * line[2]['debit'])
        #						if rate >=1:
        #							discount = rate * discount
        #						else:
        #							discount = float(discount) / float(rate)
        #					line[2]['debit'] = line[2]['debit'] - discount
        #					val = (0, 0, {'analytic_account_id': line[2]['analytic_account_id'], 'name': 'Discount',  'product_uom_id': line[2]['product_uom_id'], 'invoice_id': line[2]['invoice_id'],'currency_id': line[2]['currency_id'], 'credit': line[2]['credit'], 'product_id': line[2]['product_id'], 'date_maturity': line[2]['date_maturity'], 'debit': discount, 'amount_currency': line[2]['amount_currency'], 'quantity': line[2]['quantity'], 'partner_id': line[2]['partner_id'], 'account_id': kg_discount_acc_id})
        #					result.append(val)

        #

        return result


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    kg_is_it_tranpcharge = fields.Boolean('Other Cost')
    kg_provision_acc_id = fields.Many2one('account.account', string="Pro.Tranportation")
    is_cost_checked = fields.Boolean(stirng="Is Cost Checked", default=False)
    cost = fields.Float(string='Cost', store=True)
    total_cost = fields.Float('Total Cost', compute='compute_cost', store=True,
                              domain=[('move_type', '=', 'out_invoice')])
    profit = fields.Monetary('Profit', compute='compute_cost', store=True, domain=[('move_type', '=', 'out_invoice')])
    sale_line_id = fields.Many2one('sale.order.line')

    @api.depends('cost', 'quantity', 'price_unit', 'price_subtotal', 'total_cost')
    def compute_cost(self):
        for rec in self:
            rec.total_cost = rec.cost * rec.quantity
            profit = rec.price_subtotal - rec.total_cost
            if rec.move_type == 'out_refund':
                if profit < 0:
                    rec.profit = profit
                else:
                    rec.profit = -profit
            else:
                rec.profit = profit
    def remove_cost_check(self):
        recs = self.sudo().search([('is_cost_checked', '=', True)])
        for rec in recs:
            rec.is_cost_checked = False

    def recompute_invoice_cost(self):
        recs = self.sudo().search(
            [('is_cost_checked', '=', False),
             ('move_type', 'in', ['out_invoice'])], limit=1200)

        for rec in recs:
            try:
                cost = 0
                invoice_rec = rec.move_id
                sale_rec = invoice_rec.kg_so_id
                if sale_rec:
                    delivery_recs = sale_rec.picking_ids
                    if delivery_recs:
                        delivery_recs = delivery_recs.filtered(lambda a: a.picking_type_code == 'outgoing' and a.state == 'done' and kg_invoice_id and kg_invoice_id == invoice_rec.id)
                        
                        for d_rec in delivery_recs:
                            
                            valuation_recs = self.env['stock.valuation.layer'].sudo().search(
                                [('reference', '=', d_rec.name), ('product_id', '=', rec.product_id.id)])
    
                            if valuation_recs:
                                # cost = sum(valuation_recs.mapped('unit_cost'))
                                for v_rec in valuation_recs:
                                    if v_rec.unit_cost:
                                        cost += v_rec.unit_cost
                                    else:
                                        cost += rec.product_id.standard_price

                rec.sudo().write(
                    {
                        'cost': cost,
                        'is_cost_checked': True
                    }
                )
            except Exception as e:
                _logger.error("Error in recompute_cost: %s", e)
                
    def recompute_credit_note_cost(self):
        recs = self.sudo().search(
            [('is_cost_checked', '=', False),
             ('move_type', 'in', ['out_refund'])], limit=1200)

        for rec in recs:
            try:
                cost = 0
                invoice_rec = rec.move_id
                sale_rec = invoice_rec.kg_so_id
                if sale_rec:
                    delivery_recs = sale_rec.picking_ids
                    if delivery_recs:
                        delivery_recs = delivery_recs.filtered(lambda a: a.picking_type_code == 'incoming' and a.state == 'done')
                        
                        for d_rec in delivery_recs:
                            
                            valuation_recs = self.env['stock.valuation.layer'].sudo().search(
                                [('reference', '=', d_rec.name), ('product_id', '=', rec.product_id.id)])
    
                            if valuation_recs:
                                # cost = sum(valuation_recs.mapped('unit_cost'))
                                for v_rec in valuation_recs:
                                    if v_rec.unit_cost:
                                        cost += v_rec.unit_cost
                                    else:
                                        cost += rec.product_id.standard_price

                rec.sudo().write(
                    {
                        'cost': cost,
                        'is_cost_checked': True
                    }
                )
            except Exception as e:
                _logger.error("Error in recompute_cost: %s", e)



class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    total_cost = fields.Float('Total Cost')
    profit = fields.Float('Profit')

    def _select(self):
        res = super()._select()
        # res = res + ",(line.cost * line.quantity) as total_cost, (line.price_subtotal - line.total_cost) as profit"
        res = res + ",line.total_cost as total_cost, line.profit as profit"
        return res


class KgInvoiceTermsLine(models.Model):
    _name = "kg.invoice.terms.line"
    invoice_id = fields.Many2one('account.invoice', string="Invoice")
    terms_id = fields.Many2one('kg.terms.condition', string="Terms and Condition")
