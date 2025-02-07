# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    kg_is_create = fields.Boolean(default=False)
    kg_tr_no = fields.Char()
    issue_count = fields.Integer(compute='_compute_issue_count')
    issue_ids = fields.One2many('project.issue', 'partner_id', string='Issues')

    def _compute_issue_count(self):
        for project in self:
            project.issue_count = len(project.issue_ids)

    def act_create_user_portal(self):
        users = self.env['res.users']
        portal_group = self.env.ref('base.group_portal').id
        for rec in self:
            if rec.user_ids:
                rec.user_ids.write({'groups_id': [(4, portal_group)]})
                continue
            if not rec.email:
                continue
            user = users.create(
                {'partner_id': rec.id, 'name': rec.name, 'login': rec.email, 'groups_id': [(4, portal_group)]})
            self.kg_is_create = True
