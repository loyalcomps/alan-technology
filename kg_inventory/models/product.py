# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.product'

    @api.constrains('type', 'default_code')
    def _check_dob(self):
        default_code = self.default_code

        if default_code:
            product_ids = self.env['product.product'].search([('default_code', '=', default_code)])
            if len(product_ids) > 1:
                raise UserError(_('Part number duplication not allowed'))
        if self.type == 'consu':
            raise UserError(
                _('Product type must be stockable or service, if it is service then only select service, consumable type not allowed'))

        if self.type == 'service':
            if not self.invoice_policy == 'order':
                raise UserError(
                    _('Products with service type have no delivery order,so make it invoicing policy based on Ordered quantities'))
