# -*- coding: utf-8 -*-

import csv
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PdcPayment(models.Model):
    _name = "pdc.payment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "PDC Payments"
    _order = "date desc, name desc"
    _check_company_auto = True

    @api.model
    def _get_default_journal(self):
        company_id = self._context.get('default_company_id', self.env.company.id)
        domain = [('company_id', '=', company_id), ('type', '=', 'bank')]

        journal = None
        if self._context.get('default_currency_id'):
            currency_domain = domain + [('currency_id', '=', self._context['default_currency_id'])]
            journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)
        return journal

    name = fields.Char(string='Name', copy=False, compute='_compute_name', readonly=False, store=True, index=True,
                       tracking=True)
    reconciled_move_ids = fields.Many2many('account.move', string="Reconciled Moves",
                                              compute='_compute_stat_buttons_from_reconciliation',
                                              help="Invoices whose journal items have been reconciled with these payments.")
    reconciled_move_count = fields.Integer(string="# Reconciled Moves",
                                               compute="_compute_stat_buttons_from_reconciliation")
    move_ids = fields.One2many(
        comodel_name='account.move',
        string='Journal Entry', readonly=True, inverse_name='pdc_payment_id',
        copy=False, check_company=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 check_company=True, domain="[('company_id', '=', company_id), ('type', '=', 'bank')]",
                                 default=_get_default_journal)
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, readonly=False,
                                  compute='_compute_currency_id',
                                  help="The payment's currency.")
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer",
        store=True, readonly=False, ondelete='restrict',
        domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        tracking=True, required=True,
        check_company=True)
    amount = fields.Monetary(currency_field='currency_id', string="Payment Amount", required=1)
    cheque_reference = fields.Char(copy=False, string="Cheque No", required=1)
    pdc_date = fields.Date('PDC Date', help='Effective date of PDC', copy=False, default=False, required=True)
    accounting_date = fields.Date('Accounting Date', help='Posted PDC Date')
    agent_bank = fields.Many2one('res.partner.bank', 'Agent Bank', domain="[('partner_id','=', partner_id)]")
    date = fields.Date(string='Date', required=True, index=True, readonly=True, states={'draft': [('readonly', False)]},
                       copy=False, tracking=True, default=fields.Date.context_today)
    ref = fields.Char(string='Reference', copy=False, tracking=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('registered', 'Registered'),
        ('returned', 'Returned'),
        ('deposited', 'Deposited'),
        ('bounced', 'Bounced'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', required=True, readonly=True, copy=False, tracking=True, default='draft')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', store=True, readonly=True,
                                 compute='_compute_company_id')
    user_id = fields.Many2one('res.users', copy=False, tracking=True, string='User', default=lambda self: self.env.user)
    payment_type = fields.Selection([
        ('outbound', 'Send'),
        ('inbound', 'Receive'),
    ], string='Payment Type', default='inbound', required=True, tracking=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], default='customer', tracking=True, required=True)

    # == Payment methods fields ==
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
                                             readonly=False, store=True, copy=False,
                                             compute='_compute_payment_method_line_id',
                                             domain="[('id', 'in', available_payment_method_line_ids),('code', '=', 'pdc')]",
                                             help="Manual: Pay or Get paid by any method outside of Odoo.\n"
                                                  "Payment Providers: Each payment provider has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
                                                  "Check: Pay bills by check and print it from Odoo.\n"
                                                  "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
                                                  "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
                                                  "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
    available_payment_method_line_ids = fields.Many2many('account.payment.method.line',
                                                         compute='_compute_payment_method_line_fields')
    payment_method_id = fields.Many2one(
        related='payment_method_line_id.payment_method_id',
        string="Method",
        tracking=True,
        store=True
    )
    available_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        compute='_compute_available_journal_ids'
    )

    # payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
    #                                          readonly=False, store=True, copy=False,
    #                                          compute='_compute_payment_method_line_id',
    #                                          domain="[('code', '=', 'pdc')]")
    is_reconciled = fields.Boolean(string="Is Reconciled", store=True,
                                   compute='_compute_reconciliation_status',
                                   help="Technical field indicating if the payment is already reconciled.")
    is_matched = fields.Boolean(string="Is Matched With a Bank Statement", store=True,
                                compute='_compute_reconciliation_status',
                                help="Technical field indicating if the payment has been matched with a statement line.")
    pdc_attachment_ids = fields.Many2many(comodel_name="ir.attachment", relation="pdc_ir_attachment_relation",
                                          column1="pdc_id", column2="attachment_id", string="Attachments",
                                          required=True, copy=False)
    attachment_count = fields.Integer('Attachment Count', compute='_compute_total_attachment', store=True)

    @api.depends('pdc_attachment_ids')
    def _compute_total_attachment(self):

        for record in self:
            record.attachment_count = record.pdc_attachment_ids.ids and len(record.pdc_attachment_ids.ids) or 0

    # @api.constrains('pdc_attachment_ids', 'attachment_count')
    # def check_attachments(self):
    #     for record in self:
    #         if len(record.pdc_attachment_ids.ids) <= 0 or record.attachment_count <= 0:
    #             raise UserError(_("Please upload one attachment"))

    @api.onchange('payment_type')
    def change_partner_type(self):
        for record in self:
            if record.payment_type == 'inbound':
                record.partner_type = 'customer'
            else:
                record.partner_type = 'supplier'

    @api.onchange('pdc_date')
    def get_accounting_date(self):
        for record in self:
            record.accounting_date = record.pdc_date

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for pay in self:
            pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id

    @api.depends('journal_id')
    def _compute_company_id(self):
        for move in self:
            move.company_id = move.journal_id.company_id or move.company_id or self.env.company

    @api.depends('move_ids.line_ids.matched_debit_ids', 'move_ids.line_ids.matched_credit_ids')
    def _compute_stat_buttons_from_reconciliation(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
        stored_payments = self.filtered('id')
        if not stored_payments:
            self.reconciled_move_ids = False
            self.reconciled_move_count = 0
            return

        self.env['account.move'].flush()
        self.env['account.move.line'].flush()
        self.env['account.partial.reconcile'].flush()

        self._cr.execute('''
                SELECT
                    payment.id,
                    ARRAY_AGG(DISTINCT invoice.id) AS invoice_ids,
                    invoice.move_type
                FROM pdc_payment payment
                JOIN account_move move ON move.pdc_payment_id = payment.id
                JOIN account_move_line line ON line.move_id = move.id
                JOIN account_partial_reconcile part ON
                    part.debit_move_id = line.id
                    OR
                    part.credit_move_id = line.id
                JOIN account_move_line counterpart_line ON
                    part.debit_move_id = counterpart_line.id
                    OR
                    part.credit_move_id = counterpart_line.id
                JOIN account_move invoice ON invoice.id = counterpart_line.move_id
                JOIN account_account account ON account.id = line.account_id
                WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                    AND payment.id IN %(payment_ids)s
                    AND line.id != counterpart_line.id
                    AND invoice.move_type in ('out_invoice','in_invoice')
                GROUP BY payment.id, invoice.move_type
            ''', {
            'payment_ids': tuple(stored_payments.ids)
        })
        query_res = self._cr.dictfetchall()
        self.reconciled_move_ids = self.reconciled_move_count = False
        for res in query_res:
            pay = self.browse(res['id'])
            pay.reconciled_move_ids += self.env['account.move'].browse(res.get('invoice_ids', []))
            pay.reconciled_move_count = len(res.get('invoice_ids', []))

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('pdc.payment') or _('New')
        return super(PdcPayment, self).create(vals)

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_method_line_id(self):
        print("------------computeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
        ''' Compute the 'payment_method_line_id' field.
        '''
        for pay in self:
            available_payment_method_line_ids = pay.journal_id._get_available_payment_method_lines(pay.payment_type)
            print("---------avaiablr",available_payment_method_line_ids)

            if available_payment_method_line_ids:

                payment_method_lines = available_payment_method_line_ids.filtered(lambda l: l.code == 'pdc')
                print("-------payment method ;inesssssssssss",payment_method_lines)


                pay.payment_method_line_id = payment_method_lines[0]._origin if payment_method_lines else False
            else:
                pay.payment_method_line_id = False

    @api.depends('payment_type', 'journal_id', 'currency_id')
    def _compute_payment_method_line_fields(self):
        for pay in self:
            pay.available_payment_method_line_ids = pay.journal_id._get_available_payment_method_lines(pay.payment_type)
            to_exclude = pay._get_payment_method_codes_to_exclude()
            if to_exclude:
                pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(
                    lambda x: x.code not in to_exclude)

    def _get_payment_method_codes_to_exclude(self):
        # can be overriden to exclude payment methods based on the payment characteristics
        self.ensure_one()
        return []

    def _seek_for_lines(self):
        ''' Helper used to dispatch the journal items between:
        - The lines using the temporary liquidity account.
        - The lines using the counterpart account.
        - The lines being the write-off lines.
        :return: (liquidity_lines, counterpart_lines, writeoff_lines)
        '''
        self.ensure_one()

        liquidity_lines = self.env['account.move.line']
        counterpart_lines = self.env['account.move.line']
        writeoff_lines = self.env['account.move.line']

        for line in self.move_ids.line_ids:
            if line.account_id in self._get_valid_liquidity_accounts():
                liquidity_lines += line
            elif line.account_id.account_type in (
            'asset_receivable', 'liability_payable') or line.partner_id == line.company_id.partner_id:
                counterpart_lines += line
            else:
                writeoff_lines += line

        return liquidity_lines, counterpart_lines, writeoff_lines

    def _get_valid_liquidity_accounts(self):
        return (
            self.journal_id.default_account_id,
            self.payment_method_line_id.payment_account_id,
            self.journal_id.company_id.pdc_customer_account,
            self.journal_id.company_id.pdc_supplier_account,
        )

    @api.depends('move_ids.line_ids.amount_residual', 'move_ids.line_ids.amount_residual_currency',
                 'move_ids.line_ids.account_id')
    def _compute_reconciliation_status(self):
        ''' Compute the field indicating if the payments are already reconciled with something.
        This field is used for display purpose (e.g. display the 'reconcile' button redirecting to the reconciliation
        widget).
        '''
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            if not pay.currency_id or not pay.id:
                pay.is_reconciled = False
                pay.is_matched = False
            elif pay.currency_id.is_zero(pay.amount):
                pay.is_reconciled = True
                pay.is_matched = True
            else:
                residual_field = 'amount_residual' if pay.currency_id == pay.company_id.currency_id else 'amount_residual_currency'
                if pay.journal_id.default_account_id and pay.journal_id.default_account_id in liquidity_lines.account_id:
                    # Allow user managing payments without any statement lines by using the bank account directly.
                    # In that case, the user manages transactions only using the register payment wizard.
                    pay.is_matched = True
                else:
                    pay.is_matched = pay.currency_id.is_zero(sum(liquidity_lines.mapped(residual_field)))

                reconcile_lines = (counterpart_lines + writeoff_lines).filtered(lambda line: line.account_id.reconcile)
                pay.is_reconciled = pay.currency_id.is_zero(sum(reconcile_lines.mapped(residual_field)))

    def button_open_journal_entry(self):
        ''' Redirect the user to this payment journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.move_ids.ids)],
        }

    def register_pdc_cheque(self):
        for record in self:
            if record.state == 'draft':
                if record.payment_type == 'inbound':
                    line_ids = [
                        (
                            0,
                            0,
                            {
                                "debit": record.amount,
                                "credit": 0.0,
                                "account_id": record.payment_method_line_id.payment_account_id.id if record.payment_method_line_id.payment_account_id.id else record.company_id.pdc_customer_account.id,
                                "partner_id": record.partner_id.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": record.amount,
                                "account_id": record.partner_id.property_account_receivable_id.id,
                                "partner_id": record.partner_id.id,
                            },
                        ),
                    ]
                else:
                    line_ids = [
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": record.amount,
                                "account_id": record.payment_method_line_id.payment_account_id.id if record.payment_method_line_id.payment_account_id.id else record.company_id.pdc_supplier_account.id,
                                "partner_id": record.partner_id.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": record.amount,
                                "credit": 0.0,
                                "account_id": record.partner_id.property_account_payable_id.id,
                                "partner_id": record.partner_id.id,
                            },
                        ),
                    ]
                move_vals = {
                    "journal_id": record.journal_id.id,
                    "date": record.date,
                    "ref": record.name,
                    "pdc_payment_id": record.id,
                    "line_ids": line_ids,
                }
                move = self.env["account.move"].create(move_vals)
                move.action_post()
                record.move_ids = [(4, move.id)]
                record.state = 'registered'

    def return_pdc_cheque(self):
        for record in self:
            record.state = 'returned'

    def register_bounced_pdc_cheque(self):
        for record in self:
            record.state = 'registered'

    def cancel_pdc_cheque(self):
        for record in self:
            if record.move_ids:
                for move in record.move_ids:
                    reverse_move_vals = {
                        "move_ids": [(4, move.id)],
                        "reason": "Cancelled" + record.name,
                        "refund_method": 'cancel',
                        'company_id': move.company_id.id,
                        'journal_id': move.journal_id.id,
                    }
                    reverse_move = self.env["account.move.reversal"].create(reverse_move_vals)
                    res = reverse_move.reverse_moves()
                    for new_move in reverse_move.new_move_ids:
                        new_move.pdc_payment_id = record.id
                    record.move_ids = [(4, id in reverse_move.new_move_ids.ids)]
            record.state = 'cancel'

    def deposit_pdc_cheque(self):
        for record in self:
            record.state = 'deposited'

    def bounce_pdc_cheque(self):
        for record in self:
            record.state = 'bounced'

    def done_pdc_cheque(self):
        for record in self:
            if record.payment_type == 'inbound':
                line_ids = [
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": record.amount,
                            "account_id": record.payment_method_line_id.payment_account_id.id if record.payment_method_line_id.payment_account_id.id else record.company_id.pdc_customer_account.id,
                            "partner_id": record.partner_id.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": record.amount,
                            "credit": 0.0,
                            "account_id": record.journal_id.default_account_id.id,
                            "partner_id": record.partner_id.id,
                        },
                    ),
                ]
            else:
                line_ids = [
                    (
                        0,
                        0,
                        {
                            "debit": record.amount,
                            "credit": 0.0,
                            "account_id": record.payment_method_line_id.payment_account_id.id if record.payment_method_line_id.payment_account_id.id else record.company_id.pdc_supplier_account.id,
                            "partner_id": record.partner_id.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": record.amount,
                            "account_id": record.journal_id.default_account_id.id,
                            "partner_id": record.partner_id.id,
                        },
                    ),
                ]
            move_vals = {
                "journal_id": record.journal_id.id,
                "date": record.accounting_date,
                "ref": record.name,
                "pdc_payment_id": record.id,
                "line_ids": line_ids,
            }
            move = self.env["account.move"].create(move_vals)
            move.action_post()
            record.move_ids = [(4, move.id)]
            record.state = 'done'

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_(
                    "Payments only in draft state can be deleted."))
        res = super().unlink()
        return res

    def button_open_invoices(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        name = "Paid Invoices" if self.payment_type == 'inbound' else 'Paid Bills'

        action = {
            'name': _(name),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.reconciled_move_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reconciled_move_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.reconciled_move_ids.ids)],
            })
        return action

    def print_csv(self):
        lines = [(['Name', 'Partner', 'Bank', 'PDC Date', 'Amount', 'Cheque No', 'Status'])]
        for rec in self:
            lines.append(([rec.name, rec.partner_id.name, rec.journal_id.name,
                           rec.pdc_date, rec.amount, rec.cheque_reference, rec.state]))
        with open('pdc_payment.csv', 'w') as file:
            a = csv.writer(file, delimiter=',')
            data_lines = lines
            a.writerows(data_lines)
        with open('pdc_payment.csv', 'r', encoding="utf-8") as f2:
            # file encode and store in a variable ‘data’
            data = str.encode(f2.read(), 'utf-8')
        pdc_report = self.env['pdc.report.wizard'].create({
            'csv_data': base64.encodestring(data),
            'filename': 'pdc_payment.csv'
        })
        return {'type': 'ir.actions.act_url', 'url': "web/content/?model=pdc.report.wizard&id=" + str(
            pdc_report.id) + "&filename=pdc_payment.csv&field=csv_data&download=true&filename=" + pdc_report.filename,
                'target': 'self', }


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['pdc'] = {
            'mode': 'multi',
            'domain': [('type', '=', 'bank')],
        }
        return res


class AccountMove(models.Model):
    _inherit = "account.move"

    pdc_payment_id = fields.Many2one(comodel_name='pdc.payment', ondelete="cascade")

    def _get_reconciled_payments(self):
        """Helper used to retrieve the reconciled payments on this journal entry"""
        reconciled_lines = self.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        reconciled_amls = reconciled_lines.mapped('matched_debit_ids.debit_move_id') + \
                          reconciled_lines.mapped('matched_credit_ids.credit_move_id')
        if reconciled_amls.move_id.pdc_payment_id:
            return reconciled_amls.move_id.pdc_payment_id
        else:
            return super(AccountMove, self)._get_reconciled_payments()

    @api.depends('line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
                 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
                 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'line_ids.matched_debit_ids.debit_move_id.move_id.pdc_payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.pdc_payment_id.is_matched',
        'line_ids.pdc_payment_id.state')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    pdc_payment_id = fields.Many2one('pdc.payment', index=True, store=True,
                                     string="Originator PDC Payment",
                                     related='move_id.pdc_payment_id',
                                     help="The payment that created this entry")