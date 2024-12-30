# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class PurchaseOrderGroup(models.TransientModel):
    _name = "purchase.order.group"
    _description = "Purchase Order Merge"

    def merge_orders(self):
        order_obj = self.env['purchase.order']
        active_ids = self._context.get('active_ids', [])
        if len(active_ids) < 2:
            raise UserError(
                _('Choose atleast two records'))

        allorders = order_obj.do_merge(order_obj, active_ids)
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        action['domain'] = [('id', '=', allorders)]

        return action
#
