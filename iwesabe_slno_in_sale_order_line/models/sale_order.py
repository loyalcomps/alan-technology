# -*- coding: utf-8 -*-
##############################################################################
#
#    Global Creative Concepts Tech Co Ltd.
#    Copyright (C) 2018-TODAY iWesabe (<http://www.iwesabe.com>).
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models



class SaleOrder(models.Model):
    _inherit = 'sale.order'


    # @api.onchange('order_line')
    # def _onchange_order_line_set_sn(self):
    #     sl_no = 1
    #     for line in self.order_line:
    #         if line.display_type not in ['line_note', 'line_section']:
    #             line.sl_no = sl_no
    #             sl_no += 1
    #         else:
    #             line.sl_no = False

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sl_no = fields.Integer(string='Sl. No.')
    

    