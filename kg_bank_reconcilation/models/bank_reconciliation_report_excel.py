import io
import base64
from odoo import models


class BankReconciliationXlsx(models.AbstractModel):
    _name = 'report.kg_bank_reconcilation.report_bank_statement_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Bank Reconciliation XLSX Report"

    def generate_xlsx_report(self, workbook, data, bank):
        for obj in bank:

            sheet = workbook.add_worksheet("Bank Reconciliation Report")

            bold = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True,"font_size": 15})
            format_3 = workbook.add_format({'align': 'left', 'bold': True, 'valign': 'top', 'text_wrap': True})
            format_7 = workbook.add_format({'align': 'center', 'bold': False, 'text_wrap': True})
            sheet.merge_range('D3:F3', 'Bank Reconciliation Statement', bold)

            sheet.write(4,0,'Bank :' + obj.journal_id.name)
            sheet.write(4,0,obj.journal_id.name)
            sheet.write(5,0,'Date From :' )
            sheet.write(5,1,obj.date_from.strftime('%d-%m-%Y') )
            sheet.write(6,0,'Date To :' )
            sheet.write(6,1,obj.date_to.strftime('%d-%m-%Y') )
            reconcile_balance=obj.get_reconcile()
            unreconcile_balance=obj.get_unreconcile()
            sheet.write(4, 3, 'Book Balance :'+ str(obj.gl_balance)  )
            sheet.write(5, 3, 'Bank Balance :' + str(obj.bank_balance))
            sheet.write(6, 3, 'Reconciled Balance :'+ str(reconcile_balance))
            sheet.write(7, 3, 'Unreconciled Balance :'+ str(unreconcile_balance))


            sheet.set_column('B:B',12)
            sheet.set_column('C:C',45)
            sheet.set_column('G:G',18)
            sheet.set_column('H:H',18)
            sheet.set_column('I:I',18)
            sheet.set_column('L:L',12)
            sheet.set_column('N:N',12)
            sheet.set_column('D:D',37)
            sheet.set_column('E:E',15)
            sheet.set_column('F:F',15)

            sheet.set_row(17,15)
            sheet.write(9,0,'Sl.No:',format_3)
            sheet.write(9,1,'Date:',format_3)
            sheet.write(9,2,'Reference:',format_3)
            sheet.write(9,3,'Partner:',format_3)
            sheet.write(9,4,'Debit:',format_3)
            sheet.write(9,5,'Credit:',format_3)

            row=10
            sl_no=0

            for lines in obj.statement_lines.filtered(lambda line: not line.statement_date):
                sl_no +=1

                sheet.write(row,0, sl_no,format_7)
                sheet.write(row,1, lines.date.strftime('%d-%m-%Y'),format_7)
                sheet.write(row,2, lines.ref or '')
                sheet.write(row,3, lines.partner_id.name or '')
                sheet.write(row,4, lines.debit or '',format_7)
                sheet.write(row,5, lines.credit or '',format_7)
                row+=1

