# -*- coding: utf-8 -*-
from odoo import fields, models


class ImportReconcile(models.Model):
    """ To reconcile imported entries """
    _name = 'import.reconcile'
    _description = 'import.reconcile'

    account_move_ids = fields.One2many('account.move.import', 'reconcile_id', string='Account Move Entry')
    payment_ids = fields.One2many('account.payment.import', 'payment_reconcile_id', string='Payments Entry')
    conciled = fields.Boolean(default=False)

    def validate_entry(self):
        for imp in self.env['import.reconcile'].sudo().search([]):
            if len(imp.payment_ids) == 1:
                payment_line = self.env['payment.journal'].sudo().search([('paymet_ref', '=', imp.payment_ids.x_payment)])
                if len(payment_line) > 0:
                    credit_move_id = self.env['account.payment'].search(
                        [('name', '=', payment_line.journal_ref)]).move_id.line_ids.filtered(
                        lambda l: l.account_id == imp.payment_ids[0].imp_account_id)
                    if len(credit_move_id) > 0:
                        for inv_line in imp.account_move_ids:
                            in_line = self.env['account.move'].search([('name','=',inv_line.x_invoice)])
                            if len(in_line) == 1:
                                debit_move_id = in_line.line_ids.filtered(lambda l: l.account_id == inv_line.imp_account_id)
                                reconcile_id = self.env['account.partial.reconcile'].sudo().create(
                                    {'debit_move_id': debit_move_id.id,
                                     'credit_move_id': credit_move_id.id,
                                     'amount': inv_line.allocation,
                                     'debit_amount_currency': inv_line.allocation,
                                     'credit_amount_currency': inv_line.allocation,
                                     })
                                imp.write({'conciled':True})


class AccountMove(models.Model):
    _name = 'account.move.import'
    _description = 'account.move'

    reconcile_id = fields.Many2one('import.reconcile', string='Inverse')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    acc_date = fields.Date(string='Date')
    imp_partner_id = fields.Many2one('res.partner',string='Partner')
    imp_account_id = fields.Many2one('account.account', string='Account')
    allocation = fields.Float(string='Allocate')


class AccountPayment(models.Model):
    _name = 'account.payment.import'
    _description = 'account.payment'

    payment_reconcile_id = fields.Many2one('import.reconcile', string='Inverse')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    payment = fields.Char(string='Payment')
    acc_date = fields.Date(string='Date')
    imp_partner_id = fields.Many2one('res.partner',string='Partner')
    imp_account_id = fields.Many2one('account.account', string='Account')
    allocation = fields.Float(string='Allocate')


class ImportReconcile(models.Model):
    """ link payment with journal """
    _name = 'payment.journal'

    journal_ref = fields.Char()
    paymet_ref = fields.Char()