from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_project_stages = fields.Boolean("Service Stages", implied_group="project.group_project_stages")

