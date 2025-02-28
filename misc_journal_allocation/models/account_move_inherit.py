from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
from datetime import date, datetime, timedelta
from odoo.exceptions import Warning


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    # self.write({'state': 'posted'})

    def action_open_journal_allocation_wizard(self):
        payment_vals = []
        partner = False
        def_id = False
        payment_amount=0
        company = False
        inv_vals = []
        amount_bal = 0
        val_1=False


        for data in self:
            if partner != data.partner_id.id and partner != False:
                raise ValidationError(_('Selected Journals are of different Partners'))
            allocatable_lines=data.line_ids.filtered(lambda account:account.account_id.account_type in ['asset_receivable','liability_payable'] and account.partner_id)
            if not allocatable_lines:
                raise ValidationError(_('Allocation cannot be done'))

            for line in allocatable_lines:
                partner = line.partner_id
                if line.account_id.account_type =='asset_receivable' and line.debit==0:
                    payment_amount = line.credit
                    val_1 = line.id

                    # partial = self.env['account.partial.reconcile'].search([('credit_move_id', '=', val_1)])
                    # for val in partial:
                    #
                    #     amount_bal += val.debit_amount_currency
                    debit = self.env['account.partial.reconcile'].search([('credit_move_id', '=', val_1)])

                    for val in debit:

                        amount_bal += val.credit_amount_currency


                        amount_bal += val.debit_amount_currency
                if line.account_id.account_type =='liability_payable' and line.credit==0:
                    payment_amount=line.debit

                    val_1 = line.id
                    debit = self.env['account.partial.reconcile'].search([('debit_move_id', '=', val_1)])

                    for val in debit:


                        amount_bal += val.debit_amount_currency
                payment_vals.append({
                                     'name': data.name,
                                     'date': data.date,
                                     'memo': line.name,
                                     'move_line_id':line.id,
                                     'amount': line.credit if line.credit !=0 else line.debit})


                def_id = data.id
                company = data.company_id.id

                invoice = self.env['account.move'].search([('partner_id', '=', partner.id),('payment_state','in',['partial','not_paid','in_payment']),
                                                           ('amount_residual','!=',0.0),('state','in',['posted'])])

                for inv in invoice:
                    val_2 = 0
                    # for line in inv.line_ids:
                    #     # Extra codition added for(out_invoice/in_invoice)
                    #     print("line.move_id.move_type",line.move_id.move_type)
                    #     if line.move_id.move_type == 'out_invoice':
                    #         if line.credit == 0:
                    #             val_2 = line.id
                    #     elif line.move_id.move_type == 'in_invoice':
                    #         if line.debit == 0:
                    #             val_2 = line.id
                    if inv.move_type == 'out_invoice':
                        if inv.line_ids.filtered(lambda l: l.credit == 0):
                            val_2 = inv.line_ids.filtered(lambda l: l.credit == 0)[0].id
                    elif inv.move_type == 'in_invoice':
                        if inv.line_ids.filtered(lambda l: l.debit == 0):
                            val_2 = inv.line_ids.filtered(lambda l: l.debit == 0)[0].id
                    inv_vals.append({'inv_amount': inv.amount_total,
                                             'bill_ref':inv.ref,
                                             'name': inv.name,
                                             'inv_date': inv.invoice_date,
                                             'move_line_id': val_2,
                                             'date_due': inv.invoice_date_due,
                                             'inv_unallocated_amount': inv.amount_residual,

                                         })
                entries = self.env['account.move'].search([('has_reconciled_entries','=',False),
                                                           ('state', 'in', ['posted']),('move_type','=','entry'),('journal_id.type','=','general')])
                for inv in entries:
                    val_2 = 0
                    amnt = 0
                    if inv.line_ids.filtered(
                            lambda l: l.account_id.account_type == 'asset_receivable' and l.partner_id == partner.id):
                        if inv.line_ids.filtered(lambda l: l.credit == 0 and l.account_id.account_type == 'asset_receivable' and l.partner_id == partner.id):
                            val_2 = inv.line_ids.filtered(lambda l: l.credit == 0 and l.account_id.account_type == 'asset_receivable' and l.partner_id == partner.id)[0].id
                            amnt = inv.line_ids.filtered(lambda l: l.credit == 0 and l.account_id.account_type == 'asset_receivable' and l.partner_id == partner.id)[0].debit
                    elif inv.line_ids.filtered(
                            lambda l: l.account_id.account_type == 'liability_payable' and l.partner_id == partner.id):
                        if inv.line_ids.filtered(lambda l: l.debit == 0 and l.account_id.account_type == 'liability_payable' and l.partner_id == partner.id):
                            amnt = inv.line_ids.filtered(lambda l: l.debit == 0 and l.account_id.account_type == 'liability_payable' and l.partner_id == partner.id)[0].credit
                            val_2 = inv.line_ids.filtered(lambda l: l.debit == 0 and l.account_id.account_type == 'liability_payable' and l.partner_id == partner.id)[0].id
                    if val_2:
                        rec_ids = self.env['account.partial.reconcile'].search(['|',('credit_move_id','=',val_2),('debit_move_id','=',val_2)])
                        amt = abs(sum(rec_ids.mapped('amount')))
                        if (amnt-amt)>0:
                            inv_vals.append({'inv_amount': amnt,
                                             'name': inv.name,
                                             'inv_date': inv.invoice_date,
                                             'move_line_id': val_2,
                                             'date_due': inv.invoice_date_due,
                                             'inv_unallocated_amount':amnt-amt,
                                             })
            balance_amount=0
            debit = self.env['account.partial.reconcile'].search([('credit_move_id', '=', val_1)])

            if not debit:
                balance_amount=payment_amount
            else:
                balance_amount=payment_amount - amount_bal

            if balance_amount <=0:
                raise ValidationError(_("Already Allocated "))

            return {
                'name': 'Journals',
                'res_model': 'journal.allocation.wizard',
                'type': 'ir.actions.act_window',
                'context': {'default_partner_id': partner.id,
                #             'default_show_reference': show_reference,
                            'default_journal_id': def_id,
                #             'default_payment_type':data.payment_type,
                            'default_balnc_paymnt_amnt':balance_amount,
                            'default_journal_allocation_ids': payment_vals,
                            'default_invoice_allocation_ids': inv_vals,
                            'default_company_id': company,
                #
                #
                            },
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new'}
