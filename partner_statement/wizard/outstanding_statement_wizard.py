# Copyright 2018 ForgeFlow, S.L. (http://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models
from datetime import datetime

class OutstandingStatementWizard(models.TransientModel):
    """Outstanding Statement wizard."""

    _name = "outstanding.statement.wizard"
    _inherit = "statement.common.wizard"
    _description = "Outstanding Statement Wizard"

    def _print_report(self, report_type):
        self.ensure_one()
        data = self._prepare_statement()

        if report_type == "xlsx":
            report_name = "p_s.report_outstanding_statement_xlsx"
        else:
            report_name = "partner_statement.outstanding_statement"
        partner = self.env['res.partner'].browse(data['partner_ids'])
        if self.salesperson_wise and self.salesperson_id:
            partner_name = self.salesperson_id.name
        else:
         partner_name = partner.name
        # return (
        #     self.env["ir.actions.report"]
        #     .search(
        #         [("report_name", "=", report_name), ("report_type", "=", report_type)],
        #         limit=1,
        #     )
        #     .report_action(self, data=data)
        # )
         rec= self.env["ir.actions.report"].search(
                [("report_name", "=", report_name), ("report_type", "=", report_type)],
                limit=1,
            )
        # customer_name = self.partner_id.name  # Assuming 'partner_id' is the related customer field
         date = self.date_end

         rec.name = f" Outstanding Statement -{partner_name}-{date}"

         return rec.with_context(print_report_name=rec.name).report_action(self, data=data)

        # return rec_name

    def _export(self, report_type):
        """Default export is PDF."""
        return self._print_report(report_type)
