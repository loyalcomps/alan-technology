# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
from datetime import date, timedelta


class PaymentAllocation(models.TransientModel):
    _name = 'payment.allocation.wizard'
    _description = 'payment allocation'

    partner_id = fields.Many2one('res.partner', string="Partner")
    company_id = fields.Many2one('res.company', string="Company")
    account_id = fields.Many2one('account.account', string="Account")
    show_parent_child = fields.Boolean("Show parent/children")
    payment_id = fields.Many2one('account.payment', string="Payment")
    balnc_paymnt_amnt = fields.Float(string="Balance Amount", store=True)
    invoice_allocation_ids = fields.One2many('payment.allocation.wizard.debit.lines', 'rec_id', "Invoices")
    payment_allocation_ids = fields.One2many('payment.allocation.wizard.credit.lines', 'rec_id', "Payments")
    move_line_id = fields.Many2one('account.move.line', related='invoice_allocation_ids.move_line_id.move_id')
    payment_type = fields.Selection([('inbound', 'Receive Money'), ('outbound', 'Send Money')], string="Payment Type",
                                    required=False)

    @api.onchange('show_parent_child')
    def onchange_show_parent_child(self):
        payment_type = self.payment_type

        move=self.env['account.move'].search([('partner_id', '=', self.partner_id.id),('state', 'in', ['posted']), ('move_type', 'in', ['entry'])])
        pay_term_lines = move.line_ids \
            .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))


        for data in self:

            if data.show_parent_child:
                inv_vals = [(5, 0, 0)]
                partner = self.env['res.partner'].search(
                    ['|', '|', ('id', 'in', data.partner_id.child_ids.ids), ('id', '=', data.partner_id.id),
                     ('id', '=', data.partner_id.parent_id.id)])
                if data.payment_type == 'inbound':
                    for p in partner:
                        invoice = self.env['account.move'].search([('partner_id', '=', p.id), (
                            'amount_residual', '>', 0.0), ('state', 'in', ['posted']),
                                                                   ('move_type', 'in', ['out_invoice'])])

                        for inv in invoice:
                            val = 0
                            for line in inv.line_ids:
                                if line.credit == 0:
                                    val = line.id
                                    vals = {'inv_amount': inv.amount_total,
                                            'name': inv.name,
                                            'inv_date': inv.invoice_date,
                                            'move_line_id': val,
                                            'date_due': inv.invoice_date_due,
                                            'inv_unallocated_amount': inv.amount_residual,
                                            }
                            inv_vals.append((0, 0, vals))
                        journal_entry = self.env['account.move.line'].search([
                            ('account_id', 'in', pay_term_lines.account_id.ids),
                            ('move_id', '!=', self.payment_id.move_id.id),

                            ('parent_state', '=', 'posted'), ('balance', '<', 0.0),
                            ('partner_id', '=', p.id),
                            ('reconciled', '=', False),
                            '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
                        ])


                        # for line in journal_entry:
                        for line in journal_entry.filtered(
                                    lambda l: l.debit == 0 and l.move_id.journal_id.type not in ['bank', 'cash']):
                            if line.currency_id == move.currency_id:
                                # Same foreign currency.
                                amount = abs(line.amount_residual_currency)
                            else:
                                # Different foreign currencies.
                                amount = line.company_currency_id._convert(
                                    abs(line.amount_residual),
                                    move.currency_id,
                                    move.company_id,
                                    line.date,
                                )

                            if line.debit == 0:
                                val = line.id
                                jvals = {'inv_amount': amount,
                                        'name': line.move_id.name,
                                        'inv_date': line.move_id.date,
                                        'move_line_id': val,
                                        'date_due': line.date,
                                        'inv_unallocated_amount': line.amount_residual,
                                        }
                            inv_vals.append((0, 0, jvals))
                    data.invoice_allocation_ids = inv_vals

                    cred_invoice = self.env['account.move'].search([('partner_id', '=', p.id), (
                        'amount_residual', '>', 0.0), ('state', 'in', ['posted']),
                                                                    ('move_type', 'in', ['out_refund'])])
                    pay_vals = []
                    for cred in cred_invoice:
                        val = 0
                        for line in cred.line_ids:
                            if line.credit == 0:
                                val = line.id
                                vals = {
                                    'name': cred.name,
                                    'date': cred.invoice_date,
                                    'memo': cred.ref,
                                    'amount': cred.amount_residual

                                }
                        pay_vals.append((0, 0, vals))
                    data.payment_allocation_ids = pay_vals

                else:
                    for p in partner:
                        invoice = self.env['account.move'].search([('partner_id', '=', p.id), (
                            'amount_residual', '>', 0.0), ('state', 'in', ['posted']),
                                                                   ('move_type', 'in', ['in_invoice'])])
                        for inv in invoice:
                            val = 0
                            for line in inv.line_ids:
                                if line.credit == 0:
                                    val = line.id
                                    vals = {'inv_amount': inv.amount_total,
                                            'name': inv.name,
                                            'inv_date': inv.invoice_date,
                                            'move_line_id': val,
                                            'date_due': inv.invoice_date_due,
                                            'inv_unallocated_amount': inv.amount_residual,
                                            }
                            inv_vals.append((0, 0, vals))
                        journal_entry = self.env['account.move.line'].search([
                            ('account_id', 'in', pay_term_lines.account_id.ids),
                            ('move_id', '!=', self.payment_id.move_id.id),

                            ('parent_state', '=', 'posted'), ('balance', '>', 0.0),
                            ('partner_id', '=', p.id),
                            ('reconciled', '=', False),
                            '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
                        ])

                        # for line in journal_entry:
                        for line in journal_entry.filtered(
                                    lambda l: l.credit == 0 and l.move_id.journal_id.type not in ['bank', 'cash']):
                            if line.currency_id == move.currency_id:
                                # Same foreign currency.
                                amount = abs(line.amount_residual_currency)
                            else:
                                # Different foreign currencies.
                                amount = line.company_currency_id._convert(
                                    abs(line.amount_residual),
                                    move.currency_id,
                                    move.company_id,
                                    line.date,
                                )

                            if line.credit == 0:
                                val = line.id
                                j_vals = {'inv_amount': amount,
                                        'name': line.move_id.name,
                                        'inv_date': line.move_id.date,
                                        'move_line_id': val,
                                        'date_due': line.date,
                                        'inv_unallocated_amount': line.amount_residual,
                                        }
                            inv_vals.append((0, 0, j_vals))
                    data.invoice_allocation_ids = inv_vals

                    cred_invoice = self.env['account.move'].search([('partner_id', '=', p.id), (
                        'amount_residual', '>', 0.0), ('state', 'in', ['posted']),
                                                                    ('move_type', 'in', ['in_refund'])])
                    pay_vals = []
                    for cred in cred_invoice:
                        val = 0
                        for line in cred.line_ids:
                            if line.credit == 0:
                                val = line.id
                                vals = {
                                    'name': cred.name,
                                    'date': cred.invoice_date,
                                    'memo': cred.ref,
                                    'amount': cred.amount_residual

                                }
                        pay_vals.append((0, 0, vals))
                    data.payment_allocation_ids = pay_vals

            else:
                inv_vals = [(5, 0, 0)]
                partner = self.env['res.partner'].search(
                    ['|', '|', ('id', 'in', data.partner_id.child_ids.ids), ('id', '=', data.partner_id.id),
                     ('id', '=', data.partner_id.parent_id.id)])
                if data.payment_type == 'inbound':
                    for p in partner:
                        invoice = self.env['account.move'].search([('partner_id', '=', p.id), (
                            'amount_residual', '>', 0.0), ('state', 'in', ['posted']),
                                                                   ('move_type', 'in', ['out_invoice'])])

                        for inv in invoice:

                            val = 0
                            for line in inv.line_ids:
                                print("-----------invoiceeeeeeeeeee ACCOUNT NAME", line.move_id.name)

                                if line.credit == 0:
                                    val = line.id
                                    vals = {'inv_amount': inv.amount_total,
                                            'name': inv.name,
                                            'inv_date': inv.invoice_date,
                                            'move_line_id': val,
                                            'date_due': inv.invoice_date_due,
                                            'inv_unallocated_amount': inv.amount_residual,
                                            }
                            inv_vals.append((0, 0, vals))
                        journal_entry = self.env['account.move.line'].search([
                            ('account_id', 'in', pay_term_lines.account_id.ids),

                            ('move_id', '!=', self.payment_id.move_id.id),

                            ('parent_state', '=', 'posted'), ('balance', '<', 0.0),
                            ('partner_id', '=', p.id),
                            ('reconciled', '=', False),
                            '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
                        ])


                        for line in journal_entry.filtered(
                                    lambda l: l.debit == 0 and l.move_id.journal_id.type not in ['bank', 'cash']):

                            if line.currency_id == move.currency_id:
                                # Same foreign currency.
                                amount = abs(line.amount_residual_currency)
                            else:
                                # Different foreign currencies.
                                amount = line.company_currency_id._convert(
                                    abs(line.amount_residual),
                                    move.currency_id,
                                    move.company_id,
                                    line.date,
                                )

                            if line.debit == 0:
                                val = line.id
                                j_vals = {'inv_amount': amount,
                                        'name': line.move_id.name,
                                        'inv_date': line.move_id.date,
                                        'move_line_id': val,
                                        'date_due': line.date,
                                        'inv_unallocated_amount': line.amount_residual,
                                        }
                            inv_vals.append((0, 0, j_vals))

                    data.invoice_allocation_ids = inv_vals


                    cred_invoice = self.env['account.move'].search([('partner_id', '=', p.id), (
                        'amount_residual', '>', 0.0), ('state', 'in', ['posted']),
                                                                    ('move_type', 'in', ['out_refund'])])
                    pay_vals = []
                    for cred in cred_invoice:
                        val = 0
                        for line in cred.line_ids:
                            if line.credit == 0:
                                val = line.id
                                vals = {
                                    'name': cred.name,
                                    'date': cred.invoice_date,
                                    'memo': cred.ref,
                                    'amount': cred.amount_residual

                                }
                        pay_vals.append((0, 0, vals))
                    data.payment_allocation_ids = pay_vals
                else:

                    for p in partner:
                        invoice = self.env['account.move'].search([('partner_id', '=', p.id), (
                            'amount_residual', '>', 0.0), ('state', 'in', ['posted']),
                                                                   ('move_type', 'in', ['in_invoice'])])
                        for inv in invoice:
                            val = 0
                            for line in inv.line_ids:


                                if line.credit == 0:
                                    val = line.id
                                    vals = {'inv_amount': inv.amount_total,
                                            'name': inv.name,
                                            'inv_date': inv.invoice_date,
                                            'move_line_id': val,
                                            'date_due': inv.invoice_date_due,
                                            'inv_unallocated_amount': inv.amount_residual,
                                            }
                            inv_vals.append((0, 0, vals))
                        journal_entry = self.env['account.move.line'].search([
                            ('account_id', 'in', pay_term_lines.account_id.ids),
                            # ('account_id.account_type', 'in',['asset_receivable', 'liability_payable']),
                            ('move_id','!=',self.payment_id.move_id.id),

                            ('parent_state', '=', 'posted'), ('balance', '>', 0.0),
                            ('partner_id', '=', p.id),
                            ('reconciled', '=', False),
                            '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
                        ])


                        for line in journal_entry.filtered(lambda l:l.credit==0 and l.move_id.journal_id.type not in ['bank','cash']):


                            if line.currency_id == move.currency_id:
                                # Same foreign currency.
                                amount = abs(line.amount_residual_currency)
                            else:
                                # Different foreign currencies.
                                amount = line.company_currency_id._convert(
                                    abs(line.amount_residual),
                                    move.currency_id,
                                    move.company_id,
                                    line.date,
                                )

                            if line.credit == 0:
                                val = line.id
                                j_vals = {'inv_amount': amount,
                                        'name': line.move_id.name,
                                        'inv_date': line.move_id.date,
                                        'move_line_id': val,
                                        'date_due': line.date,
                                        'inv_unallocated_amount': line.amount_residual,
                                        }
                            inv_vals.append((0, 0, j_vals))


                        data.invoice_allocation_ids = inv_vals

                        cred_invoice = self.env['account.move'].search([('partner_id', '=', p.id), (
                            'amount_residual', '>', 0.0), ('state', 'in', ['posted']),
                                                                        ('move_type', 'in', ['in_refund'])])
                        pay_vals = []
                        for cred in cred_invoice:
                            val = 0
                            for line in cred.line_ids:
                                if line.credit == 0:
                                    val = line.id
                                    vals = {
                                        'name': cred.name,
                                        'date': cred.invoice_date,
                                        'memo': cred.ref,
                                        'amount': cred.amount_residual

                                    }
                            pay_vals.append((0, 0, vals))
                        data.payment_allocation_ids = pay_vals


    def get_matching_dict(self, debit_move_dict, credit_move_dict):
        matching_list = []
        debit_dict = {}
        credit_dict = {}
        payment_type = self.payment_type
        if payment_type == 'inbound':
            debit_dict = debit_move_dict
            credit_dict = credit_move_dict
        elif payment_type == 'outbound':
            debit_dict = credit_move_dict
            credit_dict = debit_move_dict
        if payment_type in ('inbound', 'outbound'):
            for cred_move_id, credamt, in credit_dict.items():
                if credamt > 0.0:
                    for deb_move_id, debamt in debit_dict.items():
                        is_full_reconcile = debit_dict['is_full_reconcile']
                        balance = credamt - debamt
                        if credamt <= 0.0:
                            continue
                        if debamt == 0.0:
                            continue
                        if balance > 0.0:
                            ful_rec = self.env['account.full.reconcile']
                            if is_full_reconcile == True:
                                vals = {}
                                ful_rec = self.env['account.full.reconcile'].create(vals)
                            if deb_move_id != 'is_full_reconcile':
                                matching_list.append(
                                    {'credit_move_id': cred_move_id, 'full_reconcile_id': ful_rec.id,
                                     'debit_amount_currency': debamt, 'credit_amount_currency': debamt,
                                     'debit_move_id': deb_move_id, 'amount': debamt})
                            debit_dict[deb_move_id] = 0.0

                        if balance < 0.0:
                            ful_rec = self.env['account.full.reconcile']
                            if is_full_reconcile == True:
                                vals = {}
                                ful_rec = self.env['account.full.reconcile'].create(vals)
                            if deb_move_id != 'is_full_reconcile':
                                matching_list.append(
                                    {'credit_move_id': cred_move_id, 'full_reconcile_id': ful_rec.id,
                                     'debit_amount_currency': credamt, 'credit_amount_currency': credamt,
                                     'debit_move_id': deb_move_id, 'amount': credamt})
                            debit_dict[deb_move_id] = abs(balance)
                            credit_dict[cred_move_id] = 0.0


                        if balance == 0.0:
                            ful_rec = self.env['account.full.reconcile']
                            if is_full_reconcile == True:
                                vals = {}
                                ful_rec = self.env['account.full.reconcile'].create(vals)

                            if deb_move_id != 'is_full_reconcile':
                                matching_list.append(
                                    {'credit_move_id': cred_move_id, 'full_reconcile_id': ful_rec.id,
                                     'debit_move_id': deb_move_id, 'debit_amount_currency': debamt,
                                     'credit_amount_currency': debamt, 'amount': debamt})
                            debit_dict[deb_move_id] = 0.0
                            credit_dict[cred_move_id] = 0.0
                            credamt = 0.0
                        credamt = balance
        return matching_list

    def validate_payment(self):
        payment_amount = 0
        for rec in self.payment_allocation_ids:
            payment_amount += rec.amount
        for rec in self.invoice_allocation_ids:
            if (rec.inv_allocate_amount) > (rec.inv_unallocated_amount):
                print("-------------",rec.inv_allocate_amount, rec.inv_unallocated_amount)
                raise ValidationError(_('Allocate amount exceeds invoice amount'))
            if rec.inv_allocate_amount > payment_amount:
                raise ValidationError(_('Allocate amount exceeds payment amount'))

        debit_move_dict = {}
        credit_move_dict = {}
        for line in self.invoice_allocation_ids:
            # debit_move_dict[line.move_line_id.id] = line.inv_allocate_amount
            val_2 = line.move_line_id.id
            if line.move_line_id.move_id.move_type == 'out_invoice':
                if line.move_line_id.move_id.line_ids.filtered(lambda l: l.credit == 0):
                    val_2 = line.move_line_id.move_id.line_ids.filtered(lambda l: l.credit == 0)[0].id
            elif line.move_line_id.move_id.move_type == 'in_invoice':
                if line.move_line_id.move_id.line_ids.filtered(lambda l: l.debit == 0):
                    val_2 = line.move_line_id.move_id.line_ids.filtered(lambda l: l.debit == 0)[0].id
            debit_move_dict[val_2] = line.inv_allocate_amount

        for line in self.payment_allocation_ids:
            credit_move_dict[line.move_line_id.id] = self.balnc_paymnt_amnt

        for line in self.invoice_allocation_ids:
            if self.payment_type == "inbound":
                if line.inv_unallocated_amount == line.inv_allocate_amount:
                    debit_move_dict['is_full_reconcile'] = True
                else:
                    debit_move_dict['is_full_reconcile'] = False
            else:
                if line.inv_unallocated_amount == line.inv_allocate_amount:
                    credit_move_dict['is_full_reconcile'] = True
                else:
                    credit_move_dict['is_full_reconcile'] = False

        matching_list = self.get_matching_dict(debit_move_dict, credit_move_dict)
        for rec_val in matching_list:
            rec = self.env['account.partial.reconcile'].create(rec_val)


