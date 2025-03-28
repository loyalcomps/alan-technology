from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
from datetime import date, datetime, timedelta
from odoo.exceptions import Warning


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    def action_open_journal_allocation_wizard(self):
        self.ensure_one()
        payment_vals = []
        partner = False
        def_id = False
        payment_amount = 0
        payment_type = False
        company = False
        inv_vals = []
        amount_bal = 0
        val_1 = False

        for data in self:
            if data.journal_id.type not in ['general']:
                raise ValidationError(_('Only Miscellaneous Journals Can Be Selected'))
            if partner != data.partner_id.id and partner != False:
                raise ValidationError(_('Selected Journals are of different Partners'))
            for line in data.line_ids:
                print("\n\n")
                print(line.account_id.account_type)
            allocatable_lines = data.line_ids.filtered(
                lambda account:account.account_id.account_type in ['asset_receivable',
                                                                   'liability_payable','income_other'] and account.partner_id)
            if not allocatable_lines:
                raise ValidationError(_('Allocation cannot be done'))
            print("allocatable_lines::::::::", allocatable_lines)

            for line in allocatable_lines:
                partner = line.partner_id
                # payment_amount = line.credit if line.credit else line.debit
                if line.debit == 0:
                    payment_type = 'inbound'
                    payment_amount = line.credit
                    val_1 = line.id
                else:
                    payment_type = 'outbound'
                    payment_amount = line.debit
                    val_1 = line.id

                debit = self.env['account.partial.reconcile'].search(
                    ['|', ('credit_move_id', '=', val_1), ('debit_move_id', '=', val_1)])

                for val in debit:
                    if val.credit_amount_currency:
                        amount_bal += val.credit_amount_currency
                    else:
                        amount_bal += val.debit_amount_currency
                payment_vals.append({
                    'name':data.name,
                    'date':data.date,
                    'memo':line.name,
                    'move_line_id':line.id,
                    'account_type': line.account_id.name if line.account_id else None,
                    'amount':line.credit if line.credit != 0 else line.debit})

                def_id = data.id
                company = data.company_id.id

                invoice = self.env['account.move'].search(
                    [('partner_id', '=', partner.id), ('payment_state', 'in', ['partial', 'not_paid', 'in_payment']),
                     ('amount_residual', '!=', 0.0), ('state', 'in', ['posted'])])

                for inv in invoice:
                    val_2 = 0
                    if inv.move_type == 'out_invoice':
                        if inv.line_ids.filtered(lambda l:l.credit == 0):
                            val_2 = inv.line_ids.filtered(lambda l:l.credit == 0)[0].id
                    elif inv.move_type == 'in_invoice':
                        if inv.line_ids.filtered(lambda l:l.debit == 0):
                            val_2 = inv.line_ids.filtered(lambda l:l.debit == 0)[0].id
                    inv_vals.append({'inv_amount':inv.amount_total,
                                     'bill_ref':inv.ref,
                                     'name':inv.name,
                                     'inv_date':inv.invoice_date,
                                     'move_line_id':val_2,
                                     'date_due':inv.invoice_date_due,
                                     'inv_unallocated_amount':inv.amount_residual,

                                     })
                entries = self.env['account.move'].sudo().search(
                    [('state', 'in', ['posted']), ('move_type', '=', 'entry'), ('journal_id.type', '=', 'general')])
                for inv in entries:
                    val_2 = 0
                    amnt = 0
                    filtered_inv = inv.line_ids.filtered(
                        lambda l:l.account_id.account_type == 'asset_receivable' and l.partner_id.id == partner.id and l.id != line.id)
                    if filtered_inv:
                        for f_inv in filtered_inv:
                            if payment_type == 'inbound' and f_inv.credit:
                                val_2 = f_inv.id
                                amnt = f_inv.credit
                            else:
                                val_2 = f_inv.id
                                amnt = f_inv.debit

                        # if inv.line_ids.filtered(lambda l:l.credit == 0 and l.account_id.account_type == 'asset_receivable' and l.partner_id.id == partner.id):
                        #     val_2 = inv.line_ids.filtered(lambda l:l.credit == 0 and l.account_id.account_type=='asset_receivable' and l.partner_id.id == partner.id)[0].id
                        #     amnt = inv.line_ids.filtered(lambda l:l.credit == 0 and l.account_id.account_type=='asset_receivable' and l.partner_id.id == partner.id)[0].debit
                    elif inv.line_ids.filtered(
                            lambda l:l.account_id.account_type == 'liability_payable' and l.partner_id.id == partner.id):
                        if inv.line_ids.filtered(
                                lambda l:l.debit == 0 and l.account_id.account_type == 'liability_payable' and l.partner_id.id == partner.id):
                            amnt = inv.line_ids.filtered(lambda
                                                             l:l.debit == 0 and l.account_id.account_type == 'liability_payable' and l.partner_id.id == partner.id)[
                                0].credit
                            val_2 = inv.line_ids.filtered(lambda
                                                              l:l.debit == 0 and l.account_id.account_type == 'liability_payable' and l.partner_id.id == partner.id)[
                                0].id
                    if val_2:
                        rec_ids = self.env['account.partial.reconcile'].search(
                            ['|', ('credit_move_id', '=', val_2), ('debit_move_id', '=', val_2)])
                        amt = abs(sum(rec_ids.mapped('amount')))

                        if (amnt - amt) > 0:
                            inv_vals.append({'inv_amount':amnt,
                                             'name':inv.name,
                                             'inv_date':inv.invoice_date,
                                             'move_line_id':val_2,
                                             'date_due':inv.invoice_date_due,
                                             'inv_unallocated_amount':amnt - amt,
                                             })

            balance_amount = 0
            debit = self.env['account.partial.reconcile'].search([('credit_move_id', '=', val_1)])

            if not debit:
                balance_amount = payment_amount
            else:
                balance_amount = payment_amount - amount_bal

            if balance_amount <= 0:
                raise ValidationError(_("Already Allocated "))

            return {
                'name':'Journals',
                'res_model':'journal.allocation.wizard',
                'type':'ir.actions.act_window',
                'context':{'default_partner_id':partner.id,
                           'default_journal_id':data.id,
                           'default_payment_type':payment_type,
                           'default_balnc_paymnt_amnt':balance_amount,
                           'default_journal_allocation_ids':payment_vals,
                           'default_invoice_allocation_ids':inv_vals,
                           'default_company_id':company,
                           'default_show_parent_child': True
                           },
                'view_type':'form',
                'view_mode':'form',
                'target':'new'}
