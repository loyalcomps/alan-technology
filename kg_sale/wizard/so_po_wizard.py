from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang


class KGSoPoWizard(models.TransientModel):
    _name = 'kg.so.po.wizard'
    _description = 'kg.so.po.wizard'

    def select_all(self):
        print("select all")
        select_wiz_line = self.wiz_line
        for sel in select_wiz_line:
            if sel.sale_id.display_type not in ['line_section','line_note']:
                sel.select = True
        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'kg.so.po.wizard',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def delete(self):
        wiz_line = self.wiz_line

        for line in wiz_line:
            if line.select:
                line.unlink()

        return {
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'kg.so.po.wizard',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    # def create_po(self):
    #     wiz_line = self.wiz_line
    #     if not wiz_line:
    #         raise UserError(_('no lines found for generating PO'))
    #     partner_id = self.supplier_id and self.supplier_id.id
    #     line_vals_array = []
    #     so_id = self.sale_order_id and self.sale_order_id.id
    #     date_order = self.sale_order_id.date_order
    #     payment_term_id = self.payment_term_id and self.payment_term_id.id
    #     select_ids= wiz_line.mapped('select')
    #
    #     for line in wiz_line:
    #         print(line.name,'lineeeeeeeeeeeeeeeeeeeee')
    #
    #         product_id = line.product_id and line.product_id.id
    #         name = line.name
    #         product_uom = line.product_uom and line.product_uom.id
    #         tax_ids = []
    #         if line.tax_id:
    #             tax_ids.append(line.tax_id and line.tax_id.id or False)
    #         product_qty = line.qty
    #         price_unit = line.unit_price
    #
    #         if line.product_id.type not in ('service', 'consu'):
    #             if any(select_ids):
    #                 line_vals = (0, 0, {'product_id': product_id, 'product_qty': product_qty, 'price_unit': price_unit,
    #                                     'product_uom': product_uom, 'name': name, 'date_planned': date_order,
    #                                     'taxes_id': [(6, 0, tax_ids)]})
    #
    #                 line_vals_array.append(line_vals)
    #                 print(line_vals_array,'lkjjhgddhhhhhhhhhhh')
    #             else:
    #                 raise ValidationError(_('Select atleast one product'))
    #
    #     vals = {'partner_id': partner_id, 'order_line': line_vals_array, 'kg_sale_order_id': so_id,
    #             'payment_term_id': payment_term_id}
    #     purchase_order_obj = self.env['purchase.order'].create(vals)
    #     purchase_line = self.sale_order_id and self.sale_order_id.kg_purchase_order_lines
    #     lpo = ''
    #     for line in purchase_line:
    #         lpo = lpo + "," + line.name
    #
    #     lpo = lpo[1:]
    #     self.sale_order_id.kg_lpos = lpo
    #     sale_qty = self.sale_order_id.order_line.product_uom_qty
    #     po_qty = self.wiz_line.qty
    #     if sale_qty == po_qty:
    #         self.sale_order_id.kg_invoice_status_1 = 'lpo_created'
    #     else:
    #         self.sale_order_id.kg_invoice_status_1 = 'lpo_created_p'
    #     return True
    def create_po(self):
        wiz_line = self.wiz_line

        if not wiz_line:
            raise ValidationError(_('No lines found for generating PO'))

        # Check if any line has select set to True
        if not any(line.select for line in wiz_line):
            raise ValidationError(_('Select at least one product'))

        partner_id = self.supplier_id and self.supplier_id.id
        line_vals_array = []
        so_id = self.sale_order_id and self.sale_order_id.id
        date_order = self.sale_order_id.date_order
        payment_term_id = self.payment_term_id and self.payment_term_id.id
        sale_order_id = []
        for sale_order in self.kg_sale_order_id:
            sale_order_id.append(sale_order.id)

        for line in wiz_line:
            if line.select:

                product_id = line.product_id and line.product_id.id
                name = line.name
                product_uom = line.product_uom and line.product_uom.id
                tax_ids = [(6, 0, line.tax_id.ids)] if line.tax_id else False
                product_qty = line.qty
                price_unit = line.unit_price

                if line.product_id.type not in ('service', 'consu'):
                    line_vals = {
                        'product_id': product_id,
                        'product_qty': product_qty,
                        'price_unit': price_unit,
                        'product_uom': product_uom,
                        'name': name,
                        'date_planned': date_order,
                        'taxes_id': tax_ids
                    }
                    line_vals_array.append((0, 0, line_vals))

        if not line_vals_array:
            raise ValidationError(_('Select atleast one product'))

        vals = {
            'partner_id': partner_id,
            'order_line': line_vals_array,
            'kg_sale_order_id': sale_order_id,
            'payment_term_id': payment_term_id
        }
        purchase_order_obj = self.env['purchase.order'].create(vals)

        purchase_line = self.sale_order_id and self.sale_order_id.kg_purchase_order_lines
        lpo = ','.join(line.name for line in purchase_line)

        self.sale_order_id.kg_lpos = lpo
        for sale in self.kg_sale_order_id:
            sale_qty = sum(sale_line.product_uom_qty for sale_line in sale.order_line)
            po_qty = sum(line.qty for line in wiz_line if line.select and line.sale_id.order_id == sale)
            if sale_qty == po_qty:
                sale.kg_invoice_status_1 = 'lpo_created'
            else:
                sale.kg_invoice_status_1 = 'lpo_created_p'
        list_po = []
        for related_po in self.kg_sale_order_id.kg_purchase_order_lines:
            if related_po:
                list_po.append(related_po.name)
        po_string = ', '.join(list_po)
        self.kg_sale_order_id.picking_ids.kg_po_ref = po_string

        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': purchase_order_obj.id,
            'target': 'current'
        }

    @api.model
    def default_get(self, fields_list):
        res = super(KGSoPoWizard, self).default_get(fields_list)
        active_sale_order_ids = self._context.get('active_ids', [])
        line_vals_array = []
        for active in active_sale_order_ids:
            sale_obj = self.env['sale.order'].browse(active)
            sale_line = sale_obj.order_line
            currency_id = sale_obj.currency_id and sale_obj.currency_id.id
            for line in sale_line:
                product_id = line.product_id and line.product_id.id
                product_uom_qty = line.product_uom_qty
                name = line.name
                product_uom = line.product_uom and line.product_uom.id
                purchase_price = line.purchase_price
                tax_id = line.tax_id
                sale_id = line.id
                if line.product_id.type not in ('service', 'consu'):
                    vals = (0, 0,
                            {'product_id': product_id, 'qty': product_uom_qty, 'sale_id': sale_id,
                             'unit_price': purchase_price, 'name': name,
                             'product_uom': product_uom, 'tax_id': tax_id})
                    line_vals_array.append(vals)
        res.update({'sale_order_id': sale_obj.id, 'wiz_line': line_vals_array, 'currency_id': currency_id})
        return res

    wiz_line = fields.One2many('kg.so.po.wizard.line', 'wiz_id', string='Wiz Line', )
    supplier_id = fields.Many2one('res.partner', string='Vendor')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    kg_sale_order_id = fields.Many2many('sale.order', string='Sale Order')
    currency_id = fields.Many2one('res.currency', string='Currency')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term')


class KGSoPoWizardLine(models.TransientModel):
    _name = 'kg.so.po.wizard.line'
    _description = 'kg.so.po.wizard.line'

    wiz_id = fields.Many2one('kg.so.po.wizard', string='Wiz')
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(string='Description', )
    qty = fields.Integer(string="Qty")
    unit_price = fields.Float(string="Cost")
    sale_id = fields.Many2one('sale.order.line', string='Sale order')
    tax_id = fields.Many2one('account.tax', string='Vat')
    product_uom = fields.Many2one('uom.category', string='Product Unit of Measure')
    display_type = fields.Selection(related="sale_id.display_type")
    select = fields.Boolean('Select')
