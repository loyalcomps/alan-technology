from odoo import models, fields, api,_

class SaleCancelCustom(models.TransientModel):
    _name = 'sale.cancel.custom'
    _description = 'sale.cancel.custom'


    cancel_reason = fields.Text(string="Cancel Reason")
    sale_id = fields.Many2one('sale.order')

    def action_cancel_confirm(self,ctx=None):
        template = self.env.ref('sale.mail_template_sale_cancellation')
        compose_form_id = self.env.ref('sale.sale_order_cancel_view_form').id

        context = {
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'default_order_id': self.sale_id.id,
            'default_cancel_reason': self.cancel_reason,
            'default_attachment_ids': None,
            'force_email': True,
            'default_email_from': self.sale_id.partner_id.email,
            'default_partner_id': self.sale_id.partner_id.id
        }

        if ctx:
            context.update(ctx)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.cancel',
            'view_mode': 'form',
            'views': [(compose_form_id, 'form')],
            'views_id': compose_form_id,
            'target': 'new',
            'context': context,
        }

class SaleOrderCancel(models.TransientModel):
    _inherit = 'sale.order.cancel'

    cancel_reason = fields.Text(string="Cancel Reason")


    def action_send_mail_and_cancel(self):
        result = super(SaleOrderCancel, self).action_send_mail_and_cancel()
        self.order_id.cancelled_reason = self.cancel_reason
        return result

    def action_cancel(self):
        result = super(SaleOrderCancel, self).action_cancel()
        self.order_id.cancelled_reason = self.cancel_reason
        return result
