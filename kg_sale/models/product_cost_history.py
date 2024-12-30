# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import Warning


class KgProductCostHistory(models.Model):
    _name = 'kg.product.cost.history'
    _description = "Product Cost History"

    product_id = fields.Many2one('product.product',string="Product")
    user_id = fields.Many2one('res.users',string="User",default=lambda self: self.env.user)
    supplier_id = fields.Many2one('res.partner',string="Vendor")
    date = fields.Date(string="Date",default=fields.Datetime.now)
    cost = fields.Float(string="Cost")
    

