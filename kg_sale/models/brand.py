# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KgProductBrand(models.Model):
    _name = 'kg.product.brand'
    _description = "Product Brand"

    code = fields.Char(string='Code')
    name = fields.Char(string='Name')
    note = fields.Text(string='Name')
    product_id = fields.Many2one('product.product', string="Product")
    kg_categ_id = fields.Many2one('product.category', 'Category')


    @api.onchange('name')
    def onchange_name(self):
        name = self.name
        if name:
            upper = name.upper()
            self.name = upper

    @api.constrains('name')
    def _check_dob(self):
        name = self.name

        if name:
            same_name = self.env['kg.product.brand'].search([('name', '=', name)])
            if len(same_name) > 1:
                raise UserError(_('brand duplication not allowed'))
