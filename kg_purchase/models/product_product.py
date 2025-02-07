# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = "product.product"

    expensed_ok = fields.Boolean('Can be Expensed')
    od_payroll_item = fields.Boolean('Payroll Item')
    warranty = fields.Float('Warranty')
    attribute_value_ids = fields.Many2many(
        'product.attribute.value', string='Attributes', ondelete='restrict')
    property_stock_account_input = fields.Many2one('account.account', 'Stock Input Account')
    property_stock_account_output = fields.Many2one('account.account', 'Stock Output Account')
