/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        const currentOrder = this.pos.get_order();
        if (!currentOrder) {
            return;
        }

        this.invoice_journals = this.pos.journals || [];
        const isRefund = currentOrder.is_refund();

        if (this.pos.config.l10n_pa_edi_send_invoice) {
            currentOrder.set_to_invoice(true);
        }

        if (!isRefund && this.pos.config.auto_select_journal) {
            currentOrder._autoSelectJournal(this.pos.journals);
        }

        this.state = useState({
            selectedJournalId: currentOrder.payment_journal_id || null,
        });
    },

    shouldDownloadInvoice() {
        return false;
    },

    get has_payment_refund() {
        return this.currentOrder.is_refund();
    },

    async _postPushOrderResolve(order, order_server_ids) {
        try {
            const invoiceData = await this.orm.call(
                "pos.order",
                "invoice_data",
                [order.pos_reference]
            );

            if (invoiceData) {
                Object.assign(order, invoiceData);
                if (!order._raw) {
                    order._raw = {};
                }
                Object.assign(order._raw, invoiceData);
            }
        } catch (error) {
            console.error("Error obteniendo datos de factura:", error);
        }

        return super._postPushOrderResolve(...arguments);
    },

    setJournal(journal) {
        const currentOrder = this.pos.get_order();
        if (!currentOrder) {
            return;
        }

        this.state.selectedJournalId = journal.id;
        currentOrder.payment_journal_id = journal.id;
        currentOrder.set_to_invoice(true);
    },

    async validateOrder(isForceValidate) {
        const currentOrder = this.pos.get_order();

        if (this.pos.config.l10n_pa_edi_send_invoice) {
            if (!currentOrder.is_refund() && !currentOrder.payment_journal_id) {
                this.dialog.add(AlertDialog, {
                    title: _t("Diario no seleccionado"),
                    body: _t("Debe seleccionar un diario para facturar antes de proceder con la venta."),
                });
                return;
            }
        }

        return super.validateOrder(isForceValidate);
    },
});
