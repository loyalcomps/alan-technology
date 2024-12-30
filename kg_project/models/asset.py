from odoo import fields, models, api
from datetime import datetime,date


class ProjectAsset(models.Model):
    _name = "project.asset"
    _description = "Asset"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    project_id = fields.Many2one('project.project')
    name = fields.Char()
    password = fields.Char()
    shw_password = fields.Char()
    show_psw = fields.Boolean(default=False,copy=False,readonly=False)
    date = fields.Date(default=date.today())

    @api.onchange('password')
    def chng_pas(self):
        if self.password :
            print("mai")
            self.shw_password = self.password

    @api.onchange('shw_password')
    def show_password(self):
        if self.shw_password:
            print("chmai")
            self.password = self.shw_password