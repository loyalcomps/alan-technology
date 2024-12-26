# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict

class PdcReportWizard(models.TransientModel):
    _name = 'pdc.report.wizard'

    csv_data = fields.Binary()
    filename = fields.Char()


