# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import Warning


class KgWarranty(models.Model):
    _name = 'kg.warranty'
    _description = "Warranty"


    name = fields.Char(string='Name')
    note = fields.Text(string='Name')
