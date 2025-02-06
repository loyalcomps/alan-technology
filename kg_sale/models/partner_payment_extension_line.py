# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import Warning
from odoo import api, fields, models, _
from odoo.exceptions import UserError




class KgPartnerPaymentExtensionLine(models.Model):
    _name = 'kg.partner.payment.extension.line'
    _description = "kg.partner.payment.extension.line"



    def unlink(self):
        """Prevents deletion of the record if it has been approved.

        This method raises a `UserError` if the record has already been approved,
        preventing its deletion. If the record is not approved, the deletion proceeds
        by calling the superclass `unlink` method.

        Returns:
            bool: Returns the result of the superclass `unlink` method, allowing
                  deletion only if the record has not been approved.

        Raises:
            UserError: If the record is approved, it raises a `UserError` with a message
                       indicating that the record cannot be deleted.
        """
        if self.approved:
            raise UserError(_('you cannot delete it,its already approved'))
            

        return super(KgPartnerPaymentExtensionLine, self).unlink()    

    def allow_extension_approval(self):
        """Approves the payment extension and calculates the total extended days.

        This method approves the payment extension and calculates the total extended
        days by adding the `payment_extension_id.days` and the days from any previous
        extensions for the same partner. It updates the partner's extension remarks
        and marks the extension as approved.

        Returns:
            None

        Raises:
            UserError: If the record has already been approved, a `UserError` is raised.
            UserError: If the partner has not been set, a `UserError` is raised asking
                       the user to save the form first.
        """
        partner_id = self.partner_id and self.partner_id.id
        if self.approved:
            raise UserError(_('already approved'))            
        if not partner_id:
            raise UserError(_('Please Save the form first'))
            
        kg_payment_extension_line = self
        prev_days = 0
        previous_lines = self.env['kg.partner.payment.extension.line'].search([('partner_id', '=', partner_id),('id', '!=', self.id)])
        for line in previous_lines:
            prev_days = prev_days + line.extended_days
            
        

         
        extended_days = self.payment_extension_id.days + prev_days
        self.extended_days = extended_days
        self.approved = True
        partner = self.partner_id
 
            

        partner.kg_payment_extension_remarks = 'Approved for ' + str(extended_days) + ' Days'



    partner_id = fields.Many2one('res.partner',string="Partner")
    extended_days = fields.Integer(string="Extended Days",)
    payment_extension_id = fields.Many2one('kg.payment.extension',string="Payment Extension")
    approved = fields.Boolean('Approved')
