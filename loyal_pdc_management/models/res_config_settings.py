# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = "res.company"

    pdc_customer_account = fields.Many2one('account.account', 'PDC Account for Customer',
                                           domain=lambda self: "[('company_id', '=', id), ('reconcile', '=', True), ('account_type', '=', 'asset_current')]",
                                           help='Default PDC account for customer')

    pdc_supplier_account = fields.Many2one('account.account', 'PDC Account for Supplier',
                                           domain=lambda self: "[('company_id', '=', id), ('reconcile', '=', True), ('account_type', '=', 'asset_current')]",
                                           help='Default PDC account for supplier')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pdc_customer_account = fields.Many2one('account.account', 'PDC Account for Customer', readonly=False,
                                           domain=lambda self: "[('company_id', '=', company_id), ('reconcile', '=', True), ('account_type', '=', 'asset_current')]",
                                           help='Default PDC account for customer',
                                           related='company_id.pdc_customer_account')
    pdc_supplier_account = fields.Many2one('account.account', 'PDC Account for Supplier', readonly=False,
                                           domain=lambda self: "[('company_id', '=', company_id), ('reconcile', '=', True), ('account_type', '=', 'asset_current')]",
                                           help='Default PDC account for supplier',
                                           related='company_id.pdc_supplier_account')