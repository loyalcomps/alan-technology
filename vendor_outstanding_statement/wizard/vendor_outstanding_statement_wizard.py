# -*- coding: utf-8 -*-
# Copyright 2017 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from ast import parse
from datetime import date
from odoo import api, fields, models
from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo import api, fields, models
from odoo.exceptions import UserError, RedirectWarning, ValidationError

from odoo import api, fields, models, _

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import xlwt
# from cStringIO import StringIO
from io import StringIO
import base64

class VendorOutstandingStatementWizard(models.TransientModel):
    """Vendor Outstanding Statement wizard."""

    _name = 'vendor.outstanding.statement'
    _description = 'Vendor Outstanding Statement Wizard'

    @api.model
    def default_get(self, fields):
        result = super(VendorOutstandingStatementWizard, self).default_get(fields)
        partner_id = self._context.get('active_id')
        date = str(datetime.now())
        result['partner_id'] = partner_id
        result['end_date'] = date
        return result

    partner_id = fields.Many2one('res.partner',
                                 string='Partner')

    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.user.company_id,
        string='Company'
    )

    end_date = fields.Date(required=True)

    def _export(self, xls=False):
        """Export to PDF."""

        data = self._prepare_outstanding_statement()
        if xls:
            data['xls'] = True
        else:
            data['xls'] = False
        return self.env.ref('vendor_outstanding_statement.action_vendor_invoice_outstanding').report_action(
            self, data=data, config=False)

        # return self.env['report'].with_context(landscape=True).get_action(
        #     self, 'vendor_outstanding_statement.invoice_outstanding', data=data)


    # @api.multi
    def button_export_pdf(self):
        self.ensure_one()
        return self._export(False)


    def _prepare_outstanding_statement(self):
        self.ensure_one()
        return {
            'end_date': self.end_date,
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
        }

    # def _print_report(self, data,):
    #     data['form'].update(self.read(['end_date', 'partner_id'])[0])
    #     self.model = self.env.context.get('active_model')
    #     print self.model
    #     date = data['form']['end_date']
    #     return self.env['report'].with_context(landscape=True).get_action(self, 'vendor_outstanding_statement.invoice_outstanding', data=data)


    # @api.multi
    # def button_export_pdf(self):
    #     self.ensure_one()
    #     data = {}
    #     data['form'] = self.read(['partner_id', 'date_end'])[0]
    #     return self._export(data)
    #
    # def _prepare_outstanding_statement(self):
    #     self.ensure_one()
    #     return {
    #         'date_end': self.date_end,
    #         'company_id': self.company_id.id,
    #         'partner_ids': self._context['active_ids'],
    #     }
    #
    # def _export(self, data, xls=False,):
    #     """Export to PDF."""
    #     print "111111111111111111111111111111111111111111111111111111", xls
    #     lines = []
    #     self.model = self.env.context.get('active_model')
    #     docs = self.env[self.model].browse(self.env.context.get('active_id'))
    #     data['form'].update(self.read(['partner_id', 'date_end'])[0])
    #     date = data['form']['date_end']
    #     # partner = self.env['res.partner'].browse(data['partner_id'])
    #     orders = self.env['account.invoice'].search([('partner_id', '=',docs.id), ('state', '=', 'open')])
    #     print orders
    #     for line in orders:
    #         if date >= line.date_due:
    #             vals = {
    #                 'name': line.number,
    #                 'date': line.date_invoice,
    #                 'due_date': line.date_due,
    #                 'amount_due': line.residual,
    #             }
    #             lines.append(vals)
    #     data = lines
    #     print "111111111111111111111111111111111111111111111111111111", lines
    #     return self.env['report'].with_context(landscape=True).get_action(
    #         self, 'vendor_outstanding_statement.statement', data=data)

    # @api.multi
    # def button_export_pdf(self):
    #     data = {}
    #     data['form'] = self.read(['partner_id', 'date_end'])[0]
    #     return self._print_report(data)

    # def _print_report(self, data):
    #     data['form'].update(self.read(['partner_id', 'date_end'])[0])
    #     return self.env['report'].get_action(self, 'sales_report.report_salesperson', data=data)

    # @api.model
    # def render_html(self, docids, data=None):
    #     self.model = self.env.context.get('active_model')
    #     docs = self.env[self.model].browse(self.env.context.get('active_id'))
    #     sales_records = []
    #     orders = self.env['account.invoice'].search([('partner_id', '=', docs.partner_id.id),('state', '=', 'open')])
    #     print orders
    #     if docs.date_from and docs.date_to:
    #         for order in orders:
    #             if parse(docs.date_from) <= parse(order.date_order) and parse(docs.date_to) >= parse(order.date_order):
    #                 sales_records.append(order);
    #             else:
    #                 raise UserError("Please enter duration")
    #
    #     docargs = {
    #         'doc_ids': self.ids,
    #         'doc_model': self.model,
    #         'docs': docs,
    #         'time': time,
    #         'orders': sales_records
    #     }
    #     return self.env['report'].render('sales_report.report_salesperson', docargs)


    # @api.multi
    # def action_soa_send(self):
    #
    #     self.ensure_one()
    #     ir_model_data = self.env['ir.model.data']
    #     #        try:
    #     #            template_id = ir_model_data.get_object_reference('sale', 'email_template_edi_sale')[1]
    #     #        except ValueError:
    #     #            template_id = False
    #     try:
    #         compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
    #     except ValueError:
    #         compose_form_id = False
    #     ctx = dict()
    #     ctx.update({
    #         'default_model': 'res.partner',
    #         'default_template_id': 21,
    #         'default_subject': 'SOA',
    #         'default_partner_ids': [(6, 0, [self.partner_id and self.partner_id.id])],
    #         'default_res_id': self.partner_id and self.partner_id.id,
    #         'default_composition_mode': 'comment',
    #         'mark_so_as_sent': True,
    #
    #     })
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'mail.compose.message',
    #         'views': [(compose_form_id, 'form')],
    #         'view_id': compose_form_id,
    #         'target': 'new',
    #         'context': ctx,
    #     }
    #
    # excel_file = fields.Binary(string='Dowload Report Excel', readonly="1")
    # file_name = fields.Char(string='Excel File', readonly="1")
    #
    # partner_id = fields.Many2one('res.partner',
    #                              string='Partner')
    #
    # company_id = fields.Many2one(
    #     comodel_name='res.company',
    #     default=lambda self: self.env.user.company_id,
    #     string='Company'
    # )
    #
    # date_end = fields.Date(required=True)
    # show_aging_buckets = fields.Boolean(string='Include Aging Buckets',
    #                                     default=True)
    # number_partner_ids = fields.Integer(
    #     default=lambda self: len(self._context['active_ids'])
    # )
    # filter_partners_non_due = fields.Boolean(
    #     string='Don\'t show partners with no due entries', default=True)
    #
    # @api.multi
    # def button_export_pdf(self):
    #     self.ensure_one()
    #     return self._export(False)
    #
    # @api.multi
    # def button_create_xls(self):
    #     self.ensure_one()
    #     data = self._prepare_outstanding_statement()
    #     if len(data['partner_ids']) > 1:
    #         raise UserError(_('select one partner at a time'))
    #     data_xls = self.xls_main(data)
    #     print "bbbbbbbbbbbbbbbbbbbbb", data_xls
    #     partner_obj = data_xls['docs']
    #     p_name = partner_obj.name
    #     date_end = self.date_end
    #
    #     #        filename= 'customer_outstanding.xls'
    #     filename = partner_obj.name + "(" + date_end + ")" + ".xls"
    #
    #     workbook = xlwt.Workbook(encoding="UTF-8")
    #     sheet = workbook.add_sheet('General Ledger Report', cell_overwrite_ok=True)
    #     style = xlwt.easyxf(
    #         'font:height 400, bold True, name Arial; align: horiz center, vert center;borders: top medium,right medium,bottom medium,left medium')
    #     style_filter = xlwt.easyxf('font:name Arial; align: horiz center, vert center;')
    #     a = range(1, 10)
    #     row = 0
    #     col = 0
    #     # header = header
    #     style2 = xlwt.easyxf('font: bold 1')
    #
    #     sheet.write(row, 0, "Customer", style2)
    #     sheet.write(row, 1, p_name)
    #
    #     sheet.write(row + 1, 0, "Date", style2)
    #     sheet.write(row + 1, 1, date_end)
    #     if data_xls['Lines'][partner_obj.id]:
    #
    #         sheet.write(row + 3, 2, "Date", style2)
    #         sheet.write(row + 3, 3, "Reference number", style2)
    #
    #         sheet.write(row + 3, 4, "Description", style2)
    #
    #         sheet.write(row + 3, 5, "Opening Amount", style2)
    #         sheet.write(row + 3, 6, "Pending Amount", style2)
    #         sheet.write(row + 3, 7, "Balance", style2)
    #         sheet.write(row + 3, 8, "Due Date", style2)
    #         row = 3
    #         for currency in data_xls['Lines'][partner_obj.id]:
    #             for line in data_xls['Lines'][partner_obj.id][currency]:
    #                 if not line['blocked']:
    #                     row = row + 1
    #                     sheet.write(row, 2, line['date'])
    #                     sheet.write(row, 3, line['move_id'])
    #
    #                     sheet.write(row, 8, line['date_maturity'])
    #                     if line['name'] != '/':
    #                         if not line['ref']:
    #                             sheet.write(row, 4, line['name'])
    #
    #                         if line['ref'] and line['name']:
    #                             if line['name'] not in line['ref']:
    #                                 sheet.write(row, 4, line['name'])
    #                             if line['ref'] not in line['name']:
    #                                 sheet.write(row, 4, line['ref'])
    #                     if line['name'] == '/':
    #                         sheet.write(row, 4, line['ref'])
    #
    #                     sheet.write(row, 5, line['amount'])
    #                     sheet.write(row, 6, line['open_amount'])
    #                     sheet.write(row, 7, line['balance'])
    #
    #                 if line['blocked']:
    #                     row = row + 1
    #                     sheet.write(row, 2, line['date'])
    #                     sheet.write(row, 3, line['move_id'])
    #
    #                     sheet.write(row, 8, line['date_maturity'])
    #                     if line['name'] != '/':
    #                         if not line['ref']:
    #                             sheet.write(row, 4, line['name'])
    #
    #                         if line['ref'] and line['name']:
    #                             if line['name'] not in line['ref']:
    #                                 sheet.write(row, 4, line['name'])
    #                             if line['ref'] not in line['name']:
    #                                 sheet.write(row, 4, line['ref'])
    #                     if line['name'] == '/':
    #                         sheet.write(row, 4, line['ref'])
    #
    #                     sheet.write(row, 5, line['amount'])
    #                     sheet.write(row, 6, line['open_amount'])
    #                     sheet.write(row, 7, line['balance'])
    #         sheet.write(row + 1, 2, data_xls['Date_end'][partner_obj.id], style2)
    #         sheet.write(row + 1, 4, 'Ending Balance', style2)
    #
    #         sheet.write(row + 1, 7, data_xls['Amount_Due'][partner_obj.id][currency], style2)
    #         row = row + 6
    #
    #         sheet.write(row, 2, 'Current Due', style2)
    #         sheet.write(row, 3, '1-30 Days Due', style2)
    #         sheet.write(row, 4, '30-60 Days Due', style2)
    #         sheet.write(row, 5, '60-90 Days Due', style2)
    #
    #         sheet.write(row, 6, '90-120 Days Due', style2)
    #         sheet.write(row, 7, '+120 Days Due', style2)
    #         sheet.write(row, 8, 'Balance Due', style2)
    #
    #         if currency in data_xls['Buckets'][partner_obj.id]:
    #             sheet.write(row + 1, 2, data_xls['Buckets'][partner_obj.id][currency]['current'])
    #             sheet.write(row + 1, 3, data_xls['Buckets'][partner_obj.id][currency]['b_1_30'])
    #             sheet.write(row + 1, 4, data_xls['Buckets'][partner_obj.id][currency]['b_30_60'])
    #             sheet.write(row + 1, 5, data_xls['Buckets'][partner_obj.id][currency]['b_60_90'])
    #             sheet.write(row + 1, 6, data_xls['Buckets'][partner_obj.id][currency]['b_90_120'])
    #             sheet.write(row + 1, 7, data_xls['Buckets'][partner_obj.id][currency]['b_over_120'])
    #             sheet.write(row + 1, 8, data_xls['Buckets'][partner_obj.id][currency]['balance'])
    #         if currency not in data_xls['Buckets'][partner_obj.id]:
    #             sheet.write(row + 1, 2, 0, style2)
    #             sheet.write(row + 1, 3, 0, style2)
    #             sheet.write(row + 1, 4, 0, style2)
    #             sheet.write(row + 1, 5, 0, style2)
    #             sheet.write(row + 1, 6, 0, style2)
    #             sheet.write(row + 1, 7, 0, style2)
    #             sheet.write(row + 1, 8, 0, style2)
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #     else:
    #         sheet.write(row + 3, 2, "No Overdue", style2)
    #
    #     fp = StringIO()
    #     workbook.save(fp)
    #     excel_file = base64.encodestring(fp.getvalue())
    #     self.excel_file = excel_file
    #     self.file_name = filename
    #     fp.close()
    #
    #     return {
    #         'name': _('Customer Outstanding'),
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'customer.outstanding.statement.wizard',
    #         'res_id': self.id,
    #         'target': 'new',
    #     }
    #
    # def _prepare_outstanding_statement(self):
    #     self.ensure_one()
    #     return {
    #         'date_end': self.date_end,
    #         'company_id': self.company_id.id,
    #         'partner_ids': self._context['active_ids'],
    #         'show_aging_buckets': self.show_aging_buckets,
    #         'filter_non_due_partners': self.filter_partners_non_due,
    #     }
    #
    # def _export(self, xls=False):
    #     """Export to PDF."""
    #
    #     print "111111111111111111111111111111111111111111111111111111", xls
    #     data = self._prepare_outstanding_statement()
    #     if len(data['partner_ids']) > 1:
    #         raise UserError(_('select one partner at a time'))
    #     if xls:
    #         data['xls'] = True
    #     else:
    #         data['xls'] = False
    #     id = 543
    #     obj_report = self.env['ir.actions.report.xml'].browse(id)
    #     partner_name = self.env['res.partner'].browse(data['partner_ids'][0]).name
    #     obj_report.name = partner_name + "(" + self.date_end + ")"
    #     print "111111111111111111111111111111111111111111111111111111", data
    #     return self.env['report'].with_context(landscape=True).get_action(
    #         self, 'customer_outstanding_statement.statement', data=data)
    #
    # ###############################################################3
    #
    # def _format_date_to_partner_lang(self, str_date, partner_id):
    #     lang_code = self.env['res.partner'].browse(partner_id).lang
    #     lang = self.env['res.lang']._lang_get(lang_code)
    #     date = datetime.strptime(str_date, DEFAULT_SERVER_DATE_FORMAT).date()
    #     return date.strftime(lang.date_format)
    #
    # def _display_lines_sql_q1(self, partners, date_end):
    #     return """
    #         SELECT m.name as move_id, l.partner_id, l.date, l.name,
    #                         l.ref, l.blocked, l.currency_id, l.company_id,
    #         CASE WHEN (l.currency_id is not null AND l.amount_currency > 0.0)
    #             THEN sum(l.amount_currency)
    #             ELSE sum(l.debit)
    #         END as debit,
    #         CASE WHEN (l.currency_id is not null AND l.amount_currency < 0.0)
    #             THEN sum(l.amount_currency * (-1))
    #             ELSE sum(l.credit)
    #         END as credit,
    #         CASE WHEN l.balance > 0.0
    #             THEN l.balance - sum(coalesce(pd.amount, 0.0))
    #             ELSE l.balance + sum(coalesce(pc.amount, 0.0))
    #         END AS open_amount,
    #         CASE WHEN l.balance > 0.0
    #             THEN l.amount_currency - sum(coalesce(pd.amount_currency, 0.0))
    #             ELSE l.amount_currency + sum(coalesce(pc.amount_currency, 0.0))
    #         END AS open_amount_currency,
    #         CASE WHEN l.date_maturity is null
    #             THEN l.date
    #             ELSE l.date_maturity
    #         END as date_maturity
    #         FROM account_move_line l
    #         JOIN account_account_type at ON (at.id = l.user_type_id)
    #         JOIN account_move m ON (l.move_id = m.id)
    #         LEFT JOIN (SELECT pr.*
    #             FROM account_partial_reconcile pr
    #             INNER JOIN account_move_line l2
    #             ON pr.credit_move_id = l2.id
    #             WHERE l2.date <= '%s'
    #         ) as pd ON pd.debit_move_id = l.id
    #         LEFT JOIN (SELECT pr.*
    #             FROM account_partial_reconcile pr
    #             INNER JOIN account_move_line l2
    #             ON pr.debit_move_id = l2.id
    #             WHERE l2.date <= '%s'
    #         ) as pc ON pc.credit_move_id = l.id
    #         WHERE l.partner_id IN (%s) AND at.type = 'receivable'
    #                             AND not l.reconciled AND l.date <= '%s'
    #         GROUP BY l.partner_id, m.name, l.date, l.date_maturity, l.name,
    #                             l.ref, l.blocked, l.currency_id,
    #                             l.balance, l.amount_currency, l.company_id
    #     """ % (date_end, date_end, partners, date_end)
    #
    # def _display_lines_sql_q2(self):
    #     return """
    #         SELECT partner_id, currency_id, move_id, date, date_maturity,
    #                         debit, credit, name, ref, blocked, company_id,
    #         CASE WHEN currency_id is not null
    #                 THEN open_amount_currency
    #                 ELSE open_amount
    #         END as open_amount
    #         FROM Q1
    #     """
    #
    # def _display_lines_sql_q3(self, company_id):
    #     return """
    #         SELECT Q2.partner_id, move_id, date, date_maturity, Q2.name, ref,
    #                         debit, credit, debit-credit AS amount, blocked,
    #         COALESCE(Q2.currency_id, c.currency_id) AS currency_id, open_amount
    #         FROM Q2
    #         JOIN res_company c ON (c.id = Q2.company_id)
    #         WHERE c.id = %s
    #     """ % company_id
    #
    # def _get_account_display_lines(self, company_id, partner_ids, date_end):
    #     res = dict(map(lambda x: (x, []), partner_ids))
    #     partners = ', '.join([str(i) for i in partner_ids])
    #     date_end = datetime.strptime(
    #         date_end, DEFAULT_SERVER_DATE_FORMAT).date()
    #     self.env.cr.execute("""WITH Q1 AS (%s), Q2 AS (%s), Q3 AS (%s)
    #     SELECT partner_id, currency_id, move_id, date, date_maturity, debit,
    #                         credit, amount, open_amount, name, ref, blocked
    #     FROM Q3
    #     ORDER BY date, date_maturity, move_id""" % (
    #         self._display_lines_sql_q1(partners, date_end),
    #         self._display_lines_sql_q2(),
    #         self._display_lines_sql_q3(company_id)))
    #     for row in self.env.cr.dictfetchall():
    #         res[row.pop('partner_id')].append(row)
    #     return res
    #
    # def _show_buckets_sql_q1(self, partners, date_end):
    #     return """
    #         SELECT l.partner_id, l.currency_id, l.company_id, l.move_id,
    #         CASE WHEN l.balance > 0.0
    #             THEN l.balance - sum(coalesce(pd.amount, 0.0))
    #             ELSE l.balance + sum(coalesce(pc.amount, 0.0))
    #         END AS open_due,
    #         CASE WHEN l.balance > 0.0
    #             THEN l.amount_currency - sum(coalesce(pd.amount_currency, 0.0))
    #             ELSE l.amount_currency + sum(coalesce(pc.amount_currency, 0.0))
    #         END AS open_due_currency,
    #         CASE WHEN l.date_maturity is null
    #             THEN l.date
    #             ELSE l.date_maturity
    #         END as date_maturity
    #         FROM account_move_line l
    #         JOIN account_account_type at ON (at.id = l.user_type_id)
    #         JOIN account_move m ON (l.move_id = m.id)
    #         LEFT JOIN (SELECT pr.*
    #             FROM account_partial_reconcile pr
    #             INNER JOIN account_move_line l2
    #             ON pr.credit_move_id = l2.id
    #             WHERE l2.date <= '%s'
    #         ) as pd ON pd.debit_move_id = l.id
    #         LEFT JOIN (SELECT pr.*
    #             FROM account_partial_reconcile pr
    #             INNER JOIN account_move_line l2
    #             ON pr.debit_move_id = l2.id
    #             WHERE l2.date <= '%s'
    #         ) as pc ON pc.credit_move_id = l.id
    #         WHERE l.partner_id IN (%s) AND at.type = 'receivable'
    #                             AND not l.reconciled AND not l.blocked
    #         GROUP BY l.partner_id, l.currency_id, l.date, l.date_maturity,
    #                             l.amount_currency, l.balance, l.move_id,
    #                             l.company_id
    #     """ % (date_end, date_end, partners)
    #
    # def _show_buckets_sql_q2(self, today, minus_30, minus_60, minus_90,
    #                          minus_120):
    #     return """
    #         SELECT partner_id, currency_id, date_maturity, open_due,
    #                         open_due_currency, move_id, company_id,
    #         CASE
    #             WHEN '%s' <= date_maturity AND currency_id is null
    #                             THEN open_due
    #             WHEN '%s' <= date_maturity AND currency_id is not null
    #                             THEN open_due_currency
    #             ELSE 0.0
    #         END as current,
    #         CASE
    #             WHEN '%s' < date_maturity AND date_maturity < '%s'
    #                             AND currency_id is null THEN open_due
    #             WHEN '%s' < date_maturity AND date_maturity < '%s'
    #                             AND currency_id is not null
    #                             THEN open_due_currency
    #             ELSE 0.0
    #         END as b_1_30,
    #         CASE
    #             WHEN '%s' < date_maturity AND date_maturity <= '%s'
    #                             AND currency_id is null THEN open_due
    #             WHEN '%s' < date_maturity AND date_maturity <= '%s'
    #                             AND currency_id is not null
    #                             THEN open_due_currency
    #             ELSE 0.0
    #         END as b_30_60,
    #         CASE
    #             WHEN '%s' < date_maturity AND date_maturity <= '%s'
    #                             AND currency_id is null THEN open_due
    #             WHEN '%s' < date_maturity AND date_maturity <= '%s'
    #                             AND currency_id is not null
    #                             THEN open_due_currency
    #             ELSE 0.0
    #         END as b_60_90,
    #         CASE
    #             WHEN '%s' < date_maturity AND date_maturity <= '%s'
    #                             AND currency_id is null THEN open_due
    #             WHEN '%s' < date_maturity AND date_maturity <= '%s'
    #                             AND currency_id is not null
    #                             THEN open_due_currency
    #             ELSE 0.0
    #         END as b_90_120,
    #         CASE
    #             WHEN date_maturity <= '%s' AND currency_id is null
    #                             THEN open_due
    #             WHEN date_maturity <= '%s' AND currency_id is not null
    #                             THEN open_due_currency
    #             ELSE 0.0
    #         END as b_over_120
    #         FROM Q1
    #         GROUP BY partner_id, currency_id, date_maturity, open_due,
    #                             open_due_currency, move_id, company_id
    #     """ % (today, today, minus_30, today, minus_30, today, minus_60,
    #            minus_30, minus_60, minus_30, minus_90, minus_60, minus_90,
    #            minus_60, minus_120, minus_90, minus_120, minus_90, minus_120,
    #            minus_120)
    #
    # def _show_buckets_sql_q3(self, company_id):
    #     return """
    #         SELECT Q2.partner_id, current, b_1_30, b_30_60, b_60_90, b_90_120,
    #                             b_over_120,
    #         COALESCE(Q2.currency_id, c.currency_id) AS currency_id
    #         FROM Q2
    #         JOIN res_company c ON (c.id = Q2.company_id)
    #         WHERE c.id = %s
    #     """ % company_id
    #
    # def _show_buckets_sql_q4(self):
    #     return """
    #         SELECT partner_id, currency_id, sum(current) as current,
    #                             sum(b_1_30) as b_1_30,
    #                             sum(b_30_60) as b_30_60,
    #                             sum(b_60_90) as b_60_90,
    #                             sum(b_90_120) as b_90_120,
    #                             sum(b_over_120) as b_over_120
    #         FROM Q3
    #         GROUP BY partner_id, currency_id
    #     """
    #
    # _bucket_dates = {
    #     'today': fields.date.today(),
    #     'minus_30': fields.date.today() - timedelta(days=30),
    #     'minus_60': fields.date.today() - timedelta(days=60),
    #     'minus_90': fields.date.today() - timedelta(days=90),
    #     'minus_120': fields.date.today() - timedelta(days=120),
    # }
    #
    # def _get_account_show_buckets(self, company_id, partner_ids, date_end):
    #     res = dict(map(lambda x: (x, []), partner_ids))
    #     partners = ', '.join([str(i) for i in partner_ids])
    #     date_end = datetime.strptime(
    #         date_end, DEFAULT_SERVER_DATE_FORMAT).date()
    #     self.env.cr.execute("""WITH Q1 AS (%s), Q2 AS (%s),
    #     Q3 AS (%s), Q4 AS (%s)
    #     SELECT partner_id, currency_id, current, b_1_30, b_30_60, b_60_90,
    #                         b_90_120, b_over_120,
    #                         current+b_1_30+b_30_60+b_60_90+b_90_120+b_over_120
    #                         AS balance
    #     FROM Q4
    #     GROUP BY partner_id, currency_id, current, b_1_30, b_30_60, b_60_90,
    #     b_90_120, b_over_120""" % (
    #         self._show_buckets_sql_q1(partners, date_end),
    #         self._show_buckets_sql_q2(
    #             self._bucket_dates['today'],
    #             self._bucket_dates['minus_30'],
    #             self._bucket_dates['minus_60'],
    #             self._bucket_dates['minus_90'],
    #             self._bucket_dates['minus_120']),
    #         self._show_buckets_sql_q3(company_id),
    #         self._show_buckets_sql_q4()))
    #     for row in self.env.cr.dictfetchall():
    #         res[row.pop('partner_id')].append(row)
    #     return res
    #
    # @api.multi
    # def xls_main(self, data):
    #     company_id = data['company_id']
    #     partner_ids = data['partner_ids']
    #     date_end = data['date_end']
    #     today = fields.Date.today()
    #
    #     buckets_to_display = {}
    #     lines_to_display, amount_due = {}, {}
    #     currency_to_display = {}
    #     today_display, date_end_display = {}, {}
    #
    #     lines = self._get_account_display_lines(
    #         company_id, partner_ids, date_end)
    #
    #     for partner_id in partner_ids:
    #         print "111111111111111111111111111111111111111111partner_id", partner_id
    #         lines_to_display[partner_id], amount_due[partner_id] = {}, {}
    #         currency_to_display[partner_id] = {}
    #         today_display[partner_id] = self._format_date_to_partner_lang(
    #             today, partner_id)
    #         date_end_display[partner_id] = self._format_date_to_partner_lang(
    #             date_end, partner_id)
    #         for line in lines[partner_id]:
    #             print "2222222222222222222222222222222222222222222222222222", line
    #             currency = self.env['res.currency'].browse(line['currency_id'])
    #             if currency not in lines_to_display[partner_id]:
    #                 lines_to_display[partner_id][currency] = []
    #                 currency_to_display[partner_id][currency] = currency
    #                 amount_due[partner_id][currency] = 0.0
    #             if not line['blocked']:
    #                 amount_due[partner_id][currency] += line['open_amount']
    #             line['balance'] = amount_due[partner_id][currency]
    #             line['date'] = self._format_date_to_partner_lang(
    #                 line['date'], partner_id)
    #             line['date_maturity'] = self._format_date_to_partner_lang(
    #                 line['date_maturity'], partner_id)
    #             lines_to_display[partner_id][currency].append(line)
    #
    #     if data['show_aging_buckets']:
    #         buckets = self._get_account_show_buckets(
    #             company_id, partner_ids, date_end)
    #         for partner_id in partner_ids:
    #             print "555555555555555555555555555555555555555555555555", partner_id
    #             buckets_to_display[partner_id] = {}
    #             for line in buckets[partner_id]:
    #                 print "9999999999999999999999999999999999999999999999999999999", line
    #                 currency = self.env['res.currency'].browse(
    #                     line['currency_id'])
    #                 if currency not in buckets_to_display[partner_id]:
    #                     buckets_to_display[partner_id][currency] = []
    #                 buckets_to_display[partner_id][currency] = line
    #
    #     docargs = {
    #         'doc_ids': partner_ids,
    #         'doc_model': 'res.partner',
    #         'docs': self.env['res.partner'].browse(partner_ids),
    #         'Amount_Due': amount_due,
    #         'Lines': lines_to_display,
    #         'Buckets': buckets_to_display,
    #         'Currencies': currency_to_display,
    #         'Show_Buckets': data['show_aging_buckets'],
    #         'Filter_non_due_partners': data['filter_non_due_partners'],
    #         'Date_end': date_end_display,
    #         'Date': today_display,
    #     }
    #     return docargs
