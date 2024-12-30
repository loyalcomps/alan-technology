from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    kg_sign_signature = fields.Binary(string="Signature")


class ResCompany(models.Model):
    _inherit = 'res.company'


    company_seal = fields.Image(string='Company Seal')
