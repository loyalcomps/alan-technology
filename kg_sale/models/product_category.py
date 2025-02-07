from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang

import odoo.addons.decimal_precision as dp
import datetime
from dateutil.relativedelta import relativedelta 



class Product_Category(models.Model):
    _inherit = "product.category"

    kg_brand_id = fields.Many2one('kg.product.brand','Brand')
