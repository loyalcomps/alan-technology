/** @odoo-module */

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import framework from 'web.framework';
import session from 'web.session';
console.log("LLLLLLL")
registry.category("ir.actions.report handlers").add("partner_statement_xlsx", async (action) => {
    if (action.report_type === 'partner_statement_xlsx') {
        framework.blockUI();
        var def = $.Deferred();
        session.get_file({
            url: '/partner_statement_xlsx',
            data: action.data,
            success: def.resolve.bind(def),
            error: (error) => this.call('crash_manager', 'rpc_error', error),
            complete: framework.unblockUI,
        });
        return def;
    }
});
