# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang



class AccountPayment(models.Model):
    _inherit = 'account.payment'

    kg_pdc = fields.Boolean(string='PDC')
    kg_cleared = fields.Boolean(string='Cleared')
    kg_other_name = fields.Char(string='Other Name')
    kg_amount_words = fields.Char(string="Amount(words)")


    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount == 0:
                raise ValidationError(_('Amount should not be zero.'))