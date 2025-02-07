# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, api, fields, _

# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import datetime

import logging

_logger = logging.getLogger(__name__)

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


    @api.onchange('kg_serial_no')
    def _onchange_kg_serial_no(self):
        """Sets the serial number (sl_no) to the value of kg_serial_no
        when kg_serial_no is changed.
        """
        if self.kg_serial_no:
            self.sl_no=self.kg_serial_no


    @api.depends('product_id', 'purchase_price', 'product_uom_qty', 'price_unit', 'kg_is_it_tranpcharge', 'kg_optional',
                 'price_unit')
    def _product_margin(self):
        """Computes and updates the margin for the sale order line.

        The margin is calculated as the difference between the subtotal price
        and the product's cost price multiplied by the quantity. The currency
        rounding is applied using the order's pricelist currency.

        The margin is only computed if the product is not marked as a transport
        charge (kg_is_it_tranpcharge) and is not optional (kg_optional).
        """
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
        """Opens the cost history action for the selected product.

        Retrieves and returns the action associated with the cost history of
        the selected product. If no product is selected, a UserError is raised.

        Returns:
           dict: An action dictionary containing the domain and context for
           opening the cost history view.
        """
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
        """Adds an entry to the product cost history.

        This method creates a new record in the 'kg.product.cost.history' model with
        the product ID, supplier ID, and purchase cost of the current record.

        Returns:
            bool: True after successfully creating the history record.
        """
        history = self.env['kg.product.cost.history']
        product_id = self.product_id and self.product_id.id
        supplier_id = self.kg_supplier_id and self.kg_supplier_id.id
        cost = self.purchase_price

        history.create({'product_id': product_id, 'supplier_id': supplier_id, 'cost': cost})
        return True


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # def _get_branch_domain(self):
    #     """method to get bank domain"""
    #     company = self.env.company
    #     partner = company.partner_id
    #     bank = []
    #     for rec in partner.bank_ids:
    #         bank.append(rec.bank_id.id)
    #     return [('id', 'in', bank)]

    def _get_bank_domain(self):
        """method to get bank domain"""
        company = self.env.company
        company.bank_ids.ids
        return [('id', 'in', company.bank_ids.ids)]

    def get_capital(self,amount):
        return amount.title()

    def get_converted(self,amount):
        return self.currency_id.compute(amount, self.env.company.currency_id)

    pro_seq = fields.Char(string="Proforma Sequence", copy=False)
    res_bank_ids = fields.Many2one('res.partner.bank', string='Bank', domain=_get_bank_domain)
    bank_id = fields.Many2one('res.bank', string='Bank')
    show_send_button = fields.Boolean(string="Show Send Button", compute='_compute_show_send_button')

    def _compute_show_send_button(self):
        """Computes whether the send button should be displayed.

           The send button is shown if:
           - The record has a `pro_seq` value.
           - The record's state is 'draft'.
           - The user belongs to the 'Proforma Sales' group or the invoice count is zero.

           This computed value is stored in the `show_send_button` field.
           """
        for rec in self:
            show_send_button = False
            user = self.env.user

            if rec.pro_seq and rec.state == 'draft' and (user.has_group('sale.group_proforma_sales') or rec.invoice_count == 0):
                show_send_button = True
            rec.show_send_button = show_send_button

    def action_unlock(self):
        """Overrides the default unlock action to update the invoice status.

        After unlocking a sale order, this method checks related invoices and updates
        the `kg_invoice_status_1` field based on the invoicing progress:
        - If all sale order lines are invoiced, status is set to 'invoiced'.
        - If partial invoicing is done, status is set to 'invoice_p'.
        - If a proforma sequence (`pro_seq`) exists, status is set to 'proforma_invoice'.
        - Otherwise, status remains 'draft'.

        Returns:
            res: The result of the parent `action_unlock` method.
        """
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
        """Prevents deletion of quotations and confirmed sales orders.

        Raises a `UserError` if an attempt is made to delete a sent quotation
        or a confirmed sales order. Only draft or canceled orders can be deleted.

        Raises:
            UserError: If the sale order is not in draft or canceled state.
        """
        for order in self:
            if order:
                raise UserError(_(
                    "You can not delete a sent quotation or a confirmed sales order."))

    def proforma_invoice_gen_seq(self):
        """Generates a new proforma invoice sequence and updates the order status.

        This method sets the `kg_invoice_status_1` field to 'proforma_invoice'
        for each sale order and generates a new sequence for the proforma invoice
        using the 'proforma.inv' sequence code. The generated sequence is then
        assigned to the `pro_seq` field of the order.

        It also prints the generated sequence for debugging purposes.
        """
        _logger.info("tested------sale")
        for order in self:
            order.kg_invoice_status_1 = 'proforma_invoice'
            sequence = self.env['ir.sequence'].sudo().next_by_code('proforma.inv') or _('New')
            order.write({'pro_seq': sequence})
            _logger.info("sequence--> %s",
                         self.env['ir.sequence'].sudo().next_by_code('proforma.invoice'))  # Log the generated sequence

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """Updates the customer type based on the selected partner.

        When the `partner_id` field is changed, this method updates the `partner_customer_type`
        field based on the customer type of the selected partner. If no partner is selected,
        the `partner_customer_type` is set to False.
        """
        if self.partner_id:
            self.partner_customer_type = self.partner_id.customer_type
        else:
            self.partner_customer_type = False

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total','order_line.kg_optional','order_line.kg_is_it_tranpcharge')
    def _compute_amounts(self):
        """Computes the total amounts for the Sale Order.

       This method computes the untaxed amount, total amount, and tax amount for the sale order
       by filtering out optional lines and transport charge lines from the order lines. The
       results are stored in the respective fields: `amount_untaxed`, `amount_total`, and `amount_tax`.
       """
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
        """Generates and returns the proforma invoice report action.

       This method triggers the report action for the proforma invoice by referencing
       the 'proforma_invoice_report_actions' defined in the 'kg_sale' module.

       Returns:
           dict: A dictionary with the report action for generating the proforma invoice.
       """
        _logger.info("tested-----------prodffforma")
        return self.env.ref('kg_sale.proforma_invoice_report_actions').report_action(self)

    ## sale order u can invoice only product with service types only

    def action_print(self):
        """Generates and returns the Sale Order report action.

           This method triggers the report action for printing the Sale Order based on
           the template 'report_so_template_alan_bt' defined in the 'kg_sale' module.

           Returns:
               dict: A dictionary with the report action for printing the Sale Order.
           """
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
        """Calculates and updates the margin for the Sale Order.

        This method calculates the margin for the sale order by considering:
        - The sum of margins for non-cancelled order lines excluding transport charge and optional items.
        - The discount applied to the order based on the difference between total and untaxed amounts.
        - The additional cost for transport charges based on the purchase price of lines marked as transport charges.

        The final margin is stored in the `margin` field of the Sale Order.

        The calculated margin is: `margin - discount - other_cost`.
        """
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
        """Updates the domain for partner fields based on the selected partner.

        When the `partner_id` field is changed, this method updates the domains for the following fields:
        - `partner_invoice_id`: The domain is updated to filter based on the child partners of the selected `partner_id`.
        - `partner_shipping_id`: The domain is updated similarly to `partner_invoice_id`.
        - `kg_kindattention_partner_id`: The domain is updated to include child partners of the selected `partner_id`.

        If no child partners are found for the selected partner, the domains are reset to allow only invoice and delivery partners.

        Returns:
            dict: A dictionary containing the updated domains for the `partner_invoice_id`,
                  `partner_shipping_id`, and `kg_kindattention_partner_id` fields.
        """

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
        """Checks if the payment due date has exceeded for the partner's open invoices.

        This method iterates through the invoices associated with the partner and checks if:
        - The invoice is of type 'out_invoice' (customer invoice).
        - The invoice is in an open state.
        - The invoice has a due date.

        If the due date has passed and the current user is not the MD (user with ID 40),
        a `UserError` is raised indicating that the customer grace period has been exceeded
        and only the MD can confirm the order.

        Raises:
            UserError: If the customer grace period for the invoice is exceeded and the user is not the MD.
        """
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
        """Confirms the sale order and performs additional validation and updates.

        This method overrides the default action for confirming a sale order. It performs the following:
        - Calls the parent `action_confirm` method to confirm the order.
        - Updates the `client_order_do_ref` field on related pickings.
        - Checks each order line for the following conditions:
          - If the line contains a product, a flag is set to 1.
          - If the line is marked as optional, a `UserError` is raised, as only confirmed items are allowed.
          - If the line is marked as a transport charge, it checks if the product type is 'service'; otherwise, a `UserError` is raised.
        - Sets `kg_allow_invoice` to 'yes' if no product lines were found.
        - Checks if the sale order requires approval from the finance manager. If so, a `UserError` is raised.
        - Calls `action_check_payment_due` to verify if the payment due date has been exceeded.

        Returns:
            result: The result of the parent `action_confirm` method.

        Raises:
            UserError: If there are optional items, incorrect product types for transport charges, or if approval is required from the finance manager.
        """

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
        """Computes the number of revisions for the sale order.

        This method calculates the number of revisions for the sale order based on the
        `kg_revisions_line` field, which stores the revisions related to the sale order.
        The result is stored in the `kg_no_of_revisions` field.

        This method is triggered when the `kg_revisions_line` field is modified.
        """
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
        """Computes the net discount for the sale order.

        This method calculates the total discount applied to the sale order, based on the
        discount percentages applied to individual order lines. It filters out optional lines
        and computes the discount for each valid line. The result is stored in the `kg_net_discount` field.

        This method is triggered when the `order_line` field is modified.
        """
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
    ], string='Quotation Status', default='draft', readonly=True, copy=False)

    inv_count = fields.Integer(string="Invoice", compute='_compute_invoice_count')

    partner_customer_type = fields.Selection([
        ('end_user', 'End User'),
        ('it_reseller', 'IT - Reseller'),
        ('export_customer', 'Export Customer')
    ], string='Customer Type')

    def _compute_invoice_count(self):
        """Computes and updates the count of invoices associated with the sale order.

        This method calculates the number of invoices related to the current sale order by searching
        for account moves (invoices) with the corresponding sale order ID (`kg_so_id`). The result
        is stored in the `inv_count` field. If no invoices are found, the count is set to 0.

        This method is triggered when the `invoice_ids` field is modified or when needed.
        """
        for inv in self:
            move_ids = self.env['account.move'].search([('kg_so_id', '=', inv.id)])
            if move_ids:
                self.inv_count = len(move_ids)
            else:
                self.inv_count = 0

    @api.constrains('kg_lpo_term_id', 'kg_warranty_id')
    def _lpo_term(self):
        """Ensures that the LPO term is provided for the sale order.

        This method is triggered when the `kg_lpo_term_id` or `kg_warranty_id` fields are modified.
        If the `kg_lpo_term_id` field is not set, it raises a `UserError` indicating that the LPO
        term is required.

        Raises:
            UserError: If the `kg_lpo_term_id` field is empty.
        """
        if not self.kg_lpo_term_id:
            raise UserError(_('LPO  Required'))

    @api.constrains('kg_warranty_id')
    def _warranty(self):
        """Ensures that the warranty is provided for the sale order.

        This method is triggered when the `kg_warranty_id` field is modified.
        If the `kg_warranty_id` field is not set, it raises a `UserError` indicating that
        the warranty is required.

        Raises:
            UserError: If the `kg_warranty_id` field is empty.
        """
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
        """Generates an action for creating invoices related to the sale order.

        This method creates an action to open the invoice creation view for the current sale order.
        It maps the `invoice_ids` field of the sale order to the `context` and sets the `domain`
        to filter invoices by the sale order and partner.

        Returns:
           dict: A dictionary containing the action details to open the invoice creation view.
        """
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
        """Opens the revisions associated with the sale order.

        This method searches for previous revisions related to the current sale order.
        If no revisions are found, a `UserError` is raised. If revisions are found,
        it opens an action to display the revisions, filtering by the current sale order ID.

        Returns:
            dict: An action dictionary that opens the revisions view for the sale order.

        Raises:
            UserError: If no revisions are found for the sale order.
        """
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
        """Opens a quick purchase order wizard for the sale order.

        This method prepares the context for a quick purchase order (PO) wizard by
        passing the current sale order ID as context. It opens a form view of the
        `kg.so.po.wizard` model in a new window for the user to create a PO related
        to the sale order.

        Returns:
            dict: A dictionary containing the action to open the quick PO wizard.
        """
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
        """Marks the sale order as completed.

        This method overrides the default `action_done` method for the sale order,
        and sets the `kg_invoice_status_1` field to 'completed' to indicate that
        the sale order has been completed.

        Returns:
            res: The result of the parent `action_done` method.
        """
        res = super(SaleOrder, self).action_done()
        self.kg_invoice_status_1 = 'completed'
        return res

    @api.depends('order_line.price_total', 'kg_discount_per', 'kg_discount', 'order_line.kg_optional',
                 'order_line.kg_is_it_tranpcharge')
    def _amount_all(self):
        """Computes the total amounts for the sale order.

        This method calculates the untaxed amount, tax amount, and total amount
        for the sale order, considering applied discounts, optional lines, and
        transport charges. If both percentage and fixed discounts are provided,
        a `UserError` is raised. The method also validates that the discount percentage
        does not exceed 100%.

        It updates the following fields:
        - `amount_untaxed`: The untaxed amount of the sale order.
        - `amount_tax`: The total tax amount of the sale order.
        - `amount_total`: The final total amount after applying any discounts.

        Raises:
            UserError: If both percentage and fixed discount options are selected or if the discount percentage exceeds 100%.
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
        """Creates a revision record for a sale order.

        This method generates a revision for the current sale order by copying the
        order's details, including product lines and terms & conditions. It also
        increments the revision number based on the number of previous revisions.
        The new revision is created in the `kg.revisions` model, and the sale order's
        `kg_latest_rev` field is updated with the new revision's name.

        The following fields are included in the revision:
        - `name`: The revision name, which includes the sale order name and the revision number.
        - `origin`, `client_order_ref`, `date_order`, `user_id`, `partner_id`, etc.: Various fields from the original sale order.
        - `revision_line`: A list of product lines from the sale order, including product details, prices, quantities, and taxes.
        - `kg_terms_condition_line`: A list of terms & conditions associated with the sale order.

        After creating the revision, the latest revision name is stored in the sale order's `kg_latest_rev` field.

        The method is triggered when the user needs to create a new revision for a sale order.

        Returns:
            None
        """
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
        """Validates the credit limit and payment terms for the partner.

        This method is triggered when the `partner_id` field is modified. It checks
        whether the partner has the `use_partner_credit_limit` flag set. If the flag
        is not set, it ensures that the partner has a valid payment term (`property_payment_term_id`).
        If no payment term is found, a `UserError` is raised indicating that either a credit
        limit or payment term must be set for the partner.

        Raises:
           UserError: If the partner does not have a payment term set and does not use the credit limit.
        """
        partner = self.partner_id
        if partner and not partner.use_partner_credit_limit:
            if not partner.property_payment_term_id:
                raise UserError(_('credit limit or payment term not found for the partner'))

    is_approve = fields.Boolean("Is approve", related='partner_id.use_partner_credit_limit')

    def kg_action_approve(self):
        """Sets the approval status and processes the partner's details.

        This method sets the `kg_need_approval` field to 'approved', indicating
        that the approval process is complete. It also retrieves the partner's
        trade license, payment term, and credit limit for further processing,
        although the details are not explicitly used in this method.

        Returns:
            bool: Always returns True, indicating successful approval.
        """
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
    ], string='Status', compute='_compute_kg_approval_status', store=True)

    @api.depends('partner_id', 'amount_total')
    def _compute_kg_approval_status(self):
        """Computes the approval status based on the partner's credit limit and the total amount.

        This method is triggered when the `partner_id` or `amount_total` fields are modified.
        It compares the total amount of the order (`amount_total`) with the partner's credit
        limit (`credit_limit`). If the total amount exceeds the credit limit, the approval status
        (`kg_need_approval`) is set to 'need_approval'. Otherwise, it is set to 'no_need_approval'.

        The computed value of `kg_need_approval` helps determine if approval is required for the order.

        This method also prints the `amount_total` and `credit_limit` for debugging purposes.

        Fields Updated:
           - `kg_need_approval`: Set to 'need_approval' or 'no_need_approval' based on the comparison.

        """
        for obj in self:
            obj.kg_need_approval='no_need_approval'
            amount_total = obj.amount_total
            partner_id = obj.partner_id and obj.partner_id.id
            if partner_id:
                credit_limit = obj.partner_id.credit_limit
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
        """Validates the stock picking for outgoing moves.

        This method is triggered when validating a stock picking. It checks if the picking type is 'outgoing'
        and verifies the available quantity for each move line. If a move line is associated with a lot and
        the available quantity of the lot is less than the quantity to be done (`qty_done`), it raises a
        `UserError` indicating that there isn't enough quantity available in the selected lot to fulfill the move.

        The method performs the following actions:
        - Loops through the `move_line_ids_without_package` to check for outgoing stock moves.
        - Verifies if the lot's quantity is less than the quantity to be done.
        - Raises a `UserError` if the lot has insufficient quantity.

        Returns:
            res: The result of the parent `button_validate` method, indicating successful validation.

        Raises:
            UserError: If the lot's quantity is insufficient for the quantity to be done.
        """
        for rec in self:
            if rec.picking_type_code == 'outgoing':
                for i in rec.move_line_ids_without_package:
                    _logger.info("Validating move line for lot %s, qty_done: %s", i.lot_id, i.qty_done)
                    if i.lot_id and i.lot_id.product_qty < i.qty_done:
                        raise UserError(_(
                            "The selected lot has only %s. Cannot create a picking for this lot.") % (
                                            i.lot_id.product_qty))

        res = super(StockMoveLine, self).button_validate()
        return res
