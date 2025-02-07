# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import image_process
from datetime import timedelta,date,datetime

from ast import literal_eval
from dateutil.relativedelta import relativedelta
from collections import OrderedDict
import re




class CheckLayout(models.Model):

    _name = 'check.layout'
    _description = 'Check Layout'

    name = fields.Char('Description',required=True)
    font_size = fields.Integer('Font Size',default=20)
    # ac_payee_padding_top = fields.Integer('Padding Top')
    # ac_payee_margin_left = fields.Integer('Margin Left')
    # rotation_text = fields.Integer('Rotation')

    date_top_padding = fields.Integer('Top Padding',default=20)
    date_left_margin = fields.Integer('Left Margin',default=180)

    amt_words_top_padding = fields.Integer('Top Padding',default=45)
    amt_words_left_margin = fields.Integer('Left Margin',default=20)
    amt_words_line_height = fields.Integer('Line Height',default=9)
    amt_words_max_width = fields.Integer('Max Width',default=140)

    amt_top_padding = fields.Integer('Top Padding',default=50)
    amt_left_margin = fields.Integer('Left Margin',default=180)


    ben_top_padding = fields.Integer('Top Padding',default=30)
    ben_left_margin = fields.Integer('Left Margin',default=20)