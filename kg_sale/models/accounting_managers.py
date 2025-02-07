# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import Warning
import base64
import csv


from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare

from odoo.exceptions import UserError

class KGPartnerAccountingManagersLine(models.Model):
    _name = "kg.partner.accounting.managers.line"
    _description = "KGPartnerAccountingManagersLine"


    employee_id = fields.Many2one('hr.employee',string="Employee")
    department_id = fields.Many2one('hr.department',string="Department")
    partner_id = fields.Many2one('res.partner',string="Partner")
