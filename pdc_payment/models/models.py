# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    bank_cheque = fields.Boolean(default=False, string='Bank Cheque', copy=False)
    journal_type = fields.Selection(related='journal_id.type', string='Journal Type', store=True)
    bank_id = fields.Many2one('res.bank', string='Bank', copy=False)
    cheque_collection_date = fields.Date(string='Collection Date', copy=False)
    cheque_returned = fields.Char(string='Returned', copy=False)
    cheque_reference = fields.Char(copy=False)
    effective_date = fields.Date(string='Cheque Due Date')
    sub_cheque_status = fields.Selection([('in_cheque_box', 'In Cheque Box'), ('issued', 'Issued'), ('draft', 'Draft'),
                                          ('refused', 'Refused'), ('collected', 'Collected'),('deposited', 'Deposited'),
                                          ('cancelled', 'Cancelled')],
                                         string='Sub Cheque Status', default='draft', copy=False)
    not_a_contact = fields.Boolean(default=False, string="Not a Vendor/Customer", copy=False)
    employee_payment_line_ids = fields.One2many('employee.payment.order.info', 'payment_id', copy=False, readonly=True,
                                                string='Payment Order Info',
                                                states={'draft': [('readonly', False)]})
    pdc_move_ids = fields.One2many(
        comodel_name='account.move',
        string='Journal Entry', readonly=True, inverse_name='pdc_payment_id',
        copy=False, check_company=True)

    branch_cheque = fields.Boolean(default=False, string='Branch Cheque', copy=False)
    branch_account_id = fields.Many2one('account.account','Branch Account')
    ho_account_id = fields.Many2one('account.account','HO Account')
    bank_journal_id = fields.Many2one('account.journal','Bank Journal',domain="[('type', '=', 'bank')]")

    # @api.depends('payment_type', 'journal_id', 'currency_id')
    # def _compute_payment_method_line_fields(self):
    #     for pay in self:
    #         if pay.branch_cheque and pay.branch_journal_id:
    #             pay.available_payment_method_line_ids = pay.branch_journal_id._get_available_payment_method_lines(pay.payment_type)
    #             to_exclude = pay._get_payment_method_codes_to_exclude()
    #             if to_exclude:
    #                 pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(
    #                     lambda x: x.code not in to_exclude)
    #         else:
    #             pay.available_payment_method_line_ids = pay.branch_journal_id._get_available_payment_method_lines(
    #                 pay.payment_type)
    #             to_exclude = pay._get_payment_method_codes_to_exclude()
    #             if to_exclude:
    #                 pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(
    #                     lambda x: x.code not in to_exclude)


    def action_draft(self):
        super().action_draft()
        if self.bank_cheque:
            self.sub_cheque_status = 'draft'
    def action_deposit_pdc(self):
        if self.bank_cheque:
            self.sub_cheque_status = 'deposited'

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        for pay in payments:
            if pay.bank_cheque and not pay.is_internal_transfer:
                pay.move_id.write(
                    {
                        'pdc_payment_id': pay.id,
                    }
                )
            pay.pdc_move_ids = [(4, pay.move_id.id)]
        return payments

    # @api.depends('payment_type', 'journal_id', 'bank_cheque', 'is_internal_transfer')
    # def _compute_payment_method_line_fields(self):
    #     for pay in self:
    #         pay.available_payment_method_line_ids = pay.journal_id._get_available_payment_method_lines(pay.payment_type)
    #         to_exclude = pay._get_payment_method_codes_to_exclude()
    #         if to_exclude:
    #             pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda x: x.code not in to_exclude)
    #         if pay.bank_cheque and not pay.is_internal_transfer:
    #             pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda x: x.code == 'pdc')
    #         else:
    #             pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda x: x.code != 'pdc')

            # if pay.payment_method_line_id.id not in pay.available_payment_method_line_ids.ids:
            #     # In some cases, we could be linked to a payment method line that has been unlinked from the journal.
            #     # In such cases, we want to show it on the payment.
            #     pay.hide_payment_method_line = False
            # else:
            #     pay.hide_payment_method_line = len(pay.available_payment_method_line_ids) == 1 and pay.available_payment_method_line_ids.code == 'manual'

    @api.onchange('is_internal_transfer')
    def _onchange_not_a_contact(self):
        if self.is_internal_transfer:
            self.not_a_contact = False

    @api.constrains('employee_payment_line_ids', 'amount', 'not_a_contact')
    def check_employee_total(self):
        for record in self:
            if record.not_a_contact:
                if sum(line.total for line in record.employee_payment_line_ids) != record.amount:
                    raise UserError(_("Sum of total value provided in payment order info should be payment amount"))

    @api.depends('employee_payment_line_ids', 'employee_payment_line_ids.account_id', 'company_id')
    def _compute_analytic_distribution(self):
        for expense in self.employee_payment_line_ids:
            distribution = self.env['account.analytic.distribution.model']._get_distribution({
                'account_prefix': expense.account_id.code,
                'company_id': self.company_id.id,
            })
            expense.analytic_distribution = distribution or expense.analytic_distribution

    @api.model
    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional list of dictionaries to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        if self.not_a_contact:
            write_off_line_vals = write_off_line_vals or {}

            if not self.outstanding_account_id:
                raise UserError(_(
                    "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
                    self.payment_method_line_id.name, self.journal_id.display_name))

            # Compute amounts.
            write_off_line_vals_list = write_off_line_vals or []
            write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
            write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)

            if self.payment_type == 'inbound':
                # Receive money.
                liquidity_amount_currency = self.amount
            elif self.payment_type == 'outbound':
                # Send money.
                liquidity_amount_currency = -self.amount
            else:
                liquidity_amount_currency = 0.0

            liquidity_balance = self.currency_id._convert(
                liquidity_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
            counterpart_balance = -liquidity_balance - write_off_balance
            currency_id = self.currency_id.id

            # Compute a default label to set on the journal items.
            liquidity_line_name = ''.join(x[1] for x in self._get_liquidity_aml_display_name_list())
            counterpart_line_name = ''.join(x[1] for x in self._get_counterpart_aml_display_name_list())
            analytic_distribution = self.employee_payment_line_ids.analytic_distribution

            line_vals_list = [
                # Liquidity line.
                {
                    'name': liquidity_line_name,
                    'date_maturity': self.date,
                    'amount_currency': liquidity_amount_currency,
                    'currency_id': currency_id,
                    'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                    'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.outstanding_account_id.id,
                    'analytic_distribution': analytic_distribution,
                }]
            for record in self.employee_payment_line_ids:
                if self.payment_type == 'inbound':
                    # Receive money.
                    liquidity_amount_currency_emp = record.total
                elif self.payment_type == 'outbound':
                    # Send money.
                    liquidity_amount_currency_emp = -record.total
                    write_off_amount_currency *= -1
                else:
                    liquidity_amount_currency_emp = write_off_amount_currency = 0.0
                liquidity_balance_emp = self.currency_id._convert(
                    liquidity_amount_currency_emp,
                    self.company_id.currency_id,
                    self.company_id,
                    self.date,
                )
                counterpart_amount_currency_emp = -liquidity_amount_currency_emp - write_off_amount_currency
                counterpart_balance_emp = -liquidity_balance_emp - write_off_balance
                analytic_distribution = record.analytic_distribution
                line_vals_list.append(
                    {
                        'name': counterpart_line_name,
                        'date_maturity': self.date,
                        'amount_currency': counterpart_amount_currency_emp,
                        'currency_id': currency_id,
                        'debit': counterpart_balance_emp if counterpart_balance_emp > 0.0 else 0.0,
                        'credit': -counterpart_balance_emp if counterpart_balance_emp < 0.0 else 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': record.account_id.id,
                        'tax_ids': [(4, line.id) for line in record.tax_ids],
                        'not_a_contact': True,
                        'analytic_distribution': analytic_distribution,
                    }
                )
            return line_vals_list + write_off_line_vals_list
        else:
            return super()._prepare_move_line_default_vals(write_off_line_vals)

    # def _prepare_move_line_default_vals(self, write_off_line_vals=None):
    #     ''' Prepare the dictionary to create the default account.move.lines for the current payment.
    #     :param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
    #         * amount:       The amount to be added to the counterpart amount.
    #         * name:         The label to set on the line.
    #         * account_id:   The account on which create the write-off.
    #     :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
    #     '''
    #     self.ensure_one()
    #     if self.not_a_contact:
    #         write_off_line_vals = write_off_line_vals or {}
    #
    #         if not self.outstanding_account_id:
    #             raise UserError(_(
    #                 "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
    #                 self.payment_method_line_id.name, self.journal_id.display_name))
    #
    #         # Compute amounts.
    #         write_off_line_vals_list = write_off_line_vals or []
    #         write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
    #         write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)
    #
    #         if self.payment_type == 'inbound':
    #             # Receive money.
    #             liquidity_amount_currency = self.amount
    #         elif self.payment_type == 'outbound':
    #             # Send money.
    #             liquidity_amount_currency = -self.amount
    #             write_off_amount_currency *= -1
    #         else:
    #             liquidity_amount_currency = write_off_amount_currency = 0.0
    #
    #         write_off_balance = self.currency_id._convert(
    #             write_off_amount_currency,
    #             self.company_id.currency_id,
    #             self.company_id,
    #             self.date,
    #         )
    #         liquidity_balance = self.currency_id._convert(
    #             liquidity_amount_currency,
    #             self.company_id.currency_id,
    #             self.company_id,
    #             self.date,
    #         )
    #         currency_id = self.currency_id.id
    #
    #         liquidity_line_name = self.payment_reference
    #
    #         # Compute a default label to set on the journal items.
    #
    #         payment_display_name = self._prepare_payment_display_name()
    #
    #         default_line_name = self.env['account.move.line']._get_default_line_name(
    #             payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
    #             self.amount,
    #             self.currency_id,
    #             self.date,
    #             partner=self.partner_id,
    #         )
    #
    #         line_vals_list = [
    #             # Liquidity line.
    #             {
    #                 'name': liquidity_line_name or default_line_name,
    #                 'date_maturity': self.date,
    #                 'amount_currency': liquidity_amount_currency,
    #                 'currency_id': currency_id,
    #                 'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
    #                 'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
    #                 'partner_id': self.partner_id.id,
    #                 'account_id': self.outstanding_account_id.id,
    #             },
    #         ]
    #         for record in self.employee_payment_line_ids:
    #             if self.payment_type == 'inbound':
    #                 # Receive money.
    #                 liquidity_amount_currency_emp = record.total
    #             elif self.payment_type == 'outbound':
    #                 # Send money.
    #                 liquidity_amount_currency_emp = -record.total
    #                 write_off_amount_currency *= -1
    #             else:
    #                 liquidity_amount_currency_emp = write_off_amount_currency = 0.0
    #             liquidity_balance_emp = self.currency_id._convert(
    #                 liquidity_amount_currency_emp,
    #                 self.company_id.currency_id,
    #                 self.company_id,
    #                 self.date,
    #             )
    #             counterpart_amount_currency_emp = -liquidity_amount_currency_emp - write_off_amount_currency
    #             counterpart_balance_emp = -liquidity_balance_emp - write_off_balance
    #             line_vals_list.append(
    #                 {
    #                     'name': record.memo or default_line_name,
    #                     'date_maturity': self.date,
    #                     'amount_currency': counterpart_amount_currency_emp,
    #                     'currency_id': currency_id,
    #                     'debit': counterpart_balance_emp if counterpart_balance_emp > 0.0 else 0.0,
    #                     'credit': -counterpart_balance_emp if counterpart_balance_emp < 0.0 else 0.0,
    #                     'partner_id': self.partner_id.id,
    #                     'account_id': record.account_id.id,
    #                     'analytic_account_id': record.analytic_account_id.id,
    #                     'tax_ids': [(4, line.id) for line in record.tax_ids],
    #                     'analytic_tag_ids': [(4, line.id) for line in record.analytic_tag_ids],
    #                     'not_a_contact': True,
    #                 }
    #             )
    #         if not self.currency_id.is_zero(write_off_amount_currency):
    #             # Write-off line.
    #             line_vals_list.append({
    #                 'name': write_off_line_vals.get('name') or default_line_name,
    #                 'amount_currency': write_off_amount_currency,
    #                 'currency_id': currency_id,
    #                 'debit': write_off_balance if write_off_balance > 0.0 else 0.0,
    #                 'credit': -write_off_balance if write_off_balance < 0.0 else 0.0,
    #                 'partner_id': self.partner_id.id,
    #                 'account_id': write_off_line_vals.get('account_id'),
    #             })
    #         return line_vals_list
    #     else:
    #         return super()._prepare_move_line_default_vals(write_off_line_vals)

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
        if self.not_a_contact:
            for line in self.move_id.line_ids:
                if line.account_id in self._get_valid_liquidity_accounts():
                    liquidity_lines += line
                elif line.not_a_contact:
                    counterpart_lines += line
                else:
                    writeoff_lines += line

            return liquidity_lines, counterpart_lines, writeoff_lines
        else:
            return super()._seek_for_lines()

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        for record in self:
            if record.not_a_contact:
                if record._context.get('skip_account_move_synchronization'):
                    return

                for pay in record.with_context(skip_account_move_synchronization=True):

                    # After the migration to 14.0, the journal entry could be shared between the account.payment and the
                    # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
                    if pay.move_id.statement_line_id:
                        continue

                    move = pay.move_id
                    move_vals_to_write = {}
                    payment_vals_to_write = {}

                    if 'journal_id' in changed_fields:
                        if pay.journal_id.type not in ('bank', 'cash'):
                            raise UserError(_("A payment must always belongs to a bank or cash journal."))

                    if 'line_ids' in changed_fields:
                        all_lines = move.line_ids
                        liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                        if len(liquidity_lines) != 1:
                            raise UserError(_(
                                "Journal Entry %s is not valid. In order to proceed, the journal items must "
                                "include one and only one outstanding payments/receipts account.",
                                move.display_name,
                            ))

                        if len(counterpart_lines) < 1:
                            raise UserError(_(
                                "Journal Entry %s is not valid. In order to proceed, the journal items must "
                                "include at least one counterpart lines (with an exception of "
                                "internal transfers).",
                                move.display_name,
                            ))

                        if writeoff_lines and len(writeoff_lines.account_id) != 1:
                            raise UserError(_(
                                "Journal Entry %s is not valid. In order to proceed, "
                                "all optional journal items must share the same account.",
                                move.display_name,
                            ))

                        if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                            raise UserError(_(
                                "Journal Entry %s is not valid. In order to proceed, the journal items must "
                                "share the same currency.",
                                move.display_name,
                            ))

                        if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                            raise UserError(_(
                                "Journal Entry %s is not valid. In order to proceed, the journal items must "
                                "share the same partner.",
                                move.display_name,
                            ))

                        liquidity_amount = liquidity_lines.amount_currency

                        move_vals_to_write.update({
                            'currency_id': liquidity_lines.currency_id.id,
                            'partner_id': liquidity_lines.partner_id.id,
                        })
                        payment_vals_to_write.update({
                            'amount': abs(liquidity_amount),
                            'currency_id': liquidity_lines.currency_id.id,
                            'partner_id': liquidity_lines.partner_id.id,
                        })
                        if liquidity_amount > 0.0:
                            payment_vals_to_write.update({'payment_type': 'inbound'})
                        elif liquidity_amount < 0.0:
                            payment_vals_to_write.update({'payment_type': 'outbound'})

                    move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
                    pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))
            else:
                super()._synchronize_from_moves(changed_fields)

    def action_post(self):
        super().action_post()
        if self.bank_cheque and not self.is_internal_transfer:
            if self.partner_type == 'customer':
                self.sub_cheque_status = 'in_cheque_box'
            else:
                self.sub_cheque_status = 'issued'

    def action_cancel_pdc(self):
        for record in self:
            second_moves = record.pdc_move_ids - record.move_id
            second_moves.button_cancel()
            if record.move_id:
                reverse_move_vals = {
                    "move_ids": [(4, record.move_id.id)],
                    "reason": "Cancelled" + record.name,
                    "refund_method": 'cancel',
                    'company_id': record.move_id.company_id.id,
                    'journal_id': record.move_id.journal_id.id,
                }
                reverse_move = self.env["account.move.reversal"].create(reverse_move_vals)
                res = reverse_move.reverse_moves()
                for new_move in reverse_move.new_move_ids:
                    new_move.pdc_payment_id = record.id
                record.pdc_move_ids = [(4, id in reverse_move.new_move_ids.ids)]
            record.sub_cheque_status = 'cancelled'

    def action_collect_pdc(self):
        for record in self:
            if record.branch_cheque:
                if record.branch_cheque:
                    if record.payment_type == 'inbound':
                        line_ids = [
                            (
                                0,
                                0,
                                {
                                    "debit": 0.0,
                                    "credit": record.amount,
                                    "account_id": record.ho_account_id.id,
                                    "partner_id": record.partner_id.id,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "debit": record.amount,
                                    "credit": 0.0,
                                    "account_id": record.bank_journal_id.default_account_id.id,
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
                                    "account_id": record.bank_journal_id.default_account_id.id,
                                    "partner_id": record.partner_id.id,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "debit": record.amount,
                                    "credit": 0.0,
                                    "account_id": record.branch_account_id.id,
                                    "partner_id": record.partner_id.id,
                                },
                            ),
                        ]
                    move_vals = {
                        "journal_id": record.bank_journal_id.id,
                        "date": record.cheque_collection_date,
                        "ref": record.name,
                        "pdc_payment_id": record.id,
                        "line_ids": line_ids,
                    }
                    move = self.env["account.move"].create(move_vals)
                    move.action_post()
                    if record.payment_type == 'inbound':
                        line_ids = [
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
                            (
                                0,
                                0,
                                {
                                    "debit": record.amount,
                                    "credit": 0.0,
                                    "account_id": record.branch_account_id.id,
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
                                    "account_id": record.journal_id.default_account_id.id,
                                    "partner_id": record.partner_id.id,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "debit": 0.0,
                                    "credit": record.amount,
                                    "account_id": record.branch_account_id.id,
                                    "partner_id": record.partner_id.id,
                                },
                            ),
                        ]
                    move_vals = {
                        "journal_id": record.journal_id.id,
                        "date": record.cheque_collection_date,
                        "ref": record.name,
                        "pdc_payment_id": record.id,
                        "line_ids": line_ids,
                    }
                    move = self.env["account.move"].sudo().create(move_vals)
                    move.sudo().action_post()
                    record.pdc_move_ids = [(4, move.id)]
                    record.sub_cheque_status = 'collected'

            else:
                if len(record.pdc_move_ids) > 1:
                    second_moves = record.pdc_move_ids - record.move_id
                    second_move_id = second_moves.filtered(lambda line: line.state != 'cancel')
                    if second_move_id and second_move_id.state == 'draft':
                        second_move_id.action_post()
                        record.sub_cheque_status = 'collected'
                    else:
                        if record.payment_type == 'inbound':
                            line_ids = [
                                (
                                    0,
                                    0,
                                    {
                                        "debit": 0.0,
                                        "credit": record.amount,
                                        "account_id": record.payment_method_line_id.payment_account_id.id,
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
                            "date": record.cheque_collection_date,
                            "ref": record.name,
                            "pdc_payment_id": record.id,
                            "line_ids": line_ids,
                        }
                        move = self.env["account.move"].create(move_vals)
                        move.action_post()
                        record.pdc_move_ids = [(4, move.id)]
                        record.sub_cheque_status = 'collected'
                else:
                    if record.payment_type == 'inbound':
                        line_ids = [
                            (
                                0,
                                0,
                                {
                                    "debit": 0.0,
                                    "credit": record.amount,
                                    "account_id": record.payment_method_line_id.payment_account_id.id,
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
                        "date": record.cheque_collection_date,
                        "ref": record.name,
                        "pdc_payment_id": record.id,
                        "line_ids": line_ids,
                    }
                    move = self.env["account.move"].create(move_vals)
                    move.action_post()
                    record.pdc_move_ids = [(4, move.id)]
                    record.sub_cheque_status = 'collected'

    def action_refuse_pdc(self):
        for record in self:
            second_move_id = record.pdc_move_ids - record.move_id
            second_move_id.filtered(lambda line: line.state == 'posted').button_draft()
            if record.partner_type == 'customer':
                record.sub_cheque_status = 'in_cheque_box'
            else:
                record.sub_cheque_status = 'issued'

            # if record.move_id:
            #     reverse_move_vals = {
            #         "move_ids": [(4, record.move_id.id)],
            #         "reason": "Cancelled" + record.name,
            #         "refund_method": 'cancel',
            #         'company_id': record.move_id.company_id.id,
            #         'journal_id': record.move_id.journal_id.id,
            #     }
            #     reverse_move = self.env["account.move.reversal"].create(reverse_move_vals)
            #     res = reverse_move.reverse_moves()
            #     for new_move in reverse_move.new_move_ids:
            #         new_move.pdc_payment_id = record.id
            #     record.pdc_move_ids = [(4, id in reverse_move.new_move_ids.ids)]
            # # record.state = 'refused'

    def button_open_journal_entry(self):
        self.ensure_one()
        if self.bank_cheque and not self.is_internal_transfer:
            return {
                'name': _("Journal Entry"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'context': {'create': False},
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.pdc_move_ids.ids)],
            }
        else:
            return super().button_open_journal_entry()


class EmployeePaymentOrderInfo(models.Model):
    _name = "employee.payment.order.info"
    _inherit = ['analytic.mixin']
    _description = "Employee Payment Order Info"
    _order = "id"
    _check_company_auto = True

    payment_id = fields.Many2one('account.payment', string='Partner Payment',
                                 index=True, required=True, readonly=True, auto_join=True, ondelete="cascade",
                                 check_company=True,)
    company_id = fields.Many2one(related='payment_id.company_id', store=True, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
                                          readonly=True, store=True,
                                          help='Utility field to express amount currency')
    account_id = fields.Many2one('account.account', string='Account', index=True, ondelete="cascade", tracking=True,
                                 domain="[('deprecated', '=', False)]", check_company=True, required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', index=True,
                                          check_company=True, copy=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags', check_company=True, copy=True)
    plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Plan',
        check_company=True,
        required=True,
        related = "analytic_account_id.plan_id"
    )
    memo = fields.Char(string='Memo', tracking=True)
    payment_amount = fields.Monetary(string='Payment Amount', default=0.0, currency_field='company_currency_id')
    tax_ids = fields.Many2many(comodel_name='account.tax', string="Tax Applied", context={'active_test': False},
                               check_company=True, help="Taxes that apply on the base amount")
    total = fields.Monetary(string='Total', compute='_compute_amount', store=True, currency_field='company_currency_id')
    price_tax = fields.Monetary(string='Tax Amount', compute='_compute_amount', store=True,
                                currency_field='company_currency_id')




    @api.depends('tax_ids', 'payment_amount')
    def _compute_amount(self):
        for line in self:
            taxes = line.tax_ids.compute_all(line.payment_amount, line.company_currency_id, 1,
                                             product=None, partner=line.payment_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'total': taxes['total_included'],
            })
    def _compute_analytic_distribution(self):
        pass

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    not_a_contact = fields.Boolean(default=False, string="Not a Contact")


class AccountMove(models.Model):
    _inherit = "account.move"

    pdc_payment_id = fields.Many2one(comodel_name='account.payment', ondelete="cascade")

