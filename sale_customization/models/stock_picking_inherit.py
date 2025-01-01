from odoo import models, fields , api,_

class StockPickingInherit(models.Model):
    _inherit='stock.picking'

    def create_invoice_from_delivery(self):

        for picking_id in self:
            current_user = self.env.uid
            if picking_id.picking_type_id.code == 'outgoing':
                invoice_line_list = []
                for move_ids_without_package in picking_id.move_ids_without_package:
                    vals = (0, 0, {
                        'name': move_ids_without_package.description_picking,
                        'product_id': move_ids_without_package.product_id.id,
                        'price_unit': move_ids_without_package.sale_line_id.price_unit,

                        'account_id': move_ids_without_package.product_id.property_account_income_id.id if move_ids_without_package.product_id.property_account_income_id
                        else move_ids_without_package.product_id.categ_id.property_account_income_categ_id.id,

                        'tax_ids': move_ids_without_package.sale_line_id.tax_id.ids,
                        'quantity': move_ids_without_package.quantity_done,
                        'description':move_ids_without_package.description,
                    })
                    invoice_line_list.append(vals)
                invoice = picking_id.env['account.move'].create({
                    'move_type': 'out_invoice',
                    'invoice_origin': picking_id.name,
                    'invoice_user_id': current_user,
                    'narration': picking_id.name,
                    'partner_id': picking_id.partner_id.id,
                    'currency_id': picking_id.env.user.company_id.currency_id.id,
                    'kg_so_id': picking_id.kg_sale_order_id.id,
                    'kg_bank_id': self.sale_id.bank_id.id,
                    'payment_reference': picking_id.name,
                    'picking_id': picking_id.id,
                    'invoice_line_ids': invoice_line_list
                })
                picking_id.update({'kg_invoice_id': invoice.id})
                so = picking_id.kg_sale_order_id
                so.update({'invoice_ids': [(4, invoice.id)]})
                delivery_qty = sum(self.sale_id.picking_ids.filtered(lambda p: p.state == 'done').mapped(
                    'move_line_ids_without_package').mapped('qty_done'))
                sale_qty = sum(self.sale_id.order_line.mapped('product_uom_qty'))
                if sale_qty == delivery_qty:
                    self.sale_id.kg_invoice_status_1 = 'invoiced'
                else:
                    self.sale_id.kg_invoice_status_1 = 'invoice_p'
                if self.kg_po_ref:
                    self.kg_invoice_id.kg_another_ref = self.kg_po_ref
                return invoice
