# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

import datetime
from dateutil.relativedelta import relativedelta 
from num2words import num2words


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"


    @api.depends('amount_total') 
    def _kg_compute_aed_text(self):
        for sale in self:
            kg_aed_value = sale.amount_total
            mystr = "{:.2f}".format(kg_aed_value)
            split_num = mystr.split('.')
            finalstr = num2words(int(split_num[0]))
            if split_num[1] != '00':
                finalstr = finalstr + ' DIRHAMS AND ' + num2words(int(split_num[1])) + ' FILS '

            else:
                finalstr = finalstr + ' DIRHAMS '
            finalstr = finalstr + " ONLY "
            sale.kg_aed_text = finalstr.upper()

    kg_aed_text = fields.Char('AED Text',compute='_kg_compute_aed_text',store=True)


