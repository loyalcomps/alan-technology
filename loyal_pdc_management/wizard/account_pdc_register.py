# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict

class AccountPdcRegister(models.TransientModel):
    _name = 'account.pdc.register'
    _description = 'Register PDC Payment'

    payment_date = fields.Date(string="Payment Date", required=True, default=fields.Date.context_today)
    pdc_date = fields.Date('PDC Date', help='Effective date of PDC', required=True)
    amount = fields.Monetary(currency_field='currency_id', store=True, required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, readonly=False,
                                  compute='_compute_currency_id',
                                  help="The payment's currency.")
    company_id = fields.Many2one('res.company', store=True, copy=False)
    partner_id = fields.Many2one('res.partner',
                                 string="Customer/Vendor", store=True, copy=False, ondelete='restrict')
    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
                                 compute='_compute_journal_id',
                                 domain="[('company_id', '=', company_id), ('type', '=', 'bank')]")
    cheque_reference = fields.Char(copy=False, string="Cheque No", required=1)
    communication = fields.Char(string="Memo", store=True, readonly=False)
    line_ids = fields.Many2many('account.move.line', 'account_pdc_register_move_line_rel', 'pdc_wizard_id', 'line_id',
                                string="Journal items", readonly=True, copy=False, )
    partner_bank_id = fields.Many2one('res.partner.bank', 'Agent Bank', domain="[('partner_id','=', partner_id)]")
    payment_type = fields.Selection([
        ('outbound', 'Send'),
        ('inbound', 'Receive'),
    ], string='Payment Type', copy=False)
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Vendor')], copy=False)
    company_currency_id = fields.Many2one('res.currency', string="Company Currency",
                                          related='company_id.currency_id')
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
                                             readonly=False, store=True,
                                             compute='_compute_payment_method_line_id',
                                             domain="[('code', '=', 'pdc')]",
                                             )
    pdc_register_attachment_ids = fields.Many2many(comodel_name="ir.attachment", relation="pdc_register_ir_attachment_relation",
                                          column1="pdc_register_id", column2="attachment_id", string="Attachments",
                                          required=True)

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_method_line_id(self):
        ''' Compute the 'payment_method_line_id' field.
        '''
        for pay in self:
            available_payment_method_line_ids = pay.journal_id._get_available_payment_method_lines(pay.payment_type)

            if available_payment_method_line_ids:
                payment_method_lines = available_payment_method_line_ids.filtered(lambda l: l.code == 'pdc')
                pay.payment_method_line_id = payment_method_lines[0]._origin if payment_method_lines else False
            else:
                pay.payment_method_line_id = False

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = wizard.journal_id.currency_id or wizard.company_id.currency_id

    @api.depends('company_id')
    def _compute_journal_id(self):
        for wizard in self:
            wizard.journal_id = self.env['account.journal'].search([
                ('type', '=', 'bank'),
                ('company_id', '=', wizard.company_id.id),
            ], limit=1)

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)
        if self._context.get('active_model') == 'account.move':
            move = self.env['account.move'].browse(self._context.get('active_ids', []))
        if 'line_ids' in fields_list and 'line_ids' not in res:

            # Retrieve moves to pay from the context.

            if self._context.get('active_model') == 'account.move':
                move = self.env['account.move'].browse(self._context.get('active_ids', []))
                lines = move.line_ids
            else:
                raise UserError(_(
                    "The register payment wizard should only be called on account.move records."
                ))

            if 'journal_id' in res and not self.env['account.journal'].browse(res['journal_id']) \
                    .filtered_domain([('company_id', '=', lines.company_id.id), ('type', '=', 'bank')]):
                # default can be inherited from the list view, should be computed instead
                del res['journal_id']

            # Keep lines having a residual amount to pay.
            available_lines = self.env['account.move.line']
            for line in lines:
                if line.move_id.state != 'posted':
                    raise UserError(_("You can only register payment for posted journal entries."))

                if line.account_type not in ('asset_receivable', 'liability_payable'):
                    continue
                if line.currency_id:
                    if line.currency_id.is_zero(line.amount_residual_currency):
                        continue
                else:
                    if line.company_currency_id.is_zero(line.amount_residual):
                        continue
                available_lines |= line

            # Check.
            if not available_lines:
                raise UserError(
                    _("You can't register a payment because there is nothing left to pay on the selected journal items."))
            if len(lines.company_id) > 1:
                raise UserError(_("You can't create payments for entries belonging to different companies."))
            if len(lines.partner_id) > 1:
                raise UserError(_("You can't create payments for entries belonging to different partners."))
            if len(lines.currency_id) > 1:
                raise UserError(_("In order to pay multiple invoices at once, they must use the same currency."))
            if len(set(available_lines.mapped('account_type'))) > 1:
                raise UserError(
                    _("You can't register payments for journal items being either all inbound, either all outbound."))

            res['line_ids'] = [(6, 0, available_lines.ids)]
        total_amount = sum(inv.amount_residual for inv in move)
        communication = ', '.join([ref for ref in move.filtered(lambda l:l.payment_state in ('not_paid', 'partial')).mapped('name') if ref])
        if 'amount' in fields_list:
            res['amount'] = abs(total_amount)
        if 'company_id' in fields_list:
            res['company_id'] = move[0].company_id.id
        if 'partner_id' in fields_list:
            res['partner_id'] = move[0].partner_id.id
        if 'communication' in fields_list:
            res['communication'] = communication
        if 'payment_type' in fields_list:
            res['payment_type'] = 'inbound' if move[0].move_type == 'out_invoice' else 'outbound'
        if 'partner_type' in fields_list:
            res['partner_type'] = 'customer' if move[0].move_type == 'out_invoice' else 'supplier'
        return res

    def _create_payment_vals_from_wizard(self):
        values = []
        for record in self.pdc_register_attachment_ids:
            values.append((0, 0, {
                'name': record.name,
                'type': record.type,
                'datas': record.datas,
            }))
        payment_vals = {
            'date': self.payment_date,
            'pdc_date': self.pdc_date,
            'accounting_date': self.pdc_date,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'ref': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'agent_bank': self.partner_bank_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'cheque_reference': self.cheque_reference,
            'pdc_attachment_ids': values,
        }
        return payment_vals

    def _init_payments(self, to_process):
        """ Create the payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_get_batches').
        """

        payments = self.env['pdc.payment'].create([x['create_vals'] for x in to_process])
        for payment in payments:
            for attachment in payment.pdc_attachment_ids:
                attachment.res_model = 'pdc.payment'
                attachment.res_id = payment.id

        for payment, vals in zip(payments, to_process):
            vals['payment'] = payment
        return payments

    def _post_payments(self, to_process):
        """ Post the newly created payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_get_batches').
        """
        payments = self.env['pdc.payment']
        for vals in to_process:
            payments |= vals['payment']
        payments.register_pdc_cheque()

    def _reconcile_payments(self, to_process):
        """ Reconcile the payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_get_batches').
        """
        domain = [
            ('parent_state', '=', 'posted'),
            ('account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('reconciled', '=', False),
        ]
        for vals in to_process:
            payment_lines = vals['payment'].move_ids.line_ids.filtered_domain(domain)
            lines = vals['to_reconcile']

            for account in payment_lines.account_id:
                (payment_lines + lines) \
                    .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
                    .reconcile()

    @api.model
    def _get_line_batch_key(self, line):
        ''' Turn the line passed as parameter to a dictionary defining on which way the lines
        will be grouped together.
        :return: A python dictionary.
        '''
        move = line.move_id

        partner_bank_account = self.env['res.partner.bank']
        if move.is_invoice(include_receipts=True):
            partner_bank_account = move.partner_bank_id._origin

        return {
            'partner_id': line.partner_id.id,
            'account_id': line.account_id.id,
            'currency_id': line.currency_id.id,
            'partner_bank_id': partner_bank_account.id,
            'partner_type': 'customer' if line.account_type == 'asset_receivable' else 'supplier',
        }

    def _get_batches(self):
        ''' Group the account.move.line linked to the wizard together.
        Lines are grouped if they share 'partner_id','account_id','currency_id' & 'partner_type' and if
        0 or 1 partner_bank_id can be determined for the group.
        :return: A list of batches, each one containing:
            * payment_values:   A dictionary of payment values.
            * moves:        An account.move recordset.
        '''
        self.ensure_one()

        lines = self.line_ids._origin

        if len(lines.company_id) > 1:
            raise UserError(_("You can't create payments for entries belonging to different companies."))
        if not lines:
            raise UserError(
                _("You can't open the register payment wizard without at least one receivable/payable line."))

        batches = defaultdict(lambda: {'lines': self.env['account.move.line']})
        for line in lines:
            batch_key = self._get_line_batch_key(line)
            serialized_key = '-'.join(str(v) for v in batch_key.values())
            vals = batches[serialized_key]
            vals['payment_values'] = batch_key
            vals['lines'] += line

        # Compute 'payment_type'.
        for vals in batches.values():
            lines = vals['lines']
            balance = sum(lines.mapped('balance'))
            vals['payment_values']['payment_type'] = 'inbound' if balance > 0.0 else 'outbound'

        return list(batches.values())

    def _create_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        to_process = []
        payment_vals = self._create_payment_vals_from_wizard()
        to_process.append({
            'create_vals': payment_vals,
            'to_reconcile': batches[0]['lines'],
            'batch': batches[0],
        })

        payments = self._init_payments(to_process)
        self._post_payments(to_process)
        self._reconcile_payments(to_process)
        return payments

    def action_create_payments(self):
        payments = self._create_payments()

        if self._context.get('dont_redirect_to_payments'):
            return True

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'pdc.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action