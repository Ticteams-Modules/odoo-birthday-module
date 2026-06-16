/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.pa_invoice_type = this.pa_invoice_type || false;
        this.payment_journal_id = this.payment_journal_id || null;
        this.original_move_id = this.original_move_id || false;
    },

    wait_for_push_order() {
        return true;
    },

    _autoSelectJournal(journals) {
        const availableJournals = journals || [];
        if (availableJournals.length > 0) {
            this.payment_journal_id = availableJournals[0].id;
            this.set_to_invoice(true);
        }
    },

    serialize() {
        const data = super.serialize(...arguments);
        data.invoice_journal_id = this.payment_journal_id || null;
        data.original_move_id = this.original_move_id || false;
        return data;
    },

    /**
     * Verifica si la orden es un reembolso (nota de crédito)
     */
    is_refund() {
        if (this.original_move_id) {
            return true;
        }
        const lines = this.lines || [];
        if (!lines.length) {
            return false;
        }
        return lines.some(line => line.refunded_orderline_id);
    },

    /**
     * Al eliminar líneas, verificar si debe limpiar original_move_id
     */
    removeOrderline(line) {
        const res = super.removeOrderline(...arguments);

        if (this.original_move_id) {
            const lines = this.lines || [];
            const hasRefundLines = lines.some(l => l.refunded_orderline_id);
            if (!hasRefundLines) {
                this.original_move_id = false;
            }
        }

        return res;
    },

    /**
     * Exportar datos para impresión del recibo
     * Incluye datos de facturación electrónica si están disponibles
     */
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);

        // Enriquecer líneas de pedido con información adicional
        if (result.orderlines?.length > 0) {
            const orderLines = this.get_orderlines();
            result.orderlines = result.orderlines.map((line, index) => {
                const originalLine = orderLines[index];
                return {
                    ...line,
                    tax_amount: originalLine?.get_tax() || 0,
                    default_code: originalLine?.get_product()?.default_code || '',
                };
            });
        }

        // Asignar datos de factura electrónica si existen
        if (this._raw) {
            Object.assign(result, this._raw);
        }

        // Datos del cliente
        const partner = this.get_partner();
        result.partner = partner ? {
            name: partner.name,
            vat: partner.vat,
            address: partner.contact_address,
        } : null;

        return result;
    }
});
