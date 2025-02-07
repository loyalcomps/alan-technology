# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class KgSupplierType(models.Model):
    _name = "kg.supplier.type"
    _description = "kg.supplier.type"

    name = fields.Char(string='Name')
    desc = fields.Text(string="Description")
