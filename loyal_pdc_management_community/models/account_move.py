# -*- coding: utf-8 -*-
import csv

from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = "account.move"

    pdc_payment_state = fields.Selection(
        [('not_received', 'Cheque Not Received'), ('pdc_received', 'Cheque Received'), ('pdc_done', 'Done')],
        string="PDC Status", store=True, readonly=True, copy=False,
        tracking=True, compute='_compute_pdc_payment_state')

    @api.depends('line_ids.matched_debit_ids.debit_move_id.move_id.pdc_payment_id.is_matched',
                 'line_ids.matched_credit_ids.credit_move_id.move_id.pdc_payment_id.is_matched',
                 'line_ids.pdc_payment_id.state')
    def _compute_pdc_payment_state(self):
        for record in self:
            reconciled_lines = record.line_ids.filtered(
                lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
            reconciled_amls = reconciled_lines.mapped('matched_debit_ids.debit_move_id') + \
                              reconciled_lines.mapped('matched_credit_ids.credit_move_id')
            if reconciled_amls.move_id.pdc_payment_id:
                if any(pdc.state in ('draft', 'registered', 'returned', 'deposited', 'bounced') for pdc in reconciled_amls.move_id.pdc_payment_id):
                    record.pdc_payment_state = 'pdc_received'
                elif all(pdc.state == 'done' for pdc in reconciled_amls.move_id.pdc_payment_id):
                    record.pdc_payment_state = 'pdc_done'
                else:
                    record.pdc_payment_state = 'not_received'
            else:
                record.pdc_payment_state = 'not_received'

    def action_register_pdc_payment(self):
        ''' Open the account.pdc.register wizard to pay the selected journal entries.
        :return: An action opening the account.pdc.register wizard.
        '''
        return {
            'name': _('Register PDC'),
            'res_model': 'account.pdc.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }