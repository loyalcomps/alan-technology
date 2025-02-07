from odoo import api, models,fields, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = 'account.payment'


    layout_id = fields.Many2one('check.layout','Check Layout')
    check_amount_in_words = fields.Char(
        string="Amount in Words",
        store=True,
        compute='_compute_check_amount_in_words',
    )

    @api.depends('payment_method_id', 'currency_id', 'amount')
    def _compute_check_amount_in_words(self):
        for pay in self:
            if pay.currency_id and pay.payment_method_id.code == 'check_printing':
                pay.check_amount_in_words = pay.currency_id.amount_to_text(pay.amount)
            else:
                pay.check_amount_in_words = pay.currency_id.amount_to_text(pay.amount)