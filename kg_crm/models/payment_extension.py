# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import Warning


class KgPaymentExtension(models.Model):
    _name = 'kg.payment.extension'
    _description = "kg.payment.extension"

    days = fields.Integer(string='Days')
    name = fields.Char(string='Name', )
    note = fields.Text(string='Note')
