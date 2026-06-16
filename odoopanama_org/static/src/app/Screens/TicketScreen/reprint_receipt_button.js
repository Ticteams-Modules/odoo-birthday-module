/** @odoo-module */


import { ReprintReceiptButton } from "@point_of_sale/app/screens/ticket_screen/reprint_receipt_button/reprint_receipt_button";
import { L10nPaEdiPosReceipt } from "@odoopanama_org/app/Screens/Receipt/L10nPaEdiPosReceipt";
import { patch } from "@web/core/utils/patch";


patch(ReprintReceiptButton.prototype, {
    async click() {
        if (!this.props.order) {
            return;
        }
        // Need to await to have the result in case of automatic skip screen.
        (await this.printer.print(L10nPaEdiPosReceipt, {
            data: this.props.order.export_for_printing(),
            formatCurrency: this.env.utils.formatCurrency,
            order: this.props.order,
        })) || this.pos.showScreen("ReprintReceiptScreen", { order: this.props.order });
    }
})
