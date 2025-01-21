from odoo import models, fields, api,_
from datetime import datetime, timedelta
from odoo.exceptions import UserError, AccessError

class SaleCancelCustom(models.TransientModel):
    _name = 'sale.cancel.custom'
    _description = 'sale.cancel.custom'


    cancel_reason = fields.Text(string="Cancel Reason")
    sale_id = fields.Many2one('sale.order')
    check_approve=fields.Boolean()
    description=fields.Text('Approval Reason')

    @api.model
    def send_so_approval_notifications(self,sale_id):
        company = self.env.company
        email_subject = "Sale Order Approval Notification"

        if sale_id.is_director_approval or sale_id.amount_total > company.max_order_amount:

            group_xml_ids =[
                'sale_customization.group_directors',

            ]
            description = sale_id.director_description

        else:
            group_xml_ids = [
                'sale_customization.group_sales_manager',

            ]
            description = sale_id.manager_description

        # Search for the corresponding group records
        groups = self.env['ir.model.data'].search([
            ('module', 'in', [xml_id.split('.')[0] for xml_id in group_xml_ids]),
            ('name', 'in', [xml_id.split('.')[1] for xml_id in group_xml_ids])
        ]).mapped('res_id')

        # Find users who belong to these groups
        user_records = self.env['res.users'].search([('groups_id', 'in', groups)])

        partner_ids = [(4, user.partner_id.id) for user in user_records]

        notification_ids = []

        for user in user_records:

            email_body = (f"Dear {user.name},<br/><br/>\n\n"

                          f"    {description}<br/>"
                          
                          f"   </b><br/>"
                         
                          f"Best regards,<br/>"
                          f"{sale_id.company_id.name}")
            # Send email
            mail_values = {
                'subject': email_subject,
                'body_html': email_body,
                'email_to': user.email,
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()
            notification_ids.append((0, 0, {
                'res_partner_id': user.partner_id.id,
                'notification_type': 'inbox'
            }))

            self.env['mail.message'].create({
                'model': 'sale.order',
                'res_id': sale_id.id,
                'partner_ids': partner_ids,
                'notification_ids': notification_ids,
                'message_type': 'notification',
                'author_id': self.env.user.partner_id.id if self.env.user.partner_id else False,
                'subtype_id': self.env.ref('mail.mt_comment').id,
                'body': email_body,
            })

            self.env['bus.bus']._sendone(
                channel=(self._cr.dbname, 'res.partner', user.partner_id.id),
                notification_type='simple_notification',
                message={'message': email_body}
            )
        return True

    def action_approve(self):
        self.sale_id.first_confirm=True
        self.send_so_approval_notifications(self.sale_id)


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
        body = _('Sale Order is Cancelled - Reason : %s',self.order_id.cancelled_reason)
        self.order_id.message_post(body=body)
        return result


    def action_confirm(self):
        """Confirm sale order and update move descriptions from order lines.

        Returns:
            Result from super call after confirming sale order

        Raises:
            UserError: If order requires approval but hasn't been approved yet
        """
        # self.sudo().update_first_confirm()
        self.env.cr.execute("""
                                      UPDATE sale_order
                                      SET first_confirm = TRUE
                                      WHERE id = %s
                                  """, (self.id,))



        if self.show_approve and self.state not in ['approve']:

            raise UserError("You cannot confirm the Sale Order unless the state is 'Approved'.")


