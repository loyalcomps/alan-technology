# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

# import odoo.addons.decimal_precision as dp
import re
import datetime as dt
from datetime import timedelta, tzinfo, time, date, datetime
from dateutil.relativedelta import relativedelta


# from monthdelta import monthdelta

class KGResBankInherit(models.Model):
    _inherit = "res.partner.bank"

    bank_iban_number = fields.Char(string="IBAN Number")
    swift_code = fields.Char(string="Swift Code")
    branch = fields.Char(string="Branch")

class ResPartner(models.Model):
    _inherit = 'res.partner'


    total_quotation = fields.Integer('Total Quotation', compute='total_invoice_and_quotation')
    total_invoice = fields.Integer('Total Invoices', compute='total_invoice_and_quotation')
    total_quotation_amt = fields.Monetary('Total Quotation Amt', compute='total_invoice_and_quotation')

    # total_invoice_amt = fields.Monetary('Total Invoice Amt', compute='total_invoice_and_quotation')

    def total_invoice_and_quotation(self):
        """Computes the total number of quotations and invoices for the partner.

        This method calculates:
        - The total number of quotations (`total_quotation`) and their total amount (`total_quotation_amt`)
          for the partner and its child partners.
        - The total number of invoices (`total_invoice`) for the partner and its child partners.

        It performs the following steps:
        1. Retrieves all child partners using `child_of` domain.
        2. Reads sale orders grouped by partner and sums the total amount.
        3. Reads invoices grouped by partner.
        4. Iterates over the sale order groups and updates `total_quotation` and `total_quotation_amt`.
        5. Iterates over the invoice groups and updates `total_invoice`.

        Fields Updated:
            - `total_quotation`: The total number of quotations for the partner.
            - `total_invoice`: The total number of invoices for the partner.
            - `total_quotation_amt`: The total amount of quotations for the partner.

        Returns:
            None
        """
        self.total_quotation = False
        self.total_invoice = False
        self.total_quotation_amt = False

        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        sale_order_groups = self.env['sale.order']._read_group(
            domain=expression.AND([self._get_sale_order_domain_count(), [('partner_id', 'in', all_partners.ids)]]),
            fields=['partner_id', 'amount_total'], groupby=['partner_id']
        )

        invoice_groups = self.env['account.move'].read_group([('partner_id', 'in', all_partners.ids),
                                                              ('move_type', 'in', ('out_invoice', 'out_refund'))],
                                                             fields=['partner_id'], groupby=['partner_id']
                                                             )
        partners = self.browse()

        for group in sale_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.total_quotation += group['partner_id_count']
                    partner.total_quotation_amt += group['amount_total']

                    partners |= partner
                partner = partner.parent_id

            (self - partners).total_quotation = 0
        for group in invoice_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner.total_invoice += group['partner_id_count']
                    partners |= partner
                partner = partner.parent_id
            (self - partners).total_invoice = 0

    @api.depends('sale_order_ids')
    def _compute_sale_order_value(self):
        """Computes the total value of open sale orders for the partner.

        This method calculates the total value of sale orders associated with the partner
        that are not confirmed (`sale`), completed (`done`), or canceled (`cancel`).
        It converts the amount based on the sale order currency's exchange rate.

        The method:
        1. Iterates over all sale orders linked to the partner.
        2. Checks if the sale order state is valid (not `sale`, `done`, or `cancel`).
        3. Converts the order amount based on the exchange rate.
        4. Sums up the total value and updates the `kg_total_value` field.

        Fields Updated:
            - `kg_total_value`: The total value of open sale orders.

        Returns:
            None
        """
        for partner in self:
            sale_order_ids = partner.sale_order_ids
            total = 0
            for sale in sale_order_ids:
                if sale.state not in ['sale', 'done', 'cancel']:
                    rate = sale.currency_id and sale.currency_id.rate or 1
                    if rate >= 1:
                        total = total + (sale.amount_total * rate)
                    else:
                        total = total + (float(sale.amount_total) / float(rate))
            partner.kg_total_value = total

    @api.depends('invoice_ids')
    def _compute_invoice_numbers(self):
        """Computes the total number of invoices associated with the partner.

        This method counts the number of invoices linked to the partner and updates
        the `kg_no_of_invoices` field accordingly.

        Fields Updated:
            - `kg_no_of_invoices`: The total number of invoices associated with the partner.

        Returns:
            None
        """
        for partner in self:
            invoice_ids = partner.invoice_ids
            no = len(invoice_ids)

            partner.kg_no_of_invoices = no

    @api.depends('sale_order_ids')
    def _compute_kg_no_of_quote(self):
        """Computes the total number of quotations for the partner.

        This method counts the number of sale orders linked to the partner that
        are still in quotation stage (not confirmed, completed, or canceled)
        and updates the `kg_no_of_quote` field.

        Fields Updated:
            - `kg_no_of_quote`: The total number of quotations associated with the partner.

        Returns:
            None
        """
        for partner in self:
            quotes = []
            sale_order_ids = partner.sale_order_ids
            for sale in sale_order_ids:
                if sale.state not in ['sale', 'done', 'cancel']:
                    quotes.append(sale.id)

            no = len(quotes)

            partner.kg_no_of_quote = no

    @api.depends('invoice_ids')
    def _compute_outstanding(self):
        """Computes the outstanding balance for the partner.

        This method calculates the outstanding balance by summing up the residual
        amounts of the partner’s invoices, adjusting for refunds and invoices.

        The outstanding value is computed as:
        - Subtracting residual amounts of refund invoices (`in_refund`, `out_refund`).
        - Adding residual amounts of standard invoices (`in_invoice`, `out_invoice`).
        - Applying currency conversion using the exchange rate.

        Fields Updated:
            - `kg_outstanding_value`: The total outstanding balance for the partner.

        Returns:
            None
        """
        for partner in self:
            total = 0
            invoice_ids = partner.invoice_ids
            for inv in invoice_ids:
                if inv.move_type == 'in_refund' or inv.move_type == 'out_refund':
                    rate = inv.currency_id and inv.currency_id.rate or 1
                    if rate >= 1:
                        total = total - (inv.amount_residual * rate)
                    else:
                        total = total - (float(inv.amount_residual) / float(rate))
                if inv.move_type == 'in_invoice' or inv.move_type == 'out_invoice':
                    rate = inv.currency_id and inv.currency_id.rate or 1
                    if rate >= 1:
                        total = total + (inv.amount_residual * rate)
                    else:
                        total = total + (float(inv.amount_residual) / float(rate))

            partner.kg_outstanding_value = total


    def default_login_user(self):
        """Returns the ID of the currently logged-in user.

        This method retrieves the ID of the currently authenticated user
        and returns it.

        Returns:
            int: The ID of the currently logged-in user.
        """
        current_user = self.env.user.id
        return current_user

    salesperson_1_id = fields.Many2one('res.users', default=default_login_user, required=True, string='IT Sales')
    salesperson_2_id = fields.Many2one('res.users', string='Solutions')
    salesperson_3_id = fields.Many2one('res.users', string='ELV')

    customer_type = fields.Selection([
        ('end_user', 'End User'),
        ('it_reseller', 'IT - Reseller'),
        ('export_customer', 'Export Customer')
    ], string='Customer Type')
    kg_total_value = fields.Float(compute='_compute_sale_order_value', string='Value')
    kg_no_of_invoices = fields.Float(compute='_compute_invoice_numbers', string='No.of Invoices')
    kg_outstanding_value = fields.Float(compute='_compute_outstanding', string='Outstanding Value')
    kg_no_of_quote = fields.Float(compute='_compute_kg_no_of_quote', string='No.of Quote')
    kg_trade_license = fields.Char(string="Trade License#")
    kg_payment_extension_line_ids = fields.One2many('kg.partner.payment.extension.line', 'partner_id',
                                                    string="Payment Extension Line")
    kg_payment_extension_remarks = fields.Char(string="Remarks")
    kg_tr_no = fields.Char(string="TR NO")
    kg_size_id = fields.Many2one('kg.size', string="Company Size")
    # kg_ind_id = fields.Many2one('kg.industry.master', string="Industry")
    kg_department_id = fields.Many2one('hr.department', string='Serving Department')
    kg_account_manager_id = fields.Many2one('res.users', string='Account Manager')
    # kg_supplier_type_id = fields.Many2one('kg.supplier.type', string='Supplier Type')
    kg_rating = fields.Selection([
        ('bad', 'Bad'),
        ('medium', 'Medium'),
        ('good', 'Good'),
        ('excellent', 'Excellent'),
    ], default='medium', string='Rating')

    kg_accounting_managers_line_ids = fields.One2many('kg.partner.accounting.managers.line', 'partner_id',
                                                      string="Accounting Managers")

    def view_sale_order(self):
        """Opens the quotations view filtered for the current partner.

        This method retrieves the quotation action and filters it to display only
        quotations (`sale.order` records) linked to the current partner, excluding
        confirmed, completed, and canceled sales.

        Returns:
            dict: An action dictionary that opens the quotations view filtered for
                  the current partner.
        """
        print("------------------------")
        action = self.env.ref('sale.action_quotations').read()[0]
        partner_id = self.id
        domain = []
        domain.append(('partner_id', '=', partner_id))
        domain.append(('state', 'not in', ('sale', 'done', 'cancel')))
        action['domain'] = domain

        action['context'] = {

            'default_partner_id': partner_id
        }

        return action

    #
    def view_quotes(self):
        """Opens the quotations view filtered for the current partner.

        This method is functionally identical to `view_sale_order()`. It retrieves
        the quotation action and filters it to display only quotations (`sale.order`
        records) linked to the current partner, excluding confirmed, completed,
        and canceled sales.

        Returns:
            dict: An action dictionary that opens the quotations view filtered for
                  the current partner.
        """
        print("------------------------")
        action = self.env.ref('sale.action_quotations').read()[0]
        partner_id = self.id
        domain = []
        domain.append(('partner_id', '=', partner_id))
        domain.append(('state', 'not in', ('sale', 'done', 'cancel')))
        action['domain'] = domain

        action['context'] = {

            'default_partner_id': partner_id
        }

        return action

    #
    #
    #
    def view_invoices(self):
        """Opens the invoices view filtered for the current partner.

        This method retrieves the customer invoices action and filters it to
        display only invoices (`account.move` records) linked to the current partner.

        Returns:
            dict: An action dictionary that opens the invoices view filtered for
                  the current partner.
        """
        print("------------------------")
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        partner_id = self.id
        domain = []
        domain.append(('partner_id', '=', partner_id))
        action['domain'] = domain

        action['context'] = {

            'default_partner_id': partner_id
        }

        return action

    def view_invoices_outstanding(self):
        """Opens the outstanding invoices view filtered for the current partner.

        This method retrieves the customer invoices action and filters it to
        display only outstanding invoices (`account.move` records) linked to
        the current partner.

        Returns:
            dict: An action dictionary that opens the outstanding invoices
                  view filtered for the current partner.
        """
        print("------------------------")
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        partner_id = self.id
        domain = []
        domain.append(('partner_id', '=', partner_id))
        action['domain'] = domain

        action['context'] = {

            'default_partner_id': partner_id
        }

        return action
