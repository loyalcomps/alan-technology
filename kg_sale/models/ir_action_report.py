from odoo import api, fields, models, _


class ActionReport(models.Model):
    _inherit = 'ir.actions.report'

    company_type = fields.Selection([('saudi','Saudi'),('non_saudi','Non Saudi'),('common','Common')],default='common')