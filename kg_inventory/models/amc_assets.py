# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AMCAssets(models.Model):
    _name = 'amc.assets'
    _description = 'amc.assets'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    description = fields.Char(string='Description')
    assets_line = fields.One2many('assets.line', 'amc_id', string='Assets Line')


class AMCAssetsLine(models.Model):
    _name = 'assets.line'
    _description = 'amc.assets'

    product_id = fields.Many2one('product.product', string='Product',required=True)
    serial_no = fields.Char(string='Serial No')
    qty = fields.Float(string='Quantity')
    username = fields.Char(string='Username')
    username_show = fields.Char(string='Show Username')
    password = fields.Char(string='Password')
    shw_password = fields.Char()
    show_psw = fields.Boolean(default=False, copy=False, readonly=False)
    last_update_on = fields.Date(string='Last Update On')
    amc_id = fields.Many2one('amc.assets')

    @api.onchange('password')
    def chng_pas(self):
        if self.password:
            self.shw_password = self.password

    @api.onchange('shw_password')
    def show_password(self):
        if self.shw_password:
            self.password = self.shw_password

    @api.onchange('username')
    def chng_username(self):
        if self.username:
            self.username_show = self.username

    @api.onchange('show_username')
    def show_username(self):
        if self.show_username:
            self.username = self.username_show
