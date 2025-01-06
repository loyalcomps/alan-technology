# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, api, fields, _

# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import datetime


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    #
    # _order = "kg_serial_no asc"
    #
    kg_optional = fields.Boolean(string="Optional")
    kg_supplier_id = fields.Many2one('res.partner', 'Supplier')
    kg_po_ref = fields.Char(string="PO")
    kg_brand_id = fields.Many2one('kg.product.brand', 'Brand')
    kg_is_it_tranpcharge = fields.Boolean('Other Cost')
    kg_serial_no = fields.Float('S.NO')
    kg_categ_id = fields.Many2one('product.category', 'Category')
    #
    kg_subheading = fields.Boolean(string="Subheading")

    #
    @api.depends('product_id', 'purchase_price', 'product_uom_qty', 'price_unit', 'kg_is_it_tranpcharge', 'kg_optional',
                 'price_unit')
    def _product_margin(self):
        for line in self:
            # print("margin tyest")
            if not line.kg_is_it_tranpcharge and not line.kg_optional:
                currency = line.order_id.pricelist_id.currency_id
                line.margin = currency.round(line.price_subtotal - (
                        (line.purchase_price or line.product_id.standard_price) * line.product_uom_qty))
                # print(line.margin,"mmmmmmmmmmmmmmmmm")

    #
    #     @api.multi
    #     def _prepare_invoice_line(self, qty):
    #         result = super(SaleOrderLine, self)._prepare_invoice_line(qty)
    #         if self.kg_is_it_tranpcharge:
    #             result['kg_is_it_tranpcharge'] = self.kg_is_it_tranpcharge
    #         return result
    #

    def open_cost_history(self):
        action = self.env.ref('kg_sale.action_kg_product_cost_history').read()[0]
        product_id = self.product_id and self.product_id.id
        if not product_id:
            raise UserError(_('select the product first'))

        domain = []
        domain.append(('product_id', '=', product_id))
        action['domain'] = domain

        action['context'] = {

            'default_product_id': product_id
        }

        return action

    def kg_add_to_pricelist(self):
        history = self.env['kg.product.cost.history']
        product_id = self.product_id and self.product_id.id
        supplier_id = self.kg_supplier_id and self.kg_supplier_id.id
        cost = self.purchase_price

        history.create({'product_id': product_id, 'supplier_id': supplier_id, 'cost': cost})
        return True


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_branch_domain(self):
        """method to get bank domain"""
        company = self.env.company
        partner = company.partner_id
        bank = []
        for rec in partner.bank_ids:
            bank.append(rec.bank_id.id)
        return [('id', 'in', bank)]

    pro_seq = fields.Char(string="Proforma Sequence", copy=False)
    bank_id = fields.Many2one('res.bank', string='Bank', domain=_get_branch_domain)

    def action_unlock(self):
        res = super(SaleOrder, self).action_unlock()
        for rec in self:
            account = self.env['account.move'].search([('move_type', '=', 'out_invoice'), ('kg_so_id', '=', rec.id)])
            if account:
                account_qty = sum(account.mapped('invoice_line_ids').mapped('quantity'))
                sale_qty = sum(account.kg_so_id.order_line.mapped('product_uom_qty'))
                if sale_qty == account_qty:
                    rec.kg_invoice_status_1 = 'invoiced'
                else:
                    rec.kg_invoice_status_1 = 'invoice_p'
            elif rec.pro_seq:
                rec.kg_invoice_status_1 = 'proforma_invoice'
            else:
                rec.kg_invoice_status_1 = 'draft'
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for order in self:
            if order:
                raise UserError(_(
                    "You can not delete a sent quotation or a confirmed sales order."))

    def proforma_invoice_gen_seq(self):
        print("tested------sale")
        for order in self:
            order.kg_invoice_status_1 = 'proforma_invoice'
            sequence = self.env['ir.sequence'].sudo().next_by_code('proforma.inv') or _('New')
            order.write({'pro_seq': sequence})
            print("sequence-->", self.env['ir.sequence'].sudo().next_by_code('proforma.invoice'))

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.partner_customer_type = self.partner_id.customer_type
        else:
            self.partner_customer_type = False

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total','order_line.kg_optional','order_line.kg_is_it_tranpcharge')
    def _compute_amounts(self):
        """Compute the total amounts of the SO."""
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.amount_untaxed = sum(order_lines.filtered(lambda x: not x.kg_optional and not x.kg_is_it_tranpcharge).mapped('price_subtotal'))
            order.amount_total = sum(order_lines.filtered(lambda x: not x.kg_optional and not x.kg_is_it_tranpcharge).mapped('price_total'))
            order.amount_tax = sum(order_lines.filtered(lambda x: not x.kg_optional and not x.kg_is_it_tranpcharge).mapped('price_tax'))


    # @api.model
    # def create(self, vals):
    #     if vals.get('kg_invoice_status_1') == 'proforma_invoice':
    #         vals['pro_seq'] = self.env['ir.sequence'].next_by_code('proforma.invoice')
    #         return super(SaleOrder, self).create(vals)
    #     print("pro_seq--------",self.pro_seq)

    # def _generate_new_proforma_sequence(self):
    #     sequence = self.env['ir.sequence'].next_by_code('proforma.invoice')
    #     return sequence
    #
    # def write(self, vals):
    #     if 'kg_invoice_status_1' in vals and vals['kg_invoice_status_1'] == 'proforma_invoice':
    #         vals['pro_seq'] = self._generate_new_proforma_sequence()
    #     return super(SaleOrder, self).write(vals)

    def proforma_invoice(self):
        print("tested-----------prodffforma")
        return self.env.ref('kg_sale.proforma_invoice_report_actions').report_action(self)

    ## sale order u can invoice only product with service types only

    def action_print(self):
        return self.env.ref('kg_sale.report_so_template_alan_bt').report_action(self)

    # def kg_create_invoice(self):
    #     print("======================+++++++++++++")
    #     sale = self
    #     lines = sale.order_line
    #     for line in lines:
    #         if line.product_id.type != 'service':
    #             raise UserError(
    #                 _('you can only invoice from sale order if the items were belonging to a service type,if not you can invoice from DO'))
    #
    #         if line.product_id.type == 'service':
    #             if line.kg_is_it_tranpcharge:
    #                 raise UserError(_('other cost items cannot invoice from sale order'))
    #     ctx = dict()
    #     ctx.update({
    #         'default_advance_payment_method': 'delivered'
    #     })
    #     return {
    #         'name': 'Invoice Order',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'sale.advance.payment.inv',
    #         #            'res_id': self.id,
    #         'target': 'new',
    #         'type': 'ir.actions.act_window',
    #         'context': ctx,
    #     }
    #
    @api.depends('order_line.margin', 'kg_discount', 'kg_discount_per', 'order_line.kg_is_it_tranpcharge',
                 'order_line.purchase_price', 'order_line.price_unit')
    def _product_margin(self):
        for order in self:
            other_cost = 0
            order_line = order.order_line
            for line in order_line:
                if line.kg_is_it_tranpcharge:
                    other_cost = other_cost + line.purchase_price
            margin = sum(order.order_line.filtered(
                lambda r: r.state != 'cancel' and not r.kg_is_it_tranpcharge and not r.kg_optional).mapped('margin'))
            discount = order.kg_discount or -1 * (order.amount_total - (order.amount_untaxed + order.amount_tax))

            order.margin = margin - discount - other_cost

    @api.onchange('partner_id')
    def onchange_partner_id_domain(self):
        # vals = super(SaleOrder, self).onchange_partner_id()

        partners_invoice = []
        partners_shipping = []
        domain = {}
        for record in self:

            if record.partner_id:
                record.kg_kindattention_partner_id = record.partner_id and record.partner_id.id
                if record.partner_id.child_ids:

                    for partner in record.partner_id.child_ids:
                        #                        if partner.type == 'invoice':
                        partners_invoice.append(partner.id)

                #                        if partner.type == 'delivery':
                #                            partners_shipping.append(partner.id)
                if partners_invoice:
                    domain['partner_invoice_id'] = [('id', 'in', partners_invoice)]
                    domain['partner_shipping_id'] = [('id', 'in', partners_invoice)]
                    domain['kg_kindattention_partner_id'] = [('id', 'in', partners_invoice)]

                else:
                    domain['partner_invoice_id'] = []
                    domain['partner_shipping_id'] = []
                    domain['kg_kindattention_partner_id'] = []
            #                if partners_shipping:
            #                    domain['partner_shipping_id'] = [('id', 'in', partners_shipping)]
            #                else:
            #                    domain['partner_shipping_id'] =  []
            else:
                domain['partner_invoice_id'] = [('type', '=', 'invoice')]
                domain['partner_shipping_id'] = [('type', '=', 'delivery')]
                domain['kg_kindattention_partner_id'] = [('type', 'in', ('delivery', 'invoice'))]
        return {'domain': domain}

    # @api.multi
    def action_check_payment_due(self):
        # print("==============================================")
        partner = self.partner_id
        uid = self.env.user and self.env.user.id

        invoice_ids = partner.invoice_ids

        for inv in invoice_ids:
            if inv.move_type == 'out_invoice' and inv.state == 'open' and inv.invoice_date_due:
                new_due_date = datetime.strptime(inv.invoice_date_due, "%Y-%m-%d") + relativedelta(days=31)
                # print(new_due_date,"new due date")
                new_due_date = str(new_due_date)[:10]
                current_date = datetime.now().strftime("%Y-%m-%d")
                if new_due_date < current_date and uid != 40:
                    raise UserError(_('Customer Grace Period Exceeded,Only MD Can Confirm the order'))

    def action_confirm(self):
        # for order in self:
        #     if not order.project_project_id:
        #         order._create_analytic_and_tasks()
        result = super(SaleOrder, self).action_confirm()
        self.picking_ids.write({'client_order_do_ref': self.client_order_ref})
        partner_obj = self.partner_id
        order_line = self.order_line
        flag = 0

        for line in order_line:
            if line.product_id.type == 'product':
                flag = 1
            if line.kg_optional:
                raise UserError(_('remove the optional items,sale order only accept confirmed items'))

            if line.kg_is_it_tranpcharge:
                flag = 1
                if line.product_id.type != 'service':
                    raise UserError(
                        _('other cost items must be type service,set product type service inside product master'))
        if flag == 0:
            self.kg_allow_invoice = 'yes'
        tradelicense = partner_obj.kg_trade_license
        # property_payment_term_id = partner_obj.property_payment_term_id and partner_obj.property_payment_term_id.id
        # credit_limit = partner_obj.credit_limit
        # if not property_payment_term_id or not credit_limit:
        #     raise UserError(_('credit limit or payment term  not found for the partner'))

        # kg_remarks = self.kg_remarks
        # if kg_remarks:
        if self.kg_need_approval == 'need_approval':
            print("-------------------needdddddddddddddddd")
            raise UserError(_('need approval from finance manager'))
        self.action_check_payment_due()
        customer_id = self.partner_id.id
        users = self.env['res.users'].browse(customer_id)

        # if users and self.project_project_id:
        #     self.project_project_id.message_subscribe(users.ids)
        return result

    #
    @api.depends('kg_revisions_line')
    def _compute_revisions(self):

        for sale in self:
            nos = 0
            revisions = sale.kg_revisions_line
            nos = len(revisions)

            sale.kg_no_of_revisions = nos

    #
    # @api.depends('amount_total', 'currency_id')
    # def _compute_amount_localcurrency(self):
    #
    #     for sale in self:
    #         rate = sale.currency_id and sale.currency_id.rate or 1
    #         amount_total = sale.amount_total
    #         if rate >= 1:
    #             amount_total = amount_total * rate
    #         else:
    #             amount_total = float(amount_total) / float(rate)
    #
    #         sale.kg_amount_localcurrency = amount_total
    #
    @api.depends('order_line')
    def _compute_kg_net_discount(self):
        for sale in self:
            lines = sale.order_line
            total_discount = 0
            for line in lines:

                if line.discount > 0 and not line.kg_optional:
                    qty = line.product_uom_qty
                    price_unit = line.price_unit
                    discount = float(float(line.discount) / float(100)) * (float(qty * price_unit))
                    total_discount = total_discount + discount
            self.kg_net_discount = total_discount

    # commented in alan addons
    # # @api.depends('order_line')
    # # def _compute_service_type(self):
    # #     for sale in self:
    # #         lines = sale.order_line
    # #         for line in lines:
    # #             prd = self.env['product.product'].search(
    # #                 [('id', '=', line.product_id.id), ('type', '=', 'service'), ], limit=1)
    # #             print prd.name
    # #             for data in prd:
    # #                 sale.kg_servicecall_categories = data.kg_servicecall_categories
    # #
    # kg_servicecall_categories = fields.Selection([
    #     ('new_installation', 'New Installation'),
    #     ('amc', 'Annual Maintenance Contract(AMC)'),
    #     ('rma', 'RMA - Faulty Product Service'),
    #     ('poc', 'Proof Of Concept(POC)')],
    #     string='Service Type', compute='_compute_service_type')
    # kg_optional = fields.Boolean(string="Optional")
    kg_terms_condition_line = fields.One2many('kg.sale.terms.line', 'order_id', string="Terms Line")
    kg_discount_per = fields.Float(string='Discount(%)')
    kg_discount = fields.Float(string='Discount')
    kg_purchase_order_lines = fields.One2many('purchase.order', 'kg_sale_order_id', string="Purchase Line")
    kg_sale_order_type = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),

    ], string='Type', default='normal')
    kg_revisions_line = fields.One2many('kg.revisions', 'kg_sale_order_id', string="Revisions Line")
    kg_no_of_revisions = fields.Float(compute='_compute_revisions', string='Revisions')
    # kg_amount_localcurrency = fields.Float(compute='_compute_amount_localcurrency', string='Amount(Local Currency)',
    #                                        store="True")
    kg_subject = fields.Char(string="Subject")
    kg_journal_id = fields.Many2one('account.journal', string="Payment")
    kg_lpos = fields.Char(string="Lpo")
    kg_warranty_id = fields.Many2one('kg.warranty', string="Warranty")
    kg_validity_id = fields.Many2one('kg.validity', string="Validity")
    kg_lpo_term_id = fields.Many2one('kg.lpo.terms', string="LPO")
    kg_delivery_id = fields.Many2one('kg.delivery', string="Delivery")
    kg_kindattention_partner_id = fields.Many2one('res.partner', string="Attention")

    kg_remove_automatic_serial = fields.Boolean(string="Remove Automatic Serial")

    kg_allow_invoice = fields.Selection([
        ('no', 'NO'),
        ('yes', 'YES'),
    ], string='Allow Invoice', default='no')

    kg_dms = fields.Selection([
        ('quotation', 'Quotation'), ('sent', 'Sent'), ('approved', 'Approved'), ('lost', 'Lost')], string='DMS',
        default='quotation')
    kg_latest_rev = fields.Char(string="Latest Revision")
    kg_net_discount = fields.Float(compute='_compute_kg_net_discount', string="Discount", store="True")
    kg_invoice_status_1 = fields.Selection([
        ('draft', 'Draft'),
        ('lpo_created_p', 'LPO Created (P)'),
        ('lpo_created', 'LPO Created'),
        ('proforma_invoice', 'Proforma Invoice Created'),
        ('invoice_p', 'Invoiced (P)'),
        ('invoiced', 'Invoiced'),
        ('completed', 'Completed'),
    ], string='Invoice Status', default='draft', readonly=True, copy=False)

    inv_count = fields.Integer(string="Invoice", compute='_compute_invoice_count')

    partner_customer_type = fields.Selection([
        ('end_user', 'End User'),
        ('it_reseller', 'IT - Reseller'),
        ('export_customer', 'Export Customer')
    ], string='Customer Type')

    def _compute_invoice_count(self):
        for inv in self:
            move_ids = self.env['account.move'].search([('kg_so_id', '=', inv.id)])
            if move_ids:
                self.inv_count = len(move_ids)
            else:
                self.inv_count = 0

    @api.constrains('kg_lpo_term_id', 'kg_warranty_id')
    def _lpo_term(self):
        if not self.kg_lpo_term_id:
            raise UserError(_('LPO  Required'))

    @api.constrains('kg_warranty_id')
    def _warranty(self):
        if not self.kg_warranty_id:
            raise UserError(_('Warranty Required'))

    # @api.model
    # def default_get(self, fields_list):
    #     res = super(SaleOrder, self).default_get(fields_list)
    #     date = datetime.strptime("%Y-%m-%d")
    #     d1 = datetime.strptime(str(date)[:10], '%Y-%m-%d')
    #     d1 = d1 + relativedelta(days=7)
    #     res.update({'validity_date': str(date)[:10]})
    #     return res

    def action_invoice(self):
        # print("------------")
        invoices = self.mapped('invoice_ids')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        # if len(invoices) > 1:
        #     action['domain'] = [('id', 'in', invoices.ids)]
        # elif len(invoices) == 1:
        #     form_view = [(self.env.ref('account.view_move_form').id, 'form')]
        #     if 'views' in action:
        #         action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
        #     else:
        #         action['views'] = form_view
        #     action['res_id'] = invoices.id
        # else:
        #     action = {'type': 'ir.actions.act_window_close'}

        action['context'] = {
            'default_kg_so_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_id': self.invoice_ids.ids,
        }
        action['domain'] = [('partner_id', '=', self.partner_id.id), ('kg_so_id', '=', self.id)]
        return action

    def kg_open_revisions(self):
        previous_revisions = self.env['kg.revisions'].search([('kg_sale_order_id', '=', self.id)])
        if len(previous_revisions) == 0:
            raise UserError(_('No revision found for this so'))

        action = self.env.ref('kg_sale.action_kg_revisions').read()[0]
        kg_sale_order_id = self.id
        domain = []
        domain.append(('kg_sale_order_id', '=', kg_sale_order_id))
        action['domain'] = domain

        action['context'] = {

            'default_kg_sale_order_id': self.id
        }

        return action

    def kg_quick_po(self):
        sale_ids = []
        for rec in self:
            sale_ids.append((rec.id))
        return {
            'name': 'Quick PO',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'kg.so.po.wizard',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {
                'default_kg_sale_order_id': sale_ids
            }
        }

    #
    def action_done(self):
        res = super(SaleOrder, self).action_done()
        self.kg_invoice_status_1 = 'completed'
        return res

    @api.depends('order_line.price_total', 'kg_discount_per', 'kg_discount', 'order_line.kg_optional',
                 'order_line.kg_is_it_tranpcharge')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        kg_discount = self.kg_discount
        kg_discount_per = self.kg_discount_per
        if kg_discount and kg_discount_per:
            # print(kg_discount,"disssssssssssssssssssssss")
            # print(kg_discount_per,"disssssssssssssssssssssss perrrrrrrrr")
            raise UserError(_('At a time choose one option discount(%) or discount'))

        if self.kg_discount_per > 100:
            raise UserError(_('maximum value 100'))

        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                # print(line.kg_optional,"opttttttttttttttttttttttttttttttttttttttttttt")
                if not line.kg_optional and not line.kg_is_it_tranpcharge:
                    amount_untaxed += line.price_subtotal
                    # FORWARDPORT UP TO 10.0
                    if order.company_id.tax_calculation_rounding_method == 'round_globally':
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                        product=line.product_id, partner=line.order_id.partner_id)
                        amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                    else:
                        amount_tax += line.price_tax

            final = amount_untaxed + amount_tax - kg_discount
            if kg_discount_per:
                final = final - float(float(float(kg_discount_per) / float(100)) * final)
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': final,
            })

    #
    def create_revisions(self):
        obj = self.env['sale.order'].browse(self._context.get('active_id'))
        lines = obj.order_line
        kg_terms_condition_line = obj.kg_terms_condition_line
        previous_revisions = self.env['kg.revisions'].search([('kg_sale_order_id', '=', obj.id)])
        no_of_rev = len(previous_revisions) + 1

        revision_lines = []
        for line in lines:
            tax_ids = []
            for tax in line.tax_id:
                tax_ids.append(tax.id)
            line_vals = (0, 0, {'product_id': line.product_id and line.product_id.id,
                                'name': line.name,
                                'price_unit': line.price_unit,
                                # 'kg_serial_no': line.kg_serial_no,
                                'price_subtotal': line.price_subtotal,
                                'product_uom_qty': line.product_uom_qty,
                                'product_uom': line.product_uom and line.product_uom.id,
                                'tax_id': [(6, 0, tax_ids)]})
            revision_lines.append(line_vals)
        terms_lines = []
        for line in kg_terms_condition_line:
            line_vals = (0, 0, {'terms_id': line.terms_id and line.terms_id.id})
            terms_lines.append(line_vals)
        vals = {'name': obj.name + "-" + str(no_of_rev),

                'origin': obj.origin,
                'client_order_ref': obj.client_order_ref,
                'date_order': obj.date_order,
                'user_id': obj.user_id and obj.user_id.id,
                'partner_id': obj.partner_id and obj.partner_id.id,
                'kg_discount_per': obj.kg_discount_per,
                'kg_discount': obj.kg_discount,
                'kg_sale_order_id': obj.id,
                # 'kg_remarks': obj.kg_remarks,
                'validity_date': obj.validity_date,
                'note': obj.note,
                'currency_id': obj.currency_id and obj.currency_id.id,
                'pricelist_id': obj.pricelist_id and obj.pricelist_id.id,
                'amount_untaxed': obj.amount_untaxed,
                'amount_tax': obj.amount_tax,
                'amount_total': obj.amount_total,
                'payment_term_id': obj.payment_term_id and obj.payment_term_id.id,
                'fiscal_position_id': obj.fiscal_position_id and obj.fiscal_position_id.id,
                'team_id': obj.team_id and obj.team_id.id,
                'revision_line': revision_lines,
                'kg_terms_condition_line': terms_lines
                }
        rev = self.env['kg.revisions'].create(vals)
        obj.kg_latest_rev = rev.name

    #
    # ****this function not needed for invoice creatio from delivry  done by another method
    # def action_invoice_create(self, grouped=False, final=False):
    #     res = super(SaleOrder, self)._create_invoices()
    #     print(res,"resultttttttttttt")
    #     invoice_obj = self.env['account.move'].browse(res)
    #     # invoice_obj = self.env['stock.picking'].browse(res)
    #     # invoice_obj = res
    #
    #     print(invoice_obj,'invoiceeeeeeeeeeee')
    #     for inv in invoice_obj:
    #         print("invvvvvvvvvvvvvvv")
    #         if inv.move_type == 'out_invoice':
    #             print("outttttttttttttttttt")
    #             inv.kg_discount_per = self.kg_discount_per
    #             inv.kg_discount = self.kg_discount
    #             inv.kg_warranty_id = self.kg_warranty_id and self.kg_warranty_id.id or False
    #             inv.kg_validity_id = self.kg_validity_id and self.kg_validity_id.id or False
    #             inv.kg_lpo_term_id = self.kg_lpo_term_id and self.kg_lpo_term_id.id or False
    #             inv.kg_delivery_id = self.kg_delivery_id and self.kg_delivery_id.id or False
    #             inv.kg_so_id = self and self.id or False
    #     return res
    # commented section in alan addon
    # # @api.multi
    # # def _create_analytic_account(self, prefix=None):
    # #     for order in self:
    # #         print 'analatyc account 001',order.kg_servicecall_categories
    # #         name = order.name
    # #         if prefix:
    # #             name = prefix + ": " + order.name
    # #         analytic = self.env['account.analytic.account'].create({
    # #             'name': name,
    # #             'code': order.client_order_ref,
    # #             'company_id': order.company_id.id,
    # #             'partner_id': order.partner_id.id,
    # #             'kg_servicecall_categories': order.kg_servicecall_categories
    # #         })
    # #         order.project_id = analytic

    @api.constrains('partner_id')
    def credit_payment_terms_validation(self):
        partner = self.partner_id
        if partner and not partner.use_partner_credit_limit:
            if not partner.property_payment_term_id:
                raise UserError(_('credit limit or payment term not found for the partner'))

    is_approve = fields.Boolean("Is approve", related='partner_id.use_partner_credit_limit')

    def kg_action_approve(self):
        self.kg_need_approval = 'approved'
        partner_obj = self.partner_id
        tradelicense = partner_obj.kg_trade_license
        property_payment_term_id = partner_obj.property_payment_term_id and partner_obj.property_payment_term_id.id
        credit_limit = partner_obj.credit_limit
        # if not property_payment_term_id or not credit_limit:
        #     raise UserError(_('credit limit or payment term not found for the partner'))
        return True

    # @api.depends('amount_total', 'partner_id')
    # def _compute_kg_credit_exposure(self):
    #     for obj in self:
    #         amount_total = obj.amount_total
    #         partner_id = obj.partner_id and obj.partner_id.id
    #         if partner_id:
    #             credit_limit = obj.partner_id.credit_limit
    #             if amount_total > credit_limit:
    #                 obj.kg_remarks = 'Credit Limit Exceeded'
    #             else:
    #                 obj.kg_remarks = ''
    #
    # kg_remarks = fields.Char(
    #     'Remark', compute='_compute_kg_credit_exposure')

    kg_need_approval = fields.Selection([
        ('need_approval', 'Need Approval From Accounts Department'),
        ('no_need_approval', 'No Approval Needed'),
        ('approved', 'Accounts Department Approved'),
    ], string='Status', compute='_compute_kg_approval_status')

    @api.depends('partner_id', 'amount_total')
    def _compute_kg_approval_status(self):

        for obj in self:
            obj.kg_need_approval='no_need_approval'
            amount_total = obj.amount_total
            partner_id = obj.partner_id and obj.partner_id.id
            if partner_id:
                credit_limit = obj.partner_id.credit_limit
                print("amount_total", amount_total)
                print("credit_limit", credit_limit)
                if amount_total > credit_limit:

                    obj.kg_need_approval = 'need_approval'
                else:
                    obj.kg_need_approval = 'no_need_approval'


class KgSaleTermsLine(models.Model):
    _name = "kg.sale.terms.line"
    order_id = fields.Many2one('sale.order', string="Order")
    terms_id = fields.Many2one('kg.terms.condition', string="Terms and Condition")


class StockMoveLine(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        for rec in self:
            if rec.picking_type_code == 'outgoing':
                for i in rec.move_line_ids_without_package:
                    print("testttt222222222")
                    if i.lot_id and i.lot_id.product_qty < i.qty_done:
                        raise UserError(_(
                            "The selected lot has only %s. Cannot create a picking for this lot.") % (
                                            i.lot_id.product_qty))

        res = super(StockMoveLine, self).button_validate()
        return res
