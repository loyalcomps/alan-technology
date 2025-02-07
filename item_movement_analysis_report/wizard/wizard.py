# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import io
from odoo import fields, models, _
from datetime import date
from odoo.exceptions import ValidationError
from odoo.tools import date_utils

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class ItemMovementAnalysis(models.TransientModel):
    _name = "item.movement.analysis"

    start_date = fields.Date(string='From Date', help='select start date')
    end_date = fields.Date(string='To Date', help='select end date')
    product_ids = fields.Many2many('product.product', string='Products')

    def print_report(self):
        print(self)
        data = {
            'form': self.read()[0]
        }

        return self.env.ref('item_movement_analysis_report.action_item_movement_analysis_report').report_action(self,
                                                                                                            data=data)

