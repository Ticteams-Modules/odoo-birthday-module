/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { L10nPaEdiPosReceipt } from "@odoopanama_org/app/Screens/Receipt/L10nPaEdiPosReceipt";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);

        // Asegurarnos de que orderUiState esté definido
        if (!this.orderUiState) {
            this.orderUiState = {};
        }

        this.orderUiState.is_l10n_pa_receipt = this.pos.config.l10n_pa_edi_send_invoice || false;
    },

    async printReceipt() {
        this.buttonPrintReceipt.el.className = "fa fa-fw fa-spin fa-circle-o-notch";
        const isPrinted = await this.printer.print(
            L10nPaEdiPosReceipt,
            {
                data: this.pos.get_order().export_for_printing(),
                formatCurrency: this.env.utils.formatCurrency,
                order: this.currentOrder,
            },
            { webPrintFallback: true }
        );

        if (isPrinted) {
            this.currentOrder._printed = true;
        }

        if (this.buttonPrintReceipt.el) {
            this.buttonPrintReceipt.el.className = "fa fa-print";
        }
    },
});

patch(ReceiptScreen, {
    components: { ...ReceiptScreen.components, L10nPaEdiPosReceipt },
});
