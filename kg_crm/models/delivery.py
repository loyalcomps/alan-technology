# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import Warning


class KgDelivery(models.Model):
    _name = 'kg.delivery'
    _description = "Delivery conditions"


    name = fields.Char(string='Name')
    note = fields.Text(string='Name')
