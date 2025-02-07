# from odoo.report import report_sxw
from odoo import models, api, _
from odoo.exceptions import except_orm


class StockReport(models.AbstractModel):
    _name = 'report.stock_movement_analysis_report.stock_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.move'].search([])
        return {
            'doc_ids': docs.ids,
            'doc_model': 'stock.move',
            'docs': docs,
            'data': data,
        }
