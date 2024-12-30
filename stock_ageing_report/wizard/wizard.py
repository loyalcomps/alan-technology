# -*- coding: utf-8 -*-
##############################################################################
#
#    DevIntelle Solution(Odoo Expert)
#    Copyright (C) 2015 Devintelle Soluation (<http://devintelle.com/>)
#
##############################################################################
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import except_orm

import xlsxwriter
from io import BytesIO

try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes


class StockAgeing(models.TransientModel):
    _name = 'stock.ageing'
    _description = 'Stock Ageing Report'

    period_length = fields.Integer('Period Length (days)', default=30)
    product_id = fields.Many2one('product.product', 'Product')
    product_category_id = fields.Many2one('product.category', 'Product Category')
    kg_brand_id = fields.Many2one('kg.product.brand', 'Brand')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    location_id = fields.Many2one('stock.location', 'Location')
    company_id = fields.Many2one('res.company', 'Company')
    date_from = fields.Date('Date', default=lambda *a: time.strftime('%Y-%m-%d'))

    fileout = fields.Binary('File', readonly=True)
    fileout_filename = fields.Char('Filename', readonly=True)

    def print_ageing_pdf_report(self):
        data = {
            'form': self.read()[0],
        }
        company_id = data['form']['company_id'][1]
        res = {}
        period_length = data['form']['period_length']
        if period_length <= 0:
            raise except_orm(_('User Error!'), _('You must set a period length greater than 0.'))
        if not data['form']['date_from']:
            raise except_orm(_('User Error!'), _('You must set a start date.'))

        start = data['form']['date_from']
        for i in range(7)[::-1]:
            stop = start - relativedelta(days=period_length)
            res[str(i)] = {
                'name': (i != 0 and (str((7 - (i + 1)) * period_length) + '-' + str((7 - i) * period_length)) or (
                        '+' + str(6 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        data['form'].update(res)
        return self.env.ref('stock_ageing_report.action_stock_ageing_report').report_action(self, data=data)

    @api.model
    def get_lines(self, form):
        res = []
        quant_obj = self.env.get('stock.quant')
        product_category_id = []
        kg_brand_id = []
        if form.get('kg_brand_id'):
            kg_brand_id = form['kg_brand_id'][0]
        if form.get('product_category_id'):
            product_category_id = form['product_category_id'][0]
        product_obj = self.env.get('product.product')
        if product_category_id:
            products = product_obj.search([('categ_id', '=', product_category_id)])
        else:
            products = product_obj.search([])
        product_ids = products._ids
        if form.get('product_id', False) and form['product_id'][0] in product_ids:
            wizard_product_id = form['product_id'][0]
            product_ids = [wizard_product_id]
        for product in product_obj.browse(product_ids):
            product_dict = {
                'pname': product.name
            }
            location_id = form['location_id'][0]
            date_from = form['date_from']
            ctx = self._context.copy()
            ctx.update({
                'location': location_id,
                'from_date': date_from,
                'to_date': date_from
            })
            product_qty = product._product_available()
            qty_list = product_qty.get(product.id)
            product_dict.update({
                'onhand_qty': qty_list['qty_available'],
            })
            for data in range(0, 7):
                total_qty = 0
                if form.get(str(data)):
                    start_date = form.get(str(data)).get('start')
                    stop_date = form.get(str(data)).get('stop')
                    if not start_date:
                        domain = [('in_date', '<=', stop_date), ('location_id', '=', location_id),
                                  ('product_id', '=', product.id)]
                    else:
                        domain = [('in_date', '<=', stop_date), ('in_date', '>=', start_date),
                                  ('location_id', '=', location_id), ('product_id', '=', product.id)]

                    for quant in quant_obj.search(domain):
                        total_qty += quant.quantity
                    product_dict[str(data)] = total_qty
            res.append(product_dict)
            print("res", res)
        return res

    def print_xlsx(self):
        active_ids_tmp = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')
        data = {
            'form': self.read()[0],
            'ids': active_ids_tmp,
            'context': {'active_model': active_model},
        }
        company_id = data['form']['company_id'][1]
        res = {}
        period_length = data['form']['period_length']
        if period_length <= 0:
            raise except_orm(_('User Error!'), _('You must set a period length greater than 0.'))
        if not data['form']['date_from']:
            raise except_orm(_('User Error!'), _('You must set a start date.'))

        start = data['form']['date_from']
        for i in range(7)[::-1]:
            stop = start - relativedelta(days=period_length)
            res[str(i)] = {
                'name': (i != 0 and (str((7 - (i + 1)) * period_length) + '-' + str((7 - i) * period_length)) or (
                        '+' + str(6 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        data['form'].update(res)
        file_io = BytesIO()
        workbook = xlsxwriter.Workbook(file_io)

        self.generate_xlsx_report(workbook, data=data)

        workbook.close()
        fout = encodebytes(file_io.getvalue())

        datetime_string = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = 'Inventory Ageing Report'
        filename = '%s_%s' % (report_name, datetime_string)
        self.write({'fileout': fout, 'fileout_filename': filename})
        file_io.close()
        filename += '%2Exlsx'

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=fileout&download=true&filename=' + filename,
        }

    def generate_xlsx_report(self, workbook, data=None, objs=None):
        date_style = workbook.add_format({'text_wrap': True, 'num_format': 'dd-mm-yyyy'})
        sheet = workbook.add_worksheet("Inventory Ageing Report")
        align = workbook.add_format({'font_size': '10px', 'align': 'center', 'border': 1})
        cell_format = workbook.add_format({'font_size': '12px', 'bold': True})
        heading = workbook.add_format({'font_size': '10px', 'align': 'center', 'border': 1, 'bold': True})
        head = workbook.add_format({'align': 'center', 'bold': True, 'font_size': '20px', 'font_color': 'red'})
        txt = workbook.add_format({'align': 'center', 'font_size': '10px'})
        sheet.merge_range('B2:P3', 'Inventory Ageing Report', head)
        sheet.write('B6', 'Company:', cell_format)
        sheet.merge_range('D6:G6', data['form']['company_id'][1], cell_format)
        sheet.write('B7', 'Warehouse:', cell_format)
        sheet.merge_range('D7:G7', data['form']['warehouse_id'][1], cell_format)
        sheet.merge_range('B8:D8', 'Period Length (days):', cell_format)
        sheet.merge_range('D8:E8', data['form']['period_length'], cell_format)
        sheet.write('B9', 'Start Date:', cell_format)
        sheet.merge_range('D9:E9', data['form']['date_from'], date_style)
        sheet.write('B10', 'Location:', cell_format)
        sheet.merge_range('D10:H10', data['form']['location_id'][1], cell_format)
        sheet.write('B11', 'Product Category:', cell_format)
        sheet.merge_range('D11:E11', data['form']['product_category_id'][1], cell_format)
        sheet.merge_range('C13:D13', 'Product', heading)
        sheet.write(12, 4, data['form']['6']['name'], heading)
        sheet.write(12, 5, data['form']['5']['name'], heading)
        sheet.write(12, 6, data['form']['4']['name'], heading)
        sheet.write(12, 7, data['form']['3']['name'], heading)
        sheet.write(12, 8, data['form']['2']['name'], heading)
        sheet.write(12, 9, data['form']['1']['name'], heading)
        sheet.write(12, 10, data['form']['0']['name'], heading)
        sheet.write(12, 11, 'Total', heading)

        line = self.get_lines(data['form'])
        if line:
            i = 6
            for product in line:
                if product.get('onhand_qty', 0) and product.get('onhand_qty', 0) > 0:
                    sheet.merge_range(i + 7, 2, i + 7, 3, product['pname'], align)
                if product.get('onhand_qty', 0) != 0 and product.get('onhand_qty', 0) > 0 and (
                        product['0'] > 0 or product['1'] > 0 or product['2'] > 0 or product['3'] > 0 or product[
                    '4'] > 0 or product['5'] > 0 or product['6'] > 0):
                    sheet.write(i + 7, 4, product['6'], align)
                else:
                    sheet.write(i + 7, 4, product['6'], align)
                if product.get('onhand_qty', 0) != 0 and product.get('onhand_qty', 0) > 0 and (
                        product['0'] > 0 or product['1'] > 0 or product['2'] > 0 or product['3'] > 0 or product[
                    '4'] > 0 or product['5'] > 0 or product['6'] > 0):
                    sheet.write(i + 7, 5, product['5'], align)
                else:
                    sheet.write(i + 7, 5, product['5'], align)
                if product.get('onhand_qty', 0) != 0 and product.get('onhand_qty', 0) > 0 and (
                        product['0'] > 0 or product['1'] > 0 or product['2'] > 0 or product['3'] > 0 or product[
                    '4'] > 0 or product['5'] > 0 or product['6'] > 0):
                    sheet.write(i + 7, 7, product['3'], align)
                else:
                    sheet.write(i + 7, 7, product['3'], align)
                if product.get('onhand_qty', 0) != 0 and product.get('onhand_qty', 0) > 0 and (
                        product['0'] > 0 or product['1'] > 0 or product['2'] > 0 or product['3'] > 0 or product[
                    '4'] > 0 or product['5'] > 0 or product['6'] > 0):
                    sheet.write(i + 7, 6, product['4'], align)
                else:
                    sheet.write(i + 7, 6, product['4'], align)
                if product.get('onhand_qty', 0) != 0 and product.get('onhand_qty', 0) > 0 and (
                        product['0'] > 0 or product['1'] > 0 or product['2'] > 0 or product['3'] > 0 or product[
                    '4'] > 0 or product['5'] > 0 or product['6'] > 0):
                    sheet.write(i + 7, 8, product['2'], align)
                else:
                    sheet.write(i + 7, 8, product['2'], align)
                if product.get('onhand_qty', 0) and product.get('onhand_qty', 0) > 0 and (
                        product['0'] > 0 or product['1'] > 0 or product['2'] > 0 or product['3'] > 0 or product[
                    '4'] > 0 or product['5'] > 0 or product['6'] > 0):
                    sheet.write(i + 7, 9, product['1'], align)
                else:
                    sheet.write(i + 7, 9, product['1'], align)
                if product.get('onhand_qty', 0) and product.get('onhand_qty', 0) > 0 and (
                        product['0'] > 0 or product['1'] > 0 or product['2'] > 0 or product['3'] > 0 or product[
                    '4'] > 0 or product['5'] > 0 or product['6'] > 0):
                    sheet.write(i + 7, 10, product['0'], align)
                else:
                    sheet.write(i + 7, 10, product['0'], align)
                if product.get('onhand_qty', 0) != 0:
                    sheet.write(i + 7, 11, product['onhand_qty'], align)
                i += 1
        workbook.close()


class Product(models.Model):
    _inherit = "product.product"

    def _product_available(self, field_names=None, arg=False):
        """ Compatibility method """
        return self._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'),
                                             self._context.get('package_id'), self._context.get('from_date'),
                                             self._context.get('to_date'))
