# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountPdcDate(models.TransientModel):

    _name = 'account.pdc.date'
    _description = 'Account PDC Date'

    date = fields.Date(string='Account date')
    payment_ids = fields.Many2many('pdc.payment', 'pdc_payment_account_date', 'account_date_id', 'pdc_payment_id',
                                   'PDC Payment', domain=[('state', '=', 'deposited')])
    journal_id = fields.Many2one('account.journal', string='Journal', check_company=True, domain="[('company_id', '=', company_id), ('type', '=', 'bank')]")
    company_id = fields.Many2one('res.company', required=True, readonly=True)
    cleared_pdc_ids = fields.Many2many('pdc.payment', 'cleared_pdc_payment_account_date', 'account_date_id', 'cleared_pdc_payment_id')

    @api.model
    def default_get(self, fields):
        res = super(AccountPdcDate, self).default_get(fields)
        move_ids = self.env['pdc.payment'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'pdc.payment' else self.env['pdc.payment']

        if any(move.state != "deposited" for move in move_ids):
            raise UserError(_('You can only done deposited PDC.'))
        if 'company_id' in fields:
            res['company_id'] = move_ids.company_id.id or self.env.company.id
        if 'payment_ids' in fields:
            res['payment_ids'] = [(6, 0, move_ids.ids)]
        if 'journal_id' in fields:
            res['journal_id'] = (len(move_ids) > 1) and False or move_ids.journal_id.id
        if 'date' in fields:
            res['date'] = (len(move_ids) > 1) and False or move_ids.pdc_date
        return res

    def change_details(self):
        self.ensure_one()
        for payment in self.payment_ids:
            if self.date:
                payment.accounting_date = self.date
            if self.journal_id:
                payment.journal_id = self.journal_id
            payment.done_pdc_cheque()
            self.cleared_pdc_ids = [(4, payment.id)]
        # Create action.
        action = {
            'name': _('Cleared PDC Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'pdc.payment',
        }
        if len(self.cleared_pdc_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.cleared_pdc_ids.id,
                'context': {'default_payment_type': self.cleared_pdc_ids.payment_type},
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.cleared_pdc_ids.ids)],
            })
            if len(set(self.cleared_pdc_ids.mapped('payment_type'))) == 1:
                action['context'] = {'default_payment_type': self.cleared_pdc_ids.mapped('payment_type').pop()}
        return action