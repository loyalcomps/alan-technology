# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang



class ProductProduct(models.Model):
    _inherit = "product.product"

    #
    # kg_department_id = fields.Many2one('hr.department', string='Department')
    # kg_part_no = fields.Char(string='Part number')
    # kg_brand_id = fields.Many2one('kg.product.brand', string='Brand')
    # kg_optional_line = fields.One2many('kg.optional.product', 'product_id', string="Optional Line")
    # kg_product_cost_history_line = fields.One2many('kg.product.cost.history', 'product_id', string="Cost History Line")
    # kg_servicecall_categories = fields.Selection([
    #     ('new_installation', 'New Installation'),
    #     ('amc', 'Annual Maintenance Contract(AMC)'),
    #     ('rma', 'RMA - Faulty Product Service'),
    #     ('poc', 'Proof Of Concept(POC)')],
    #     string='Service Type', default='new_installation')
    # active = fields.Boolean(string='Active', default=True)

    # @api.multi
    # def optional_product(self):
    #     action = self.env.ref('kg_so_enhancement.action_kg_optional_product').read()[0]
    #     product_id = self.id
    #     domain = []
    #     domain.append(('product_id', '=', product_id))
    #     action['domain'] = domain
    #
    #     action['context'] = {
    #
    #         'default_product_id': product_id
    #     }
    #
    #     return action
    #

    def open_cost_history(self):
        action = self.env.ref('kg_sale.action_kg_product_cost_history').read()[0]
        product_id = self.id
        domain = []
        domain.append(('product_id', '=', product_id))
        action['domain'] = domain

        action['context'] = {

            'default_product_id': product_id
        }

        return action


class ProductTemplate(models.Model):
    _inherit = "product.template"


    kg_department_id = fields.Many2one('hr.department', string='Department')
    kg_part_no = fields.Char(string='Part number')
    kg_brand_id = fields.Many2one('kg.product.brand', string='Brand')
    kg_optional_line = fields.One2many('kg.optional.product', 'product_id', string="Optional Line")
    kg_product_cost_history_line = fields.One2many('kg.product.cost.history', 'product_id', string="Cost History Line")
    kg_servicecall_categories = fields.Selection([
        ('new_installation', 'New Installation'),
        ('amc', 'Annual Maintenance Contract(AMC)'),
        ('rma', 'RMA - Faulty Product Service'),
        ('poc', 'Proof Of Concept(POC)')],
        string='Service Type', default='new_installation')
    active = fields.Boolean(string='Active', default=True)


    @api.onchange('kg_brand_id')
    def onchange_kg_brand_id(self):

        if self.kg_brand_id:
            category = self.env['product.category'].sudo().search([('kg_brand_id', '=', self.kg_brand_id.id)])
            print(category,"catgryyyyyyyyyyyyyyyyyyyyy")
            # self.categ_id = category.name
            return {'domain': {'categ_id': [('id', 'in', category.ids)]}}
        return {'domain': {'categ_id': []}}

