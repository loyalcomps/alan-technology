# -*- coding: utf-8 -*-
import time
from odoo import models, fields, api, _
from odoo.exceptions import except_orm


class StockMovementAnalysis(models.TransientModel):
    _name = 'stock.movement.analysis'
    _description = 'Stock  Report'

    type = fields.Selection([
        ('categories', 'Categories'),
        ('brand', 'Brand'), ('item', 'Item')], string='Report Based On', default='categories')
    product_id = fields.Many2one('product.product', 'Product')
    brand_id = fields.Many2one('kg.product.brand', 'Brand')
    product_category_id = fields.Many2one('product.category', 'Product Category')
    date_to = fields.Date('Date To', default=lambda *a: time.strftime('%Y-%m-%d'))
    date_from = fields.Date('Date From', default=lambda *a: time.strftime('%Y-%m-%d'))

    @api.onchange('type')
    def _onchange_type(self):
        self.product_id = None
        self.brand_id = None
        self.product_category_id = None

    def print_report(self):
        data = {
            'form': self.read()[0],
        }
        period_from = data['form']['date_from']
        period_to = data['form']['date_to']
        if not data['form']['date_from']:
            raise except_orm(_('User Error!'), _('You must set a start date.'))
        if not data['form']['date_to']:
            raise except_orm(_('User Error!'), _('You must set a end date.'))
        period_from = fields.Datetime.from_string(data['form']['date_from'])
        period_to = fields.Datetime.from_string(data['form']['date_to'])
        period_length = (period_to - period_from).days
        if period_length <= 0:
            raise except_orm(_('User Error!'), _('You must set a period length greater than 0.'))
        ans = {}
        end = {}
        start_date = data['form']['date_from']
        stop_date = data['form']['date_to']
        quant_obj = self.env.get('stock.move')
        res = []
        result = []
        product_category_id = []
        product_brand_id = []
        if data['form'].get('product_category_id'):
            product_category_id = data['form']['product_category_id'][0]
        if data['form'].get('brand_id'):
            product_brand_id = data['form']['brand_id'][0]
        product_obj = self.env.get('product.product')
        prd = self.env['product.product'].search([('name','like','Lenovo L24e-30 – 23.8″ inch, VGA+HDMI, FHD Monitor')])
        print("hhhhhhhhhhhhhhhhhh",prd)
        if product_category_id:
            products = prd
            print("products-------->>",products)
        elif product_brand_id:
            products = product_obj.search([('kg_brand_id', '=', product_brand_id)])
        else:
            products = product_obj.search([])
        product_ids = products._ids
        if data['form'].get('product_id', False) and data['form']['product_id'][0] in product_ids:
            wizard_product_id = data['form']['product_id'][0]
            product_ids = [wizard_product_id]

        if self.type != 'item':
            print("inside--------------->>>>1")
            for product in product_obj.browse(product_ids):
                product_dict = {}
                domain = [('date', '<=', stop_date), ('date', '>=', start_date), ('product_id', '=', product.id)]
                total_in_qty = 0.00
                total_in_cost = 0.00
                unit_in_price = 0.00
                total_out_qty = 0.00
                total_out_cost = 0.00
                unit_out_price = 0.00
                product_dict = {
                    'pname': product.name
                }
                for quant in quant_obj.search(domain):
                    if quant.picking_id.state == 'done':
                        if quant.picking_type_id.name == 'Receipts':
                            cost_total = 0.00
                            for n in quant.purchase_line_id.order_id.order_line:
                                cost_total += n.price_subtotal
                                unit_in_price = n.price_unit
                            total_in_qty += quant.product_uom_qty
                            total_in_cost += cost_total
                        if quant.picking_type_id.name == 'Delivery Orders':
                            cost_total = 0.00
                            for m in quant.picking_id.kg_invoice_id.invoice_line_ids:
                                if m.product_id.id == product.id:
                                    cost_total += m.price_subtotal
                                    unit_out_price = m.price_unit
                            total_out_qty += quant.product_uom_qty
                            total_out_cost += cost_total
                product_dict.update({'in_qty': total_in_qty,
                                     'in_cost': unit_in_price,
                                     'in_amount': total_in_cost,
                                     'out_qty': total_out_qty,
                                     'out_cost': unit_out_price,
                                     'out_amount': total_out_cost})
                res.append(product_dict)
            in_qty_total = 0.00
            in_amount_total = 0.00
            out_qty_total = 0.00
            out_amount_total = 0.00
            for i in res:
                in_qty_total += i['in_qty']
                in_amount_total += i['in_amount']
                out_qty_total += i['out_qty']
                out_amount_total += i['out_amount']
            ans.update({
                'in_qty_total': in_qty_total,
                'in_amount_total': in_amount_total,
                'out_qty_total': out_qty_total,
                'out_amount_total': out_amount_total})
            result.append(ans)
            data.update({'res': res})
            data.update({'result': result})
        if self.type == 'item':
            for product in product_obj.browse(product_ids):
                domain = [('date', '<=', stop_date), ('date', '>=', start_date), ('product_id', '=', product.id)]
                in_qty = 0.00
                in_cost = 0.00
                unit_in_price = 0.00
                out_qty = 0.00
                out_cost = 0.00
                unit_out_price = 0.00
                for quant in quant_obj.search(domain):
                    product_dict = {}
                    if quant.picking_id.state == 'done':
                        if quant.picking_type_id.name == 'Receipts':
                            cost_total = 0.00
                            for n in quant.purchase_line_id.order_id.order_line:
                                cost_total += n.price_subtotal
                                unit_in_price = n.price_unit
                            supplier = quant.picking_id.partner_id.name
                            in_qty = quant.product_uom_qty
                            in_cost = cost_total
                            product_dict.update({'supplier': supplier,
                                                 'basic_cost': product.standard_price,
                                                 'in_qty': in_qty,
                                                 'in_cost': unit_in_price,
                                                 'in_amount': in_cost,
                                                 })
                            res.append(product_dict)
                        if quant.picking_type_id.name == 'Delivery Orders':
                            cost_total = 0.00
                            for m in quant.picking_id.kg_actual_invoice_id.invoice_line_ids:
                                if m.product_id.id == product.id:
                                    cost_total += m.price_subtotal
                                    unit_out_price = m.price_unit
                            buyer = quant.picking_id.partner_id.name
                            out_qty = quant.product_uom_qty
                            out_cost = cost_total
                            product_dict.update({'buyer': buyer,
                                                 'out_qty': out_qty,
                                                 'out_cost': unit_out_price,
                                                 'out_amount': out_cost, })
                            res.append(product_dict)
                        data.update({'res': res})

        return self.env.ref('stock_movement_analysis_report.action_stock_movement_analysis_report').report_action(self,
                                                                                                                  data=data)
