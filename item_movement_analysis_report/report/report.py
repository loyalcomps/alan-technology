# -*- coding: utf-8 -*-

# import time
from odoo import api, models


# from dateutil.parser import parse
# from odoo.exceptions import UserError
# from odoo.http import request
# from odoo.tools import date_utils
# from odoo.tools.safe_eval import json


# from odoo.tools import json, date_utils


class ItemReport(models.AbstractModel):
    _name = 'report.item_movement_analysis_report.item_report'

    '''Find Outstanding invoices between the date and find total outstanding amount'''

    @api.model
    def _get_report_values(self, docids, data=None):
        # model = self.env.context.get('active_model')
        docs = self.env['item.movement.analysis'].browse(self.env.context.get('active_id'))
        # print("model:", model)
        print("docs:", docs)
        full_report = []
        for product in docs.product_ids:
            print(" docs.products:", docs.product_ids)
            full_report_child = {}
            ##suppliers
            res = self.env.cr.execute(
                """select to_char(account_move.invoice_date, 'DD/MM/YYYY') as invoice_date,
                          account_move.name as number,
                          account_move.partner_id,
                          TRUNC(sum(account_move_line.price_subtotal),3) as Value,
                          TRUNC(sum(account_move_line.quantity),3) as Quantity,
                          TRUNC(AVG(account_move_line.price_unit),3) as unit from account_move_line 
                          JOIN account_move ON account_move_line.move_id = account_move.id
                          where account_move.move_type IN ('out_invoice','out_refund') and 
                                account_move.payment_state IN ('in_payment','paid') and 
                                account_move_line.product_id = %s and account_move.invoice_date >= %s and 
                                account_move.invoice_date <=%s 
                                GROUP BY account_move_line.partner_id,account_move.id order by account_move.invoice_date ASC""",
                (product.id, docs.start_date, docs.end_date,))
            print("res----------------->>", res)

            outward_items = []
            for count, item in enumerate(self.env.cr.dictfetchall()):
                print("inward:", self.env.cr.dictfetchall())

                a = {}
                partner_name = self.env['res.partner'].browse([item['partner_id']]).name
                print("inward_partner", partner_name)
                a['name'] = partner_name
                a['qty'] = item['quantity'] or 0
                a['unit'] = item['unit'] or 0
                a['value'] = item['value'] or 0
                a['number'] = item['number']
                a['invoice_date'] = item['invoice_date']
                outward_items.append(a)
                self.env.cr.execute("""select TRUNC(sum(account_move_line.price_subtotal),3) as Value,
                                              TRUNC(sum(account_move_line.quantity),3) as Quantity,
                                              TRUNC(AVG(account_move_line.price_unit),3) as unit from account_move_line 
                                              JOIN account_move ON account_move_line.move_id = account_move.id
                                              where account_move.move_type IN ('out_invoice','out_refund') and 
                                                    account_move.payment_state IN ('in_payment','paid') and 
                                                    account_move_line.product_id = %s and 
                                                    account_move.invoice_date >= %s and 
                                                    account_move.invoice_date <=%s""",
                                    (product.id, docs.start_date, docs.end_date,))

            for count, item in enumerate(self.env.cr.dictfetchall()):
                a = {}

                a['name'] = ''
                a['qty'] = item['quantity'] or 0
                a['unit'] = item['unit'] or 0
                a['value'] = item['value'] or 0
                a['number'] = ''
                a['invoice_date'] = False
                outward_items.append(a)
                self.env.cr.execute(
                    """select to_char(account_move.invoice_date, 'DD/MM/YYYY') as invoice_date,
                              account_move.name as number,account_move_line.partner_id,
                              TRUNC(sum(account_move_line.price_subtotal),3) as Value,
                              TRUNC(sum(account_move_line.quantity),3) as Quantity,
                              TRUNC(AVG(account_move_line.price_unit),3) as unit from account_move_line
                              JOIN account_move ON account_move_line.move_id = account_move.id
                              where account_move.move_type in ('in_invoice','in_refund') and
                                    account_move.payment_state IN ('in_payment','paid') and
                                    account_move_line.product_id = %s and
                                    account_move.invoice_date >= %s and
                                    account_move.invoice_date <=%s
                                    GROUP BY account_move_line.partner_id,account_move.id order by account_move.invoice_date ASC""",
                    (product.id, docs.start_date, docs.end_date,))

            inward_items = []
            for count, item in enumerate(self.env.cr.dictfetchall()):
                print("outward:", self.env.cr.dictfetchall())

                a = {}
                partner_name = self.env['res.partner'].browse([item['partner_id']]).name
                print("outward_partner", partner_name)
                a['name'] = partner_name
                a['qty'] = item['quantity'] or 0
                a['unit'] = item['unit'] or 0
                a['value'] = item['value'] or 0
                a['number'] = item['number']
                a['invoice_date'] = item['invoice_date']
                inward_items.append(a)
                self.env.cr.execute(
                    """select TRUNC(sum(account_move_line.price_subtotal),3) as Value,
                              TRUNC(sum(account_move_line.quantity),3) as Quantity,
                              TRUNC(AVG(account_move_line.price_unit),3) as unit from account_move_line 
                              JOIN account_move ON account_move_line.move_id = account_move.id
                              where account_move.move_type in ('in_invoice','in_refund') and 
                                    account_move.payment_state IN ('in_payment','paid') and 
                                    account_move_line.product_id = %s and 
                                    account_move.invoice_date >= %s and 
                                    account_move.invoice_date <=%s""",
                    (product.id, docs.start_date, docs.end_date,))
            for count, item in enumerate(self.env.cr.dictfetchall()):
                a = {}

                a['name'] = ''
                a['qty'] = item['quantity'] or 0
                a['unit'] = item['unit'] or 0
                a['value'] = item['value'] or 0
                a['number'] = ''
                a['invoice_date'] = False
                inward_items.append(a)
                # self.env.cr.execute(
                #     """select to_char(account_move.invoice_date, 'DD/MM/YYYY') as invoice_date,
                #               account_move.name as number,account_move_line.partner_id,
                #               TRUNC(sum(account_move_line.price_subtotal),3) as Value,
                #               TRUNC(sum(account_move_line.quantity),3) as Quantity,
                #               TRUNC(AVG(account_move_line.price_unit),3) as unit from account_move_line
                #               JOIN account_move ON account_move_line.move_id = account_move.id
                #               where account_move.move_type in ('out_invoice','in_refund') and
                #                     account_move.payment_state IN ('in_payment','paid') and
                #                     account_move_line.product_id = %s and
                #                     account_move.invoice_date >= %s and
                #                     account_move.invoice_date <=%s
                #                     GROUP BY account_move_line.partner_id,account_move.id order by account_move.invoice_date ASC""",
                #     (product.id, docs.start_date, docs.end_date,))
            full_report_child['product_name'] = product.name
            full_report_child['inward_items'] = inward_items
            full_report_child['outward_items'] = outward_items
            full_report.append(full_report_child)
            print("full_report", full_report)

            result = {
                'docs': docs,

                'items': full_report,
            }
            print("result", result)
            return result