class DebitLines(models.TransientModel):
    _name = "payment.allocation.wizard.debit.lines"
    _description = 'Debit Lines'

    rec_id = fields.Many2one('payment.allocation.wizard')
    invoice_id = fields.Many2one('account.move')
    partner_id = fields.Many2one('res.partner', string="Partner")
    name = fields.Char(string="Invoices")
    move_line_id = fields.Many2one('account.move.line', string="Move Line")
    inv_date = fields.Date("Invoice Date")
    date_due = fields.Date("Due Date")
    inv_amount = fields.Float('Invoice Amount')
    inv_unallocated_amount = fields.Float('Unallocated Amount')
    inv_allocate_amount = fields.Float('Allocate Amount')
    is_invoice_allocate = fields.Boolean(string="Allocate")

    balance_amount = fields.Float('Balance')

    @api.onchange('is_invoice_allocate')
    def onchange_is_invoice_allocate(self):

        total_payment = []
        for vals in self.rec_id.payment_allocation_ids:
            total_payment.append(vals.amount)


        payment_amount = sum(total_payment)

        if self.is_invoice_allocate:
            for rec in self:
                if rec.inv_unallocated_amount >= payment_amount:
                    rec.inv_allocate_amount = payment_amount
                    payment_amount += rec.inv_unallocated_amount - payment_amount
                else:
                    rec.inv_allocate_amount = rec.inv_unallocated_amount

        else:
            self.inv_allocate_amount = 0.0


class CreditLines(models.TransientModel):
    _name = "payment.allocation.wizard.credit.lines"
    _description = 'Credit Lines'

    rec_id = fields.Many2one('payment.allocation.wizard')
    name = fields.Char(string="Payment")
    move_line_id = fields.Many2one('account.move.line', string="Move Line")
    date = fields.Date("Payment Date")
    amount = fields.Float('Payment Amount')
    memo = fields.Char('Memo')
