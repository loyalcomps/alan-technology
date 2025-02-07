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
        """Converts the name field to uppercase when it is changed.

        This method is triggered when the `name` field is changed. It checks if
        the `name` field has a value, and if so, converts the value to uppercase
        and updates the `name` field accordingly.

        Returns:
            None
        """
        name = self.name
        if name:
            upper = name.upper()
            self.name = upper

    @api.constrains('name')
    def _check_dob(self):
        """Checks for duplicate brand names before saving the record.

        This method is triggered when the `name` field is changed or validated.
        It checks whether the brand name already exists in the `kg.product.brand`
        model. If there is more than one record with the same name, a `UserError`
        is raised, preventing the duplication of brand names.

        Raises:
            UserError: If there is more than one brand with the same name.

        Returns:
            None
        """
        name = self.name

        if name:
            same_name = self.env['kg.product.brand'].search([('name', '=', name)])
            if len(same_name) > 1:
                raise UserError(_('brand duplication not allowed'))
