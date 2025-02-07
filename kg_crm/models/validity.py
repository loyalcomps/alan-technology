# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import Warning


class KgValidity(models.Model):
    _name = 'kg.validity'
    _description = "Validity"


    name = fields.Char(string='Name')
    note = fields.Text(string='Name')
