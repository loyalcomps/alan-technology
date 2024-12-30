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

class KGIndustryMaster(models.Model):
    _name = "kg.industry.master"
    _description = "KGIndustryMaster"



    name = fields.Char(string='Name')
    desc = fields.Text(string="Description")
    
