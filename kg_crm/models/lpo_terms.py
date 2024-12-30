 # -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import Warning


class KgLpoTerms(models.Model):
    _name = 'kg.lpo.terms'
    _description = "Lpo Terms"


    name = fields.Char(string='Name')
    note = fields.Text(string='Name')
