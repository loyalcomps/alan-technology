# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    kg_supplier_type_id = fields.Many2one('kg.supplier.type', 'Supplier Type')
    customer = fields.Boolean('Is a Customer')
    vendor = fields.Boolean('Is a Vendor')
    notify_email = fields.Selection(selection=[('none', 'Never'), ('always', 'All Messages')])
