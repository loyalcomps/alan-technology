# -*- coding: utf-8 -*-

import time
from odoo import api, models, fields
from dateutil.parser import parse
from odoo.exceptions import UserError


class ReportVendorOutstandingStatement(models.AbstractModel):
    _name = 'report.vendor_outstanding_statement.invoice_outstanding'
    _description = 'Vendor Outstanding Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        company_id = data['company_id']
        print("company_id", company_id, data)
        partner_id = data['partner_id']
        end_date = data['end_date']
        company_id = self.env['res.company'].browse(company_id)
        partner = self.env['res.partner'].browse(partner_id).name
        move_lines = self.env['account.move.line'].search([
            ('date_maturity', '<=', end_date),
            ('partner_id', '=', partner_id),
            ('full_reconcile_id', '=', False),
            ('balance', '!=', 0),
            ('account_id.reconcile', '=', True),
            ('account_id.account_type', '=', 'liability_payable'),
                      # ('account_id.internal_type', '=', 'payable'),
            ('move_id.state', '=', 'posted')
        ], order='date_maturity ASC')
        print(move_lines, "mmmmmmmmmmmmmmm")

        lines_to_display = []
        total_amount_due = 0

        if move_lines:
            for line in move_lines:
                vals = {
                    'name': line.move_id.name,
                    'date': line.date,
                    'due_date': line.date_maturity,
                    'balance': line.balance,
                    'journal': line.journal_id.name,
                }
                total_amount_due += line.balance
                lines_to_display.append(vals)
        else:
            lines_to_display.append({
                'name': 'No outstanding invoices found',
                'date': '',
                'due_date': '',
                'balance': 0,
                'journal': '',
            })

        docargs = {
            'docs': self.env['res.partner'].browse(partner_id),
            'lines_to_display': lines_to_display,
            'date': end_date,
            'customer': partner,
            'total_amount_due': total_amount_due,
            'company_id': company_id,

        }
        return docargs

        # if invoices:
        #
        #     amount_due = 0
        #     for total_amount in invoices:
        #         if total_amount.type == 'in_refund':
        #             amount_due = amount_due - total_amount.residual
        #         if total_amount.type == 'in_invoice':
        #             amount_due = amount_due + total_amount.residual
        #     total_amount_due = amount_due
        #     docs.end_date = end_date
        #     # partner = self.env['res.partner'].browse(partner_id)
        #     # print partner.name
        #     docargs = {
        #         'docs': self.env['res.partner'].browse(partner_id),
        #         'invoices': invoices,
        #         'date': end_date,
        #         'customer': partner,
        #         'total_amount_due': total_amount_due,
        #     }
        #     return self.env['report'].render('vendor_outstanding_statement.invoice_outstanding', docargs)
        # else:
        #     raise UserError("There is not any Outstanding invoice")
