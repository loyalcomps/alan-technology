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
class KgRevisions(models.Model):
    _name = 'kg.revisions'
    _description = 'kg.revisions'
    _order = "create_date asc"	
    

    name = fields.Char(string='Order Reference')
    origin = fields.Char(string='Source Document', )
    client_order_ref = fields.Char(string='Customer Reference')
    kg_terms_condition_line = fields.One2many('kg.revisions.terms.line','revision_id',string="Terms Line")
    

    
    date_order = fields.Datetime(string='Order Date')
    user_id = fields.Many2one('res.users', string='Salesperson', )
    partner_id = fields.Many2one('res.partner', string='Customer')
    
    kg_discount_per = fields.Float(string='Discount(%)')
    kg_discount = fields.Float(string='Discount')
    kg_sale_order_id = fields.Many2one('sale.order',string='Sale Order')
    kg_note = fields.Text('Note')
    kg_remarks = fields.Char(string='Remark')
    validity_date = fields.Date(string='Expiration Date')
    revision_line = fields.One2many('kg.revisions.line', 'revision_id', string='Revision Lines', )
    currency_id = fields.Many2one('res.currency',string='Currency')
    pricelist_id = fields.Many2one('product.pricelist',string='Pricelist')

  

    note = fields.Text('Terms and conditions')

    amount_untaxed = fields.Float(string='Untaxed Amount')
    amount_tax = fields.Float(string='Taxes')
    amount_total = fields.Float(string='Total')

    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    fiscal_position_id = fields.Many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position')
    team_id = fields.Many2one('crm.team', 'Sales Team')

    def unlink(self):
        """Prevents deletion of revision records.

        This method overrides the default `unlink` function to prevent the deletion
        of records in the `KgRevisions` model. If a deletion attempt is made, a
        `UserError` is raised, restricting users from deleting revisions.

        Raises:
            UserError: Always raised to prevent deletion of revisions.
        """
        raise UserError(_('You cannot delete revisions.'))
        return super(KgRevisions, self).unlink()


class KgRevisionsLine(models.Model):
    _name = 'kg.revisions.line'
    _description = 'kg.revisions.line'


    revision_id = fields.Many2one('kg.revisions', string='Revision')

    kg_serial_no = fields.Float('S.NO')
    

    name = fields.Text(string='Description')


    price_unit = fields.Float('Unit Price')

    price_subtotal = fields.Float(string='Subtotal')

    tax_id = fields.Many2many('account.tax', string='Taxes')
 


    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Float(string='Quantity')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')


class KgRevisionsTermsLine(models.Model):
    _name = "kg.revisions.terms.line"


    revision_id = fields.Many2one('kg.revisions', string='Revision')
    terms_id = fields.Many2one('kg.terms.condition',string="Terms and Condition")
