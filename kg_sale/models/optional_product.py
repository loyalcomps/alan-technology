# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import Warning


class KgOptionalProduct(models.Model):
    _name = 'kg.optional.product'
    _description = "kg.optional.product"

    product_id = fields.Many2one("product.product",string="Product")
    optional_product_id = fields.Many2one("product.product",string="Product")

