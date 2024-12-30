# -*- coding: utf-8 -*-

# from odoo.report import report_sxw
from odoo import models, api


class StockAgeingReport(models.AbstractModel):
    _name = 'report.stock_ageing_report.stock_ageing_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.ageing'].search([])
        return {
            'docs': docs,
            'data': data,
        }
