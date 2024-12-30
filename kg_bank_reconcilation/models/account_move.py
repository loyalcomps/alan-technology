# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    bank_statement_id = fields.Many2one('kg.bank.reconcilation', 'Bank Statement', copy=False)
    ship_from = fields.Many2one('res.country', 'Ship From')
    ship_to = fields.Many2one('res.country', 'Ship To')
    supply_date = fields.Date('Date of Supply')

    @api.onchange('move_type')
    def _onchange_move_type(self):
        domain = [('supplier_rank', '>', 0)]
        if self.move_type in ('out_invoice', 'out_refund', 'out_receipt'):
            domain = []
        if self.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
            domain = [('supplier_rank', '>', 0)]
        return {'domain': {'partner_id': domain}}

    @api.onchange('line_ids', 'invoice_payment_term_id', 'invoice_date_due', 'invoice_cash_rounding_id',
                  'invoice_vendor_bill_id')
    def _onchange_recompute_dynamic_lines(self):
        self._sync_dynamic_lines(container=False)
        # self.line_ids._compute_analytic_account()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _is_accountant(self):
        if (self.env.user.has_group('account.group_account_manager') or self.env.user.has_group(
                'account.group_account_user')) and self._context.get('default_move_type') == 'out_invoice':
            return True
        return False

    bank_statement_id = fields.Many2one('kg.bank.reconcilation', 'Bank Statement', copy=False)
    bk_reconcile_id = fields.Many2one('kg.bank.reconcilation', 'Bank Statement', copy=False)
    statement_date = fields.Date('Bank.St Date', copy=False)
    is_acc = fields.Boolean('To see if the user is an accountant or advisor', default=_is_accountant)
    week_count = fields.Integer()

    def update_bank_statement(self):
        if not self.statement_date:
            self.sudo().write({'statement_date': self.date})

    # def write(self, vals):
    #     if not vals.get("statement_date"):
    #         vals.update({"reconciled": False})
    #     elif vals.get("statement_date"):
    #         vals.update({"reconciled": True})
    #     res = super(AccountMoveLine, self).write(vals)
    #     return res

    # @api.depends('product_id', 'account_id', 'partner_id', 'date')
    # def _compute_analytic_account(self):
    #     for record in self:
    #         rec = self.env['account.analytic.default'].account_get(
    #             product_id=record.product_id.id,
    #             partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
    #             account_id=record.account_id.id,
    #             user_id=record.env.uid,
    #             date=record.date,
    #             company_id=record.move_id.company_id.id
    #         )
    #         if rec:
    #             record.analytic_account_id = rec.analytic_id
    #             record.analytic_tag_ids = rec.analytic_tag_ids
