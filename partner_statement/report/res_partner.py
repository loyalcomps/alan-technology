# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


# import odoo.addons.decimal_precision as dp


# from monthdelta import monthdelta


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def statement_overdue(self):
        return {
            'res_model': 'outstanding.statement.wizard',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
